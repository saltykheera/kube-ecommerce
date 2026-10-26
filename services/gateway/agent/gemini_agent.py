"""
Gemini Chat Agent Engine.
Executes multi-turn conversational tool-calling loops through the central MCP Gateway.
Enforces caller identity attribution, RBAC permissions, and PostgreSQL audit logging.
"""

import os
import time
import json
import logging
import asyncio
from typing import Any, Optional
import httpx
from sqlmodel.ext.asyncio.session import AsyncSession

from aggregator import aggregator
from agent.tool_converter import convert_mcp_tools_to_gemini
from core.rbac import is_tool_allowed_for_role
from models.user import User
from models.audit_log import AuditLog

logger = logging.getLogger("gemini-agent")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODELS_TO_TRY = ["gemini-flash-lite-latest", "gemini-3.1-flash-lite"]
MAX_TOOL_TURNS = 5


class GeminiChatAgent:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.preferred_model = "gemini-flash-lite-latest"

    def _get_api_key(self) -> str:
        """Dynamically re-reads environment or gemini.env if not set in memory."""
        if self.api_key:
            return self.api_key
        key = os.getenv("GEMINI_API_KEY", "")
        if not key and os.path.exists("gemini.env"):
            try:
                for line in open("gemini.env").read().splitlines():
                    if line.startswith("GEMINI_API_KEY="):
                        key = line.split("=", 1)[1].strip()
                        break
            except Exception:
                pass
        self.api_key = key
        return key

    async def _call_gemini_api(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Calls Gemini API with automatic model fallback and retry logic."""
        api_key = self._get_api_key()
        if not api_key:
            raise ValueError(
                "Gemini API key is not configured. Please ensure GEMINI_API_KEY is provided in secrets."
            )

        # Order models prioritizing previously successful model if known
        models = [self.preferred_model] if self.preferred_model else []
        for m in MODELS_TO_TRY:
            if m not in models:
                models.append(m)

        last_error = None
        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            for attempt in range(1, 3):
                try:
                    async with httpx.AsyncClient(timeout=12.0) as client:
                        resp = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
                        if resp.status_code == 503:
                            logger.warning(f"Model {model} returned 503 (attempt {attempt}/2). Retrying in 1.5s...")
                            await asyncio.sleep(1.5)
                            continue

                        resp.raise_for_status()
                        self.preferred_model = model
                        return resp.json()
                except httpx.HTTPStatusError as e:
                    last_error = f"HTTP {e.response.status_code}: {e.response.text}"
                    logger.warning(f"Error calling {model}: {last_error}")
                    break
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"Network error calling {model}: {last_error}")
                    break

        raise RuntimeError(f"All Gemini models failed: {last_error}")

    async def chat(
        self,
        message: str,
        user: User,
        session: AsyncSession,
        history: Optional[list[dict[str, Any]]] = None
    ) -> dict[str, Any]:
        """
        Executes a conversational chat turn with dynamic tool calling under the user's identity.
        Returns:
            {"reply": str, "tool_calls": list[dict]}
        """
        logger.info(f"Chat request from {user.email} (Role: {user.role.value}): '{message[:60]}...'")

        # 1. Fetch available tools from the gateway
        tools = await aggregator.refresh_tools()
        gemini_tools = convert_mcp_tools_to_gemini(tools)

        # 2. Build conversation contents
        contents = []

        # System prompt context as first user turn
        system_instruction = (
            f"You are the eCommerce Team Assistant for WooCommerce on Kubernetes. "
            f"You have access to store management, math/pricing calculation, and business metrics tools. "
            f"When answering questions, call tools to get real data rather than making assumptions. "
            f"Current authenticated user: {user.email} (Role: {user.role.value})."
        )
        contents.append({"role": "user", "parts": [{"text": system_instruction}]})
        contents.append({"role": "model", "parts": [{"text": "Understood. I am ready to assist using available tools."}]})

        # Append previous message history if any
        if history:
            for turn in history:
                role = "user" if turn.get("role") == "user" else "model"
                text = turn.get("text") or turn.get("content") or ""
                if text:
                    contents.append({"role": role, "parts": [{"text": text}]})

        # Append latest user message
        contents.append({"role": "user", "parts": [{"text": message}]})

        tool_calls_executed = []

        # 3. Multi-turn Tool Calling Loop (up to MAX_TOOL_TURNS)
        for turn_idx in range(MAX_TOOL_TURNS):
            payload = {
                "contents": contents,
                "tools": [{"function_declarations": gemini_tools}] if gemini_tools else [],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 1024,
                }
            }

            try:
                gemini_res = await self._call_gemini_api(payload)
            except Exception as e:
                logger.error(f"Gemini API invocation error: {e}")
                return {
                    "reply": f"Sorry, I encountered an error communicating with the AI service: {str(e)}",
                    "tool_calls": tool_calls_executed
                }

            candidates = gemini_res.get("candidates", [])
            if not candidates:
                return {
                    "reply": "I did not receive a valid response from the model.",
                    "tool_calls": tool_calls_executed
                }

            model_content = candidates[0].get("content", {})
            model_parts = model_content.get("parts", [{}])
            model_part = model_parts[0] if model_parts else {}

            # Case A: Model issued a functionCall
            if "functionCall" in model_part:
                func_call = model_part["functionCall"]
                tool_name = func_call.get("name")
                tool_args = func_call.get("args", {})
                call_id = func_call.get("id")

                logger.info(f"Gemini requested tool: {tool_name} with args: {tool_args}")

                # Append model's exact content (preserving thoughtSignature)
                contents.append(model_content)

                # Check RBAC
                is_allowed, rbac_error = is_tool_allowed_for_role(tool_name, user.role)
                slug = tool_name.split("__")[0] if "__" in tool_name else "unknown"

                if not is_allowed:
                    logger.warning(f"RBAC blocked chat agent execution of '{tool_name}' for {user.email}")
                    tool_result = {"isError": True, "error": rbac_error}
                    tool_status = "forbidden"
                    duration_ms = 0.0
                else:
                    start_time = time.perf_counter()
                    raw_result = await aggregator.call_tool(tool_name, tool_args)
                    duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                    is_error = raw_result.get("isError", False)
                    tool_status = "error" if is_error else "success"
                    tool_result = raw_result

                # Record in PostgreSQL Audit Trail under the logged-in user
                try:
                    audit_entry = AuditLog(
                        user_id=user.id,
                        user_email=user.email,
                        api_key_id=None,  # Called via Dashboard session
                        server_slug=slug,
                        tool_name=tool_name,
                        arguments=json.dumps(tool_args),
                        status=tool_status,
                        duration_ms=duration_ms,
                        error_message=str(tool_result) if tool_status != "success" else None,
                    )
                    session.add(audit_entry)
                    await session.commit()
                except Exception as e:
                    logger.error(f"Failed to record chat audit entry: {e}")

                # Save execution record for response
                tool_calls_executed.append({
                    "tool": tool_name,
                    "arguments": tool_args,
                    "result": tool_result,
                    "status": tool_status,
                    "duration_ms": duration_ms
                })

                # Append function response turn for Gemini (using role 'user' as required by Gemini 2.x/v1beta)
                response_part = {
                    "functionResponse": {
                        "name": tool_name,
                        "response": {"result": tool_result}
                    }
                }
                if call_id:
                    response_part["functionResponse"]["id"] = call_id

                contents.append({"role": "user", "parts": [response_part]})
                # Loop continues to allow model to synthesize final answer or call another tool

            # Case B: Model returned natural language answer
            elif "text" in model_part:
                final_text = model_part.get("text", "")
                return {
                    "reply": final_text,
                    "tool_calls": tool_calls_executed
                }

            else:
                return {
                    "reply": "Task completed.",
                    "tool_calls": tool_calls_executed
                }

        return {
            "reply": "I reached the maximum number of tool steps for this request.",
            "tool_calls": tool_calls_executed
        }


# Singleton agent instance
chat_agent = GeminiChatAgent()
