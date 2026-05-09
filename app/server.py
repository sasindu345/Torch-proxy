"""
FastAPI application factory with lifespan management.
Starts the background monitoring loop on startup, cancels it on shutdown.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

import aiohttp
from fastapi import FastAPI

from app.state import state
from app.services.monitor import monitoring_loop
from app.routes import health, config, proxies, alerts, webhooks, integrations, metrics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-25s | %(levelname)-5s | %(message)s",
)
logger = logging.getLogger("proxymaze")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage the app's lifespan:
    - On startup: create aiohttp session, start background monitor
    - On shutdown: cancel monitor, close session
    """
    logger.info("🚀 ProxyMaze starting up...")

    # Create a shared aiohttp session for all outgoing HTTP requests
    session = aiohttp.ClientSession()
    app.state.http_session = session

    # Start the background monitoring loop
    monitor_task = asyncio.create_task(monitoring_loop(state, session))
    state.monitor_task = monitor_task
    logger.info("✅ Background monitor started")

    yield

    # Shutdown
    logger.info("🛑 ProxyMaze shutting down...")
    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass
    await session.close()
    logger.info("👋 Goodbye")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="ProxyMaze",
        description="Continuous proxy pool monitoring service for Torch Labs",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Register all route modules
    app.include_router(health.router)
    app.include_router(config.router)
    app.include_router(proxies.router)
    app.include_router(alerts.router)
    app.include_router(webhooks.router)
    app.include_router(integrations.router)
    app.include_router(metrics.router)

    return app
