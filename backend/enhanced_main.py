#!/usr/bin/env python3
"""
Enhanced Red Legion Discord OAuth backend with database connectivity.
Combines working OAuth flow from clean_main.py with essential application endpoints.
"""

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
import httpx
import os
import uvicorn
from datetime import datetime, timezone, timedelta
import secrets
import json
import asyncpg
from typing import Optional, List, Dict, Any
import logging
from dotenv import load_dotenv
from google.cloud import secretmanager
import urllib.parse

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_secret(secret_name, project_id=None):
    """Retrieve secret from Google Cloud Secret Manager."""
    if project_id is None:
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'rl-prod-471116')

    try:
        client = secretmanager.SecretManagerServiceClient()
        secret_path = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": secret_path})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.warning(f"Could not get secret '{secret_name}' from Secret Manager: {e}")
        return None

def get_config_value(env_var_name, secret_name=None, fallback=None):
    """Get configuration value from environment variable, then secret manager, then fallback."""
    # Try environment variable first
    value = os.getenv(env_var_name)
    if value:
        return value

    # Try secret manager if secret_name provided
    if secret_name:
        value = get_secret(secret_name)
        if value:
            return value

    # Return fallback
    return fallback

# Configuration
DATABASE_URL = get_config_value("DATABASE_URL_LOCAL") or get_config_value("DATABASE_URL", "database-connection-string")
DISCORD_CLIENT_ID = get_config_value("DISCORD_CLIENT_ID", "discord-client-id")
DISCORD_CLIENT_SECRET = get_config_value("DISCORD_CLIENT_SECRET", "discord-client-secret")
DISCORD_REDIRECT_URI = get_config_value("DISCORD_REDIRECT_URI", fallback="http://dev.redlegion.gg/api/auth/discord/callback")
FRONTEND_URL = get_config_value("FRONTEND_URL", fallback="http://dev.redlegion.gg")

# Log configuration status (without exposing secrets)
logger.info(f"DATABASE_URL: {'✓' if DATABASE_URL else '✗'}")
logger.info(f"DISCORD_CLIENT_ID: {'✓' if DISCORD_CLIENT_ID else '✗'}")
logger.info(f"DISCORD_CLIENT_SECRET: {'✓' if DISCORD_CLIENT_SECRET else '✗'}")
logger.info(f"DISCORD_REDIRECT_URI: {DISCORD_REDIRECT_URI}")
logger.info(f"FRONTEND_URL: {FRONTEND_URL}")

# Global database pool
db_pool = None

def _get_db_password_from_secrets() -> str:
    """Get database password from Google Secrets Manager (same as Discord bot)."""
    try:
        # Initialize the client
        client = secretmanager.SecretManagerServiceClient()

        # Get project ID from environment or use default
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'rl-prod-471116')

        # Use the correct secret name for database password (same as bot)
        secret_name = "db-password"
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"

        # Access the secret version
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")

    except Exception as e:
        logger.error(f"Error getting database password from secrets: {e}")
        raise

def resolve_database_url() -> str:
    """
    Resolve database URL using the same approach as Discord bot.
    """
    try:
        # Known Cloud SQL configuration (same as bot)
        CLOUD_SQL_INTERNAL_IP = "10.92.0.3"
        CLOUD_SQL_USERNAME = "arccorp_sys_admin"

        # Get password from Google Secrets Manager
        password = _get_db_password_from_secrets()

        # URL-encode the password to handle special characters (same as bot)
        encoded_password = urllib.parse.quote(password, safe='')

        # Use original port or default to 5432
        port = 5432

        # Get database name
        database_name = 'red_legion_arccorp_data_store'
        resolved_url = f"postgresql://{CLOUD_SQL_USERNAME}:{encoded_password}@{CLOUD_SQL_INTERNAL_IP}:{port}/{database_name}"

        logger.info(f"Database URL resolved: postgresql://{CLOUD_SQL_USERNAME}:***@{CLOUD_SQL_INTERNAL_IP}:{port}/{database_name}")
        return resolved_url

    except Exception as e:
        logger.error(f"Error resolving database URL: {e}")
        raise

