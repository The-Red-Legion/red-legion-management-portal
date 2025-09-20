"""Health check and monitoring endpoints."""

from fastapi import APIRouter
import os
import logging
from datetime import datetime
from typing import Dict, Any

from database import get_db_pool
from services.uex_service import UEXService
from services.discord_integration import get_discord_bot_status

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/ping")
@router.get("/mgmt/api/ping")
async def ping():
    """Simple ping endpoint for health checks."""
    return {"status": "ok", "message": "Red Legion Management Portal API is running"}

@router.get("/health")
@router.get("/mgmt/api/health")
async def health():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "service": "Red Legion Management Portal",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/status")
@router.get("/mgmt/api/status")
async def system_status():
    """Comprehensive system status with all service connections."""
    status_data = {
        "timestamp": datetime.now().isoformat(),
        "service": "Red Legion Management Portal",
        "version": "2.0.0",
        "overall_status": "healthy",
        "services": {}
    }

    # Database status
    try:
        pool = await get_db_pool()
        if pool:
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            status_data["services"]["database"] = {
                "status": "connected",
                "message": "Database connection successful",
                "type": "PostgreSQL"
            }
        else:
            status_data["services"]["database"] = {
                "status": "disconnected",
                "message": "Database pool not available",
                "type": "PostgreSQL"
            }
            status_data["overall_status"] = "degraded"
    except Exception as e:
        status_data["services"]["database"] = {
            "status": "error",
            "message": f"Database connection failed: {str(e)}",
            "type": "PostgreSQL"
        }
        status_data["overall_status"] = "degraded"

    # UEX Service status
    try:
        bot_api_url = os.getenv("BOT_API_URL", "http://localhost:8001")
        uex_service = UEXService(bot_api_url)
        uex_data = await uex_service.get_uex_prices()

        status_data["services"]["uex_prices"] = {
            "status": uex_data["status"],
            "source": uex_data["source"],
            "message": uex_data["message"],
            "last_updated": uex_data["last_updated"]
        }

        if uex_data["status"] != "connected":
            status_data["overall_status"] = "degraded"

    except Exception as e:
        status_data["services"]["uex_prices"] = {
            "status": "error",
            "source": "unknown",
            "message": f"UEX service error: {str(e)}"
        }
        status_data["overall_status"] = "degraded"

    # Discord Bot status
    try:
        discord_status = await get_discord_bot_status()
        if discord_status.get("connected"):
            status_data["services"]["discord_bot"] = {
                "status": "connected",
                "message": "Discord bot is online and responsive"
            }
        else:
            status_data["services"]["discord_bot"] = {
                "status": "disconnected",
                "message": discord_status.get("error", "Discord bot not responding")
            }
            status_data["overall_status"] = "degraded"
    except Exception as e:
        status_data["services"]["discord_bot"] = {
            "status": "error",
            "message": f"Discord bot status check failed: {str(e)}"
        }
        status_data["overall_status"] = "degraded"

    # Set overall status based on critical services
    if status_data["services"]["database"]["status"] == "error":
        status_data["overall_status"] = "unhealthy"

    return status_data