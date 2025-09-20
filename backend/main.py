"""
Red Legion Web Payroll - FastAPI Backend (No Authentication)
Simple web interface for Discord bot payroll system without OAuth

Updated: 2025-09-20 - Triggering deployment with OAuth completely removed
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
import os
import asyncpg
import httpx
from dotenv import load_dotenv
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime, timedelta, timezone
from validation import (
    validate_discord_id, validate_event_id, validate_text_input,
    validate_positive_integer, validate_decimal_amount,
    EventCreateRequest, PayrollCalculateRequest, ChannelAddRequest,
    validate_pagination_params, log_validation_attempt
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
BOT_API_URL = os.getenv("BOT_API_URL", "http://10.128.0.2:8001")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

logger.info(f"Configuration loaded - DATABASE_URL: {'✓' if DATABASE_URL else '✗'}")
logger.info(f"Configuration loaded - BOT_API_URL: {BOT_API_URL}")
logger.info(f"Configuration loaded - FRONTEND_URL: {FRONTEND_URL}")

# Database connection pool
db_pool = None

async def get_db_pool():
    """Get database connection pool."""
    global db_pool
    if db_pool is None and DATABASE_URL:
        try:
            db_pool = await asyncpg.create_pool(DATABASE_URL)
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return None
    return db_pool

# CORS configuration
cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "https://dev.redlegion.gg",
    "http://dev.redlegion.gg"
]

# FastAPI app
app = FastAPI(
    title="Red Legion Management Portal API",
    description="Backend API for Red Legion web management portal",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoints
@app.get("/ping")
@app.get("/mgmt/api/ping")
async def ping():
    """Simple health check."""
    return {
        "status": "ok",
        "message": "Red Legion backend is running",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/health")
@app.get("/mgmt/api/health")
async def health_check():
    """Detailed health check."""
    pool = await get_db_pool()

    return {
        "status": "healthy",
        "database": "connected" if pool else "disconnected",
        "mode": "no-auth",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# Events endpoints
@app.get("/events")
@app.get("/mgmt/api/events")
async def get_events(request: Request):
    """Get all mining events from database."""
    try:
        pool = await get_db_pool()
        if pool is None:
            return []

        async with pool.acquire() as conn:
            events = await conn.fetch("""
                SELECT
                    event_id, event_name, event_type, organizer_name, organizer_id,
                    status, started_at, ended_at, created_at, updated_at,
                    total_participants, total_duration_minutes,
                    location_notes, description as additional_notes
                FROM events
                ORDER BY created_at DESC
            """)

            return [dict(event) for event in events]

    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch events: {str(e)}")

@app.get("/events/{event_id}/participants")
@app.get("/mgmt/api/events/{event_id}/participants")
async def get_event_participants(event_id: str):
    """Get participants for a specific event."""
    event_id = validate_event_id(event_id)

    try:
        pool = await get_db_pool()
        if pool is None:
            return []

        async with pool.acquire() as conn:
            participants = await conn.fetch("""
                SELECT
                    id as participant_id, user_id, username, display_name,
                    joined_at, left_at, duration_minutes, is_org_member as is_organizer
                FROM participation
                WHERE event_id = $1
                ORDER BY joined_at ASC
            """, event_id)

            return [dict(participant) for participant in participants]

    except Exception as e:
        logger.error(f"Error fetching participants for {event_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch participants")

@app.get("/uex-prices")
@app.get("/mgmt/api/uex-prices")
async def get_uex_prices_endpoint():
    """Get current UEX ore prices."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{BOT_API_URL}/api/uex-prices")
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"UEX API returned {response.status_code}")
                return get_fallback_uex_prices()
    except Exception as e:
        logger.error(f"Error fetching UEX prices: {e}")
        return get_fallback_uex_prices()

def get_fallback_uex_prices() -> Dict[str, float]:
    """Fallback UEX prices when API is unavailable."""
    return {
        'QUANTAINIUM': 17500.0,
        'BEXALITE': 8500.0,
        'TARANITE': 7500.0,
        'LARANITE': 5200.0,
        'TITANIUM': 8.1,
        'COPPER': 6.2,
        'DIAMOND': 7200.0,
        'GOLD': 6100.0,
        'AGRICIUM': 25600.0,
        'BERYL': 1200.0,
        'BORASE': 280.0,
        'HEPHAESTANITE': 3800.0,
        'HADANITE': 4500.0,
        'INERT MATERIALS': 0.01,
        'ALUMINUM': 1.2,
        'TUNGSTEN': 3.5,
        'QUARTZ': 1.4,
        'CORUNDUM': 185.0,
        'APHORITE': 152.0
    }

# Startup/shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup."""
    await get_db_pool()
    logger.info("Red Legion Management Portal API started (no authentication)")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up database connections on shutdown."""
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("Database connection pool closed")