async def get_db_pool():
    """Get database connection pool using Discord bot's proven approach."""
    global db_pool
    if db_pool is None:
        try:
            # Use the same database connection approach as the Discord bot
            database_url = resolve_database_url()
            logger.info("Using Discord bot's database connection approach")

            db_pool = await asyncpg.create_pool(database_url)
            logger.info("Database connection pool created successfully")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            logger.warning("Falling back to dummy data mode")
            return None
    return db_pool

# Create FastAPI app
app = FastAPI(title="Red Legion - Enhanced OAuth Backend with Database")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# In-memory session store (simple for now)
user_sessions = {}

# ================================
# AUTHENTICATION ENDPOINTS (from clean_main.py)
# ================================

@app.get("/")
async def root():
    return {
        "message": "Red Legion Enhanced OAuth Backend",
        "status": "ok",
        "database": "connected" if await get_db_pool() else "disconnected"
    }

@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "Enhanced backend responding"}

@app.get("/health")
async def health():
    db_status = "connected" if await get_db_pool() else "disconnected"
    return {
        "status": "healthy",
        "mode": "enhanced",
        "database": db_status,
        "active_sessions": len(user_sessions)
    }

@app.get("/auth/discord")
async def discord_login():
    """Start Discord OAuth flow."""
    if not DISCORD_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Discord client ID not configured")

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)

    discord_auth_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={DISCORD_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify"
        f"&state={state}"
    )

    return RedirectResponse(discord_auth_url)

