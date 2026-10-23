"""
FastAPI MCP Gateway Application.
Entry point assembling all MVC controllers, database lifespan, and CORS middleware.
"""

import os
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aggregator import aggregator
from database import init_db
from controllers import (
    auth_router,
    key_router,
    server_router,
    tool_router,
    audit_router,
    mcp_router,
    chat_router,
)

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("mcp-gateway")

PORT = int(os.getenv("PORT", "8000"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing MCP Gateway database, seeding upstreams and team users...")
    await init_db()
    logger.info("Refreshing initial tools from all upstreams...")
    await aggregator.refresh_tools()
    yield
    logger.info("MCP Gateway shutting down.")


app = FastAPI(
    title="Team MCP Gateway",
    version="1.0.0",
    description="Centralized Model Context Protocol Gateway on Kubernetes with Team RBAC and Audit Logging",
    lifespan=lifespan
)

# Enable CORS for the future React Dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register MVC Routers / Controllers
app.include_router(auth_router)
app.include_router(key_router)
app.include_router(server_router)
app.include_router(tool_router)
app.include_router(audit_router)
app.include_router(mcp_router)
app.include_router(chat_router)


# Health Check Endpoint
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy", "service": "mcp-gateway"}


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting MCP Gateway on port {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
