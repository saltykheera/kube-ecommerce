import os
import asyncio
import logging
from typing import AsyncGenerator
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from models import UpstreamServer

logger = logging.getLogger("gateway-db")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://gateway_user:gateway_secure_password@postgres:5432/gateway_db"
)

# Replace standard postgres:// scheme if provided by some cloud providers
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


DEFAULT_UPSTREAMS = [
    {
        "name": "WooCommerce Store",
        "slug": "woo",
        "url": os.getenv("WOOCOMMERCE_MCP_URL", "http://mcp-woocommerce:8000/mcp"),
        "is_enabled": True,
        "status": "connected",
    },
    {
        "name": "Calculator Engine",
        "slug": "calc",
        "url": os.getenv("CALCULATOR_MCP_URL", "http://mcp-calculator:8001/mcp"),
        "is_enabled": True,
        "status": "connected",
    },
    {
        "name": "Business Metrics",
        "slug": "metrics",
        "url": os.getenv("METRICS_MCP_URL", "http://mcp-metrics:8002/mcp"),
        "is_enabled": True,
        "status": "connected",
    },
]


async def init_db(max_retries: int = 15, retry_delay: float = 2.0):
    """Initializes database tables with retry logic and seeds the default 3 upstream MCP servers."""
    for attempt in range(1, max_retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.create_all)
            break
        except Exception as e:
            if attempt == max_retries:
                logger.error(f"Failed to connect to database after {max_retries} attempts: {e}")
                raise
            logger.warning(f"Database connection attempt {attempt}/{max_retries} failed ({e}). Retrying in {retry_delay}s...")
            await asyncio.sleep(retry_delay)

    async with async_session_maker() as session:
        # Check if upstreams already exist
        result = await session.exec(select(UpstreamServer))
        existing_servers = result.all()

        if not existing_servers:
            logger.info("Seeding default upstream MCP servers into PostgreSQL registry...")
            for s_data in DEFAULT_UPSTREAMS:
                server = UpstreamServer(**s_data)
                session.add(server)
            await session.commit()
            logger.info("Successfully seeded 3 default upstream servers (woo, calc, metrics).")
        else:
            logger.info(f"Database contains {len(existing_servers)} upstream servers.")