@app.get("/auth/discord/callback")
async def discord_callback(code: str = None, state: str = None, error: str = None):
    """Handle Discord OAuth callback."""
    logger.info("=== OAuth Callback ===")
    logger.info(f"Code: {'✓' if code else '✗'}")
    logger.info(f"State: {state}")
    logger.info(f"Error: {error}")

    if error:
        logger.error(f"OAuth error: {error}")
        return RedirectResponse(f"{FRONTEND_URL}?error={error}")

    if not code:
        logger.error("No authorization code received")
        return RedirectResponse(f"{FRONTEND_URL}?error=no_code")

    # Exchange code for access token
    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://discord.com/api/oauth2/token",
                data={
                    "client_id": DISCORD_CLIENT_ID,
                    "client_secret": DISCORD_CLIENT_SECRET,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": DISCORD_REDIRECT_URI,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if token_response.status_code != 200:
                logger.error(f"Token exchange failed: {token_response.status_code} - {token_response.text}")
                return RedirectResponse(f"{FRONTEND_URL}?error=token_exchange_failed")

            token_data = token_response.json()
            access_token = token_data.get("access_token")

            if not access_token:
                return RedirectResponse(f"{FRONTEND_URL}?error=no_access_token")

            # Get user info from Discord
            user_response = await client.get(
                "https://discord.com/api/users/@me",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if user_response.status_code != 200:
                logger.error(f"User info failed: {user_response.status_code} - {user_response.text}")
                return RedirectResponse(f"{FRONTEND_URL}?error=user_info_failed")

            user_data = user_response.json()
            user_id = user_data.get("id")
            username = user_data.get("username")

            if not user_id:
                return RedirectResponse(f"{FRONTEND_URL}?error=no_user_id")

            # Create simple session
            session_token = secrets.token_urlsafe(32)
            user_sessions[session_token] = {
                "user_id": user_id,
                "username": username,
                "access_token": access_token,
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            logger.info(f"✓ Session created for user {username} ({user_id})")
            logger.info(f"✓ Session token: {session_token[:8]}...")
            logger.info(f"✓ Total sessions: {len(user_sessions)}")

            # Redirect to frontend with session token
            response = RedirectResponse(f"{FRONTEND_URL}?token={session_token}")
            response.set_cookie("session_token", session_token, httponly=True, max_age=86400)  # 24 hours
            return response

    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return RedirectResponse(f"{FRONTEND_URL}?error=callback_failed")

@app.get("/auth/user")
async def get_user(request: Request):
    """Get current user info."""
    # Get session token from cookie or query param
    session_token = request.cookies.get("session_token") or request.query_params.get("token")

    if not session_token or session_token not in user_sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = user_sessions[session_token]
    return {
        "user_id": session["user_id"],
        "username": session["username"],
        "authenticated": True
    }

@app.post("/auth/logout")
async def logout(request: Request):
    """Logout user."""
    session_token = request.cookies.get("session_token")

    if session_token and session_token in user_sessions:
        del user_sessions[session_token]

    response = JSONResponse({"message": "Logged out"})
    response.delete_cookie("session_token")
    return response

# ================================
# AUTHENTICATION HELPER
# ================================

async def get_current_user(request: Request) -> dict:
    """Get current authenticated user from session."""
    session_token = request.cookies.get("session_token") or request.query_params.get("token")

    if not session_token or session_token not in user_sessions:
        raise HTTPException(status_code=401, detail="Authentication required")

    return user_sessions[session_token]

# ================================
# APPLICATION ENDPOINTS
# ================================

@app.get("/events")
async def get_events(request: Request, current_user: dict = Depends(get_current_user)):
    """Get all mining events from database."""
    try:
        pool = await get_db_pool()
        if pool is None:
            # Return dummy data when no database connection
            logger.warning("No database connection - returning dummy events data")
            return [
                {
                    "event_id": "test-event-1",
                    "event_name": "Test Mining Op Alpha",
                    "event_type": "mining",
                    "event_status": "completed",
                    "start_time": "2024-01-15T19:00:00Z",
                    "end_time": "2024-01-15T22:00:00Z",
                    "participant_count": 12,
                    "total_earnings": 450000
                },
                {
                    "event_id": "test-event-2",
                    "event_name": "Test Mining Op Beta",
                    "event_type": "mining",
                    "event_status": "live",
                    "start_time": "2024-01-16T20:00:00Z",
                    "end_time": None,
                    "participant_count": 8,
                    "total_earnings": 0
                }
            ]

        async with pool.acquire() as conn:
            events = await conn.fetch("""
                SELECT
                    event_id, event_name, event_type, event_status,
                    start_time, end_time, participant_count, total_earnings
                FROM mining_events
                ORDER BY start_time DESC
            """)
            return [dict(event) for event in events]

    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        # Return dummy data on database errors
        return []

@app.get("/events/scheduled")
async def get_scheduled_events(request: Request, current_user: dict = Depends(get_current_user)):
    """Get all scheduled events (event_status = 'scheduled')."""
    try:
        pool = await get_db_pool()
        if pool is None:
            logger.warning("No database connection - returning dummy scheduled events data")
            return [
                {
                    "event_id": "sch-demo01",
                    "event_name": "Sunday Mining Session",
                    "event_type": "mining",
                    "scheduled_start_time": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                    "organizer_name": "Red Legion Admin",
                    "event_status": "scheduled",
                    "auto_start_enabled": True
                }
            ]

        async with pool.acquire() as conn:
            events = await conn.fetch("""
                SELECT event_id, event_name, event_type, organizer_name,
                       scheduled_start_time, auto_start_enabled, event_status,
                       tracked_channels, primary_channel_id, created_at
                FROM events
                WHERE event_status = 'scheduled'
                ORDER BY scheduled_start_time ASC
            """)
            return [dict(event) for event in events]

    except Exception as e:
        logger.error(f"Error fetching scheduled events: {e}")
        return []

@app.get("/discord/channels")
async def get_discord_channels(request: Request, current_user: dict = Depends(get_current_user)):
    """Get Discord channels from database."""
    try:
        pool = await get_db_pool()
        if pool is None:
            logger.warning("No database connection - returning dummy channels data")
            return [
                {
                    "channel_id": "814699481912049707",
                    "channel_name": "mining-ops",
                    "channel_type": "GUILD_VOICE"
                },
                {
                    "channel_id": "814699481912049708",
                    "channel_name": "general-voice",
                    "channel_type": "GUILD_VOICE"
                }
            ]

        async with pool.acquire() as conn:
            channels = await conn.fetch("""
                SELECT channel_id, channel_name, channel_type
                FROM discord_channels
                WHERE channel_type = 'GUILD_VOICE'
                ORDER BY channel_name
            """)
            return [dict(channel) for channel in channels]

    except Exception as e:
        logger.error(f"Error fetching Discord channels: {e}")
        return []

@app.get("/uex-prices")
async def get_uex_prices(request: Request, current_user: dict = Depends(get_current_user)):
    """Get UEX price data."""
    try:
        pool = await get_db_pool()
        if pool is None:
            logger.warning("No database connection - returning dummy UEX prices")
            return {
                "prices": {
                    "Quantanium": {"buy_price": 8.77, "sell_price": 8.77},
                    "Laranite": {"buy_price": 6.15, "sell_price": 6.15},
                    "Bexalite": {"buy_price": 5.25, "sell_price": 5.25}
                },
                "last_updated": datetime.now(timezone.utc).isoformat()
            }

        async with pool.acquire() as conn:
            prices = await conn.fetch("""
                SELECT material_name, buy_price, sell_price, last_updated
                FROM uex_prices
                ORDER BY material_name
            """)

            price_dict = {}
            for price in prices:
                price_dict[price['material_name']] = {
                    "buy_price": price['buy_price'],
                    "sell_price": price['sell_price']
                }

            return {
                "prices": price_dict,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }

    except Exception as e:
        logger.error(f"Error fetching UEX prices: {e}")
        return {"prices": {}, "last_updated": datetime.now(timezone.utc).isoformat()}

@app.get("/trading-locations")
async def get_trading_locations(request: Request, current_user: dict = Depends(get_current_user)):
    """Get trading locations."""
    try:
        pool = await get_db_pool()
        if pool is None:
            logger.warning("No database connection - returning dummy trading locations")
            return [
                {
                    "location_id": "area18",
                    "location_name": "Area 18",
                    "system": "Stanton",
                    "planet": "ArcCorp"
                },
                {
                    "location_id": "grim-hex",
                    "location_name": "Grim Hex",
                    "system": "Stanton",
                    "planet": "Yela"
                }
            ]

        async with pool.acquire() as conn:
            locations = await conn.fetch("""
                SELECT location_id, location_name, system, planet
                FROM trading_locations
                ORDER BY location_name
            """)
            return [dict(location) for location in locations]

    except Exception as e:
        logger.error(f"Error fetching trading locations: {e}")
        return []

# ================================
# STARTUP/SHUTDOWN HANDLERS
# ================================

@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup."""
    try:
        await get_db_pool()
        logger.info("Startup complete - enhanced backend ready")
    except Exception as e:
        logger.warning(f"Startup warning: {e}. Continuing with dummy data.")

@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown."""
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("Database connection pool closed")

# ================================
# DEBUG ENDPOINTS
# ================================

@app.get("/debug/sessions")
async def debug_sessions():
    """Debug endpoint to see active sessions."""
    return {
        "active_sessions": len(user_sessions),
        "sessions": [
            {
                "token": token[:8] + "...",
                "user_id": data["user_id"],
                "username": data["username"],
                "created_at": data["created_at"]
            }
            for token, data in user_sessions.items()
        ]
    }

if __name__ == "__main__":
    logger.info("Starting Enhanced Discord OAuth Backend with Database...")
    uvicorn.run(app, host="0.0.0.0", port=8000)