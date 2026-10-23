"""
MCP Tool to Gemini Function Declaration Schema Converter.
Converts standard MCP tool schemas into Google Gemini Function Declarations.
"""

from typing import Any

# Map JSON schema primitive types to uppercase Gemini schema types
TYPE_MAP = {
    "string": "STRING",
    "integer": "INTEGER",
    "number": "NUMBER",
    "boolean": "BOOLEAN",
    "array": "ARRAY",
    "object": "OBJECT",
}


def _clean_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Recursively formats a JSON schema into Gemini-compliant schema."""
    if not isinstance(schema, dict):
        return {"type": "OBJECT", "properties": {}}

    gemini_type = TYPE_MAP.get(str(schema.get("type", "object")).lower(), "OBJECT")
    result: dict[str, Any] = {"type": gemini_type}

    if "description" in schema:
        result["description"] = schema["description"]

    if gemini_type == "OBJECT" and "properties" in schema:
        cleaned_props = {}
        for prop_name, prop_def in schema["properties"].items():
            cleaned_props[prop_name] = _clean_schema(prop_def)
        result["properties"] = cleaned_props

        if "required" in schema and isinstance(schema["required"], list):
            result["required"] = schema["required"]

    elif gemini_type == "ARRAY" and "items" in schema:
        result["items"] = _clean_schema(schema["items"])

    return result


def convert_mcp_tools_to_gemini(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Converts a list of MCP tools into Gemini function declarations."""
    declarations = []
    for tool in tools:
        name = tool.get("name")
        if not name:
            continue

        raw_schema = tool.get("inputSchema", {})
        cleaned_parameters = _clean_schema(raw_schema)

        declarations.append({
            "name": name,
            "description": tool.get("description", f"Execute tool {name}"),
            "parameters": cleaned_parameters
        })

    return declarations
