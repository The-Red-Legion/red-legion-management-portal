"""
Red Legion Web Payroll - FastAPI Backend
Simple web interface for Discord bot payroll system
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel, Field, field_validator
import os
import sys
import asyncpg
import httpx
from dotenv import load_dotenv
from google.cloud import secretmanager
from typing import List, Dict, Optional, Any
import logging
import random
import string
import secrets
from datetime import datetime, timedelta, timezone
import io
import json
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

# Discord bot integration
from services.discord_integration import (
    trigger_voice_tracking_on_event_start,
    trigger_voice_tracking_on_event_stop,
    get_discord_bot_status
)

# Discord API client
from services.discord_api import sync_discord_channels_to_db
from validation import (
    validate_discord_id, validate_event_id, validate_text_input,
    validate_positive_integer, validate_decimal_amount,
    EventCreateRequest, PayrollCalculateRequest, ChannelAddRequest,
    validate_pagination_params, log_validation_attempt
)
from session_manager import SessionManager, SessionData, SecurityConfig, get_session_manager

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

# FastAPI app
app = FastAPI(
    title="Red Legion Web Payroll",
    description="Web interface for Discord bot payroll system",
    version="1.0.0"
)

# Add graceful shutdown handling for session manager
@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully shutdown application components."""
    logger.info("Shutting down application...")
    await session_manager.shutdown()
    logger.info("Session manager shutdown complete")


# Configuration with proper secret management
DATABASE_URL = get_config_value("DATABASE_URL_LOCAL") or get_config_value("DATABASE_URL", "database-connection-string")
DISCORD_CLIENT_ID = get_config_value("DISCORD_CLIENT_ID", "discord-client-id")
DISCORD_CLIENT_SECRET = get_config_value("DISCORD_CLIENT_SECRET", "discord-client-secret")
DISCORD_REDIRECT_URI = get_config_value("DISCORD_REDIRECT_URI")
FRONTEND_URL = get_config_value("FRONTEND_URL", fallback="http://localhost:5173")
BOT_API_URL = get_config_value("BOT_API_URL", fallback="http://10.128.0.2:8001")

# Log configuration status (without exposing secrets)
logger.info(f"Configuration loaded - DATABASE_URL: {'✓' if DATABASE_URL else '✗'}")
logger.info(f"Configuration loaded - DISCORD_CLIENT_ID: {'✓' if DISCORD_CLIENT_ID else '✗'}")
logger.info(f"Configuration loaded - DISCORD_CLIENT_SECRET: {'✓' if DISCORD_CLIENT_SECRET else '✗'}")
logger.info(f"Configuration loaded - FRONTEND_URL: {FRONTEND_URL}")

# Validate critical configuration
if not DATABASE_URL:
    logger.error("DATABASE_URL not configured - required for operation")
if not DISCORD_CLIENT_ID:
    logger.error("DISCORD_CLIENT_ID not configured - required for OAuth")
if not DISCORD_CLIENT_SECRET:
    logger.error("DISCORD_CLIENT_SECRET not configured - required for OAuth")

# Discord role-based access control constants
RED_LEGION_GUILD_ID = "814699481912049704"
ADMIN_ROLE_ID = "814699701861220412"
DEVELOPER_TEAM_ROLE_ID = "1412561382834180137"
ORG_LEADERS_ROLE_ID = "1130629722070585396"
ALLOWED_ROLE_IDS = {ADMIN_ROLE_ID, DEVELOPER_TEAM_ROLE_ID, ORG_LEADERS_ROLE_ID}

# OAuth state storage (in production, use Redis or database)
oauth_states = {}

async def check_user_guild_roles(access_token: str) -> tuple[bool, list]:
    """Check if user has required roles in Red Legion guild."""
    try:
        async with httpx.AsyncClient() as client:
            # Get user's guilds to check Red Legion membership
            guilds_response = await client.get(
                "https://discord.com/api/users/@me/guilds",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if guilds_response.status_code != 200:
                logger.error(f"Failed to fetch user guilds: {guilds_response.status_code}")
                return False, []
            
            guilds = guilds_response.json()
            red_legion_guild = None
            
            # Check if user is in Red Legion guild
            for guild in guilds:
                if guild["id"] == RED_LEGION_GUILD_ID:
                    red_legion_guild = guild
                    break
            
            if not red_legion_guild:
                logger.info("User not in Red Legion guild")
                return False, []
                
            logger.info(f"User is member of Red Legion guild, checking specific roles...")
            
            # Get user info first to get user ID
            user_response = await client.get(
                "https://discord.com/api/users/@me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if user_response.status_code != 200:
                logger.error(f"Failed to fetch user info: {user_response.status_code}")
                return False, []
            
            user_data = user_response.json()
            user_id = user_data['id']
            
            # Query database for user roles instead of using bot API
            try:
                pool = await get_db_pool()
                if pool:
                    async with pool.acquire() as conn:
                        # Query guild_memberships table for user roles
                        membership = await conn.fetchrow("""
                            SELECT roles, is_active, nickname
                            FROM guild_memberships 
                            WHERE user_id = $1 
                              AND guild_id = $2 
                              AND is_active = true
                        """, user_id, RED_LEGION_GUILD_ID)
                        
                        if membership and membership['roles']:
                            user_roles = membership['roles']  # This should be a list/array
                            logger.info(f"Database returned roles for {user_data['username']}: {user_roles}")
                            
                            # Check if user has any of the allowed roles
                            for role_id in user_roles:
                                role_id_str = str(role_id)  # Ensure string comparison
                                if role_id_str in ALLOWED_ROLE_IDS:
                                    logger.info(f"User has allowed role: {role_id_str}")
                                    
                                    # Determine role names for session
                                    roles = ["member"]
                                    if role_id_str == ADMIN_ROLE_ID:
                                        roles.append("admin")
                                    if role_id_str == DEVELOPER_TEAM_ROLE_ID:
                                        roles.append("developer")
                                    if role_id_str == ORG_LEADERS_ROLE_ID:
                                        roles.append("org_leader")
                                        
                                    return True, roles
                            
                            logger.info(f"User has roles {user_roles} but none are in allowed list {list(ALLOWED_ROLE_IDS)}")
                            return False, []
                        else:
                            logger.info(f"No active guild membership found for user {user_data['username']} in database")
                            
                else:
                    logger.warning("Database pool not available, falling back to guild permissions")
                    
            except Exception as db_error:
                logger.warning(f"Database error: {db_error}, falling back to guild permissions")
            
            # Fallback: Check Discord guild permissions if bot API is unavailable
            permissions = int(red_legion_guild.get("permissions", 0))
            has_admin_perms = bool(permissions & 0x8) or bool(permissions & 0x20)
            
            logger.info(f"User permissions in guild: {permissions} (binary: {bin(permissions)})")
            logger.info(f"Admin check: permissions & 0x8 = {permissions & 0x8}, permissions & 0x20 = {permissions & 0x20}")
            
            if has_admin_perms:
                logger.info("User has admin permissions in Red Legion guild (fallback)")
                return True, ["admin", "member"]
            else:
                # Since you have the correct roles but bot API is unavailable,
                # temporarily allow access for Red Legion guild members
                # TODO: Remove this once bot API is working
                logger.info("User is Red Legion guild member - temporarily granting access until bot API is fixed")
                return True, ["member"]
                
    except Exception as e:
        logger.error(f"Error checking user roles: {e}")
        return False, []

# CORS configuration - environment aware
cors_origins = [
    "http://localhost:5173", 
    "http://127.0.0.1:5173", 
    "http://localhost:5174", 
    "http://127.0.0.1:5174",
    "https://dev.redlegion.gg",
    "http://dev.redlegion.gg"
]
if FRONTEND_URL and FRONTEND_URL not in cors_origins:
    cors_origins.append(FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# Pydantic models
class PayrollCalculationRequest(BaseModel):
    ore_quantities: Dict[str, float] = Field(..., description="Ore type to SCU quantity mapping")
    custom_prices: Optional[Dict[str, float]] = Field(None, description="Custom price overrides")
    donating_users: Optional[List[str]] = Field(None, description="Users donating to guild")

    @field_validator('ore_quantities')
    def validate_ore_quantities(cls, v):
        if not isinstance(v, dict):
            raise ValueError("Ore quantities must be a dictionary")

        for ore_type, quantity in v.items():
            if not isinstance(ore_type, str) or len(ore_type) < 2 or len(ore_type) > 50:
                raise ValueError(f"Invalid ore type: {ore_type}")

            if not isinstance(quantity, (int, float)) or quantity < 0 or quantity > 10000:
                raise ValueError(f"Invalid quantity for {ore_type}: must be 0-10000")

        return v

    @field_validator('donating_users')
    def validate_donating_users(cls, v):
        if v is not None:
            for user_id in v:
                if not isinstance(user_id, str) or not user_id.isdigit() or len(user_id) < 17 or len(user_id) > 19:
                    raise ValueError(f"Invalid Discord user ID: {user_id}")
        return v

class EventCreationRequest(BaseModel):
    event_name: str = Field(..., min_length=3, max_length=100, description="Event name")
    organizer_name: str = Field(..., min_length=2, max_length=50, description="Organizer name")
    organizer_id: Optional[str] = Field(None, pattern=r'^\d{17,19}$', description="Discord organizer ID")
    guild_id: Optional[str] = Field("814699481912049704", pattern=r'^\d{17,19}$', description="Discord guild ID")
    event_type: str = Field("mining", pattern=r'^(mining|salvage|combat|training)$', description="Event type")
    location_notes: Optional[str] = Field(None, max_length=500, description="Location notes")
    session_notes: Optional[str] = Field(None, max_length=1000, description="Session notes")
    scheduled_start_time: Optional[datetime] = Field(None, description="Scheduled start time")
    auto_start_enabled: bool = Field(False, description="Auto-start enabled")
    tracked_channels: Optional[List[Dict[str, Any]]] = Field(None, description="Tracked Discord channels")
    primary_channel_id: Optional[int] = Field(None, ge=100000000000000000, le=999999999999999999, description="Primary Discord channel ID")

    @field_validator('tracked_channels')
    def validate_tracked_channels(cls, v):
        if v is not None:
            if len(v) > 20:
                raise ValueError("Too many tracked channels (max 20)")

            for channel in v:
                if not isinstance(channel, dict):
                    raise ValueError("Each tracked channel must be a dictionary")

                if 'id' not in channel or not isinstance(channel['id'], int):
                    raise ValueError("Each channel must have a valid 'id' field")

                if channel['id'] < 100000000000000000 or channel['id'] > 999999999999999999:
                    raise ValueError(f"Invalid Discord channel ID: {channel['id']}")

        return v

# Database connection pool
db_pool = None

# Initialize secure session manager with error handling
try:
    session_manager = SessionManager(SecurityConfig(
        session_timeout_hours=24,
        max_concurrent_sessions=3,
        require_same_ip=False,  # Disabled for development, enable in production
        require_same_user_agent=False,  # Disabled for development
        cleanup_interval_minutes=30,
        enable_session_fingerprinting=True
    ))
    logger.info("Session manager initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize session manager: {e}")
    # Create fallback session manager with minimal config
    session_manager = SessionManager()
    logger.warning("Using fallback session manager configuration")

# Authentication dependencies
async def get_current_user(request: Request) -> SessionData:
    """Dependency to get current authenticated user from session."""

    # Check for session token in cookies
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Validate session using secure session manager
    session_data = await session_manager.validate_session(session_token, request)
    return session_data

async def get_admin_user(current_user: SessionData = Depends(get_current_user)) -> SessionData:
    """Dependency to ensure user has admin privileges."""
    if "admin" not in current_user.roles:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )
    return current_user

# In-memory storage for mock events (when database is not available)
# Shared mock events storage
mock_events = []
mock_events_initialized = False

def get_shared_mock_events():
    """Get or initialize shared mock events data."""
    global mock_events, mock_events_initialized
    from datetime import datetime, timedelta
    
    # Initialize with default events only once
    if not mock_events_initialized:
        mock_events = [
            {
                'event_id': 'evt_001',
                'event_name': 'Sunday Mining Operation',
                'event_type': 'mining',
                'organizer_name': 'CommanderRed',
                'started_at': (datetime.now() - timedelta(hours=4)).isoformat(),
                'ended_at': (datetime.now() - timedelta(hours=2)).isoformat(),
                'total_duration_minutes': 120,
                'participant_count': 8,
                'total_participants': 8,
                'status': 'completed',
                'has_payroll': False
            }
        ]
        mock_events_initialized = True
    
    return mock_events

async def get_db_pool():
    """Get database connection pool."""
    global db_pool
    if db_pool is None:
        try:
            db_pool = await asyncpg.create_pool(DATABASE_URL)
        except Exception as e:
            logger.warning(f"Database connection failed in get_db_pool: {e}")
            return None
    return db_pool

@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup."""
    try:
        await get_db_pool()
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.warning(f"Database connection failed: {e}. Continuing without database.")
        global db_pool
        db_pool = None

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown."""
    if db_pool:
        await db_pool.close()
        logger.info("Database connection pool closed")

# Routes

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Red Legion Web Payroll API", "version": "1.0.0"}

@app.get("/auth/login")
async def discord_login():
    """Redirect to Discord OAuth."""
    # Check if Discord OAuth is properly configured
    if not DISCORD_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Discord OAuth not configured: Missing DISCORD_CLIENT_ID")
    if not DISCORD_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Discord OAuth not configured: Missing DISCORD_REDIRECT_URI")

    # Generate CSRF state token
    state = secrets.token_urlsafe(32)
    oauth_states[state] = {
        'created_at': datetime.now(timezone.utc),
        'expires_at': datetime.now(timezone.utc) + timedelta(minutes=10)
    }

    discord_auth_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={DISCORD_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify%20guilds"
        f"&state={state}"
    )

    logger.info(f"Discord OAuth redirect URL: {discord_auth_url}")
    return RedirectResponse(discord_auth_url)

@app.get("/auth/discord/callback")
async def discord_callback(request: Request, code: str, state: str = None):
    """Handle Discord OAuth callback."""
    # Validate OAuth parameters
    if not code or len(code) > 200:  # Discord auth codes are typically shorter
        raise HTTPException(status_code=400, detail="Invalid authorization code")

    if state:
        validate_text_input(state, "OAuth state", min_length=10, max_length=100)

    try:
        # Validate CSRF state token
        if not state or state not in oauth_states:
            logger.error("Invalid or missing OAuth state parameter")
            raise HTTPException(status_code=400, detail="Invalid OAuth state")

        # Check if state has expired
        state_data = oauth_states[state]
        if datetime.now(timezone.utc) > state_data['expires_at']:
            del oauth_states[state]
            logger.error("OAuth state has expired")
            raise HTTPException(status_code=400, detail="OAuth state expired")

        # Remove used state
        del oauth_states[state]

        # Validate Discord OAuth configuration
        if not DISCORD_CLIENT_SECRET:
            raise HTTPException(status_code=500, detail="Discord OAuth not configured: Missing DISCORD_CLIENT_SECRET")

        logger.info(f"Discord OAuth callback received with code: {code[:10]}... and valid state")
        
        # Exchange code for access token
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
                logger.error(f"Discord token exchange failed: {token_response.status_code} - {token_response.text}")
                raise HTTPException(status_code=400, detail="Discord token exchange failed")
                
            token_data = token_response.json()
            logger.info("Discord token exchange successful")
            
            # Get user info
            user_response = await client.get(
                "https://discord.com/api/users/@me",
                headers={"Authorization": f"Bearer {token_data['access_token']}"}
            )
            user_data = user_response.json()
            
            # Check if user has required roles in Red Legion guild
            has_access, roles = await check_user_guild_roles(token_data['access_token'])
            
            if not has_access:
                # Redirect to access denied page
                return RedirectResponse(f"{FRONTEND_URL}/access-denied")
            
        # Create secure session using session manager
        session_token, session_data = await session_manager.create_session(
            user_id=user_data['id'],
            username=user_data['username'],
            access_token=token_data['access_token'],
            roles=roles,
            request=request
        )
        
        # Create response with secure cookie and redirect to events page
        response = RedirectResponse(f"{FRONTEND_URL}/events")
        response.set_cookie(
            key="session_token",
            value=session_token,
            max_age=24*60*60,  # 24 hours
            httponly=True,
            secure=True if FRONTEND_URL.startswith('https') else False,
            samesite="lax"
        )
        return response
        
    except Exception as e:
        logger.error(f"Discord auth error: {e}")
        raise HTTPException(status_code=400, detail="Authentication failed")

@app.get("/auth/logout")
async def logout(request: Request):
    """Handle logout and redirect to logout confirmation page."""
    # Get session token and invalidate it using session manager
    session_token = request.cookies.get("session_token")
    if session_token:
        await session_manager.invalidate_session(session_token)
        logger.info("User session invalidated on logout")

    # Create response with cleared cookie
    response = RedirectResponse(f"{FRONTEND_URL}/logout-confirmation")
    response.delete_cookie("session_token")
    return response

@app.get("/auth/user")
async def get_current_user_info(current_user: SessionData = Depends(get_current_user)):
    """Get current user info - requires authentication."""
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "roles": current_user.roles
    }

@app.get("/events")
async def get_events(current_user: SessionData = Depends(get_current_user)):
    """Get all mining events from database."""
    try:
        pool = await get_db_pool()
        if pool is None:
            # Return mock data when database is not available
            return get_shared_mock_events()
        
        async with pool.acquire() as conn:
            # Query events table with real-time participant count for live events
            events = await conn.fetch("""
                SELECT 
                    e.event_id, 
                    e.event_name, 
                    e.organizer_name, 
                    e.event_type,
                    e.started_at, 
                    CASE 
                        WHEN e.ended_at IS NULL THEN 
                            ROUND(EXTRACT(EPOCH FROM (NOW() - e.started_at)) / 60)
                        ELSE e.total_duration_minutes 
                    END as total_duration_minutes,
                    CASE 
                        WHEN e.ended_at IS NULL THEN (
                            SELECT COUNT(DISTINCT p.user_id) 
                            FROM participation p 
                            WHERE p.event_id = e.event_id 
                            AND p.left_at IS NULL 
                            AND p.was_active = true
                        )
                        ELSE e.total_participants 
                    END as participant_count,
                    e.system_location, 
                    e.planet_moon, 
                    e.location_notes,
                    e.ended_at,
                    e.event_status
                FROM events e
                WHERE (e.event_id LIKE 'sm-%' OR e.event_id LIKE 'web-%')
                ORDER BY e.started_at DESC 
                LIMIT 50
            """)
            
            return [dict(event) for event in events]
            
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error")

@app.get("/discord/channels")
async def get_discord_channels(guild_id: str = "814699481912049704", current_user: SessionData = Depends(get_current_user)):
    """Get all available Discord voice channels for the guild."""
    # Validate guild ID format
    guild_id = validate_discord_id(guild_id, "Guild ID")
    log_validation_attempt("get_discord_channels", current_user.user_id, {"guild_id": guild_id})

    try:
        pool = await get_db_pool()
        if pool is None:
            # Return fallback channels when database is not available
            fallback_channels = [
                {"id": "123456789", "name": "🎤 General Voice", "type": "voice", "category": "general"},
                {"id": "123456790", "name": "⛏️ Mining Alpha", "type": "voice", "category": "mining"},
                {"id": "123456791", "name": "⛏️ Mining Beta", "type": "voice", "category": "mining"},
                {"id": "123456792", "name": "🔧 Salvage Ops", "type": "voice", "category": "salvage"},
                {"id": "123456793", "name": "⚔️ Combat Wing", "type": "voice", "category": "combat"},
                {"id": "123456794", "name": "🚀 Exploration", "type": "voice", "category": "general"},
                {"id": "814699481912049709", "name": "🎥 Stream/Restricted", "type": "voice", "category": "restricted"}
            ]
            return {
                "channels": fallback_channels,
                "total_count": len(fallback_channels),
                "guild_id": guild_id,
                "note": "Using fallback data - database unavailable"
            }
        
        async with pool.acquire() as conn:
            # Try to get channels from new comprehensive discord_channels table
            try:
                channels_data = await conn.fetch("""
                    SELECT 
                        channel_id,
                        channel_name,
                        channel_type,
                        channel_purpose,
                        category_name,
                        is_active,
                        is_trackable,
                        last_seen
                    FROM discord_channels 
                    WHERE guild_id = $1 
                      AND is_active = true 
                      AND is_trackable = true 
                      AND channel_type = 'voice'
                    ORDER BY 
                        CASE channel_purpose 
                            WHEN 'mining' THEN 1
                            WHEN 'salvage' THEN 2 
                            WHEN 'combat' THEN 3
                            WHEN 'exploration' THEN 4
                            WHEN 'trading' THEN 5
                            WHEN 'social' THEN 6
                            WHEN 'restricted' THEN 7
                            ELSE 8
                        END,
                        channel_name
                """, int(guild_id))
                
                # Convert to the expected format
                channels = []
                for row in channels_data:
                    channels.append({
                        "id": str(row['channel_id']),
                        "name": row['channel_name'],
                        "type": row['channel_type'],
                        "category": row['channel_purpose'] or 'general',
                        "category_name": row['category_name'],
                        "is_active": row['is_active'],
                        "last_seen": row['last_seen'].isoformat() if row['last_seen'] else None
                    })
                
            except Exception as table_error:
                # Fallback to old mining_channels + participation approach if new table doesn't exist yet
                logger.warning(f"New discord_channels table not available, using fallback: {table_error}")
                
                # Get channels from mining_channels table  
                mining_channels = await conn.fetch("""
                    SELECT DISTINCT channel_id, channel_name 
                    FROM mining_channels 
                    WHERE guild_id = $1 AND is_active = true
                    ORDER BY channel_name
                """, int(guild_id))
                
                # Get channels from participation history
                participation_channels = await conn.fetch("""
                    SELECT DISTINCT channel_id, channel_name
                    FROM participation 
                    WHERE channel_id IS NOT NULL 
                      AND channel_name IS NOT NULL 
                      AND channel_name != ''
                    ORDER BY channel_name
                """)
                
                # Combine and deduplicate channels
                channel_dict = {}
                
                # Add mining channels
                for row in mining_channels:
                    channel_dict[str(row['channel_id'])] = {
                        "id": str(row['channel_id']),
                        "name": row['channel_name'],
                        "type": "voice",
                        "category": "mining",
                        "category_name": "Mining Operations"
                    }
                
                # Add participation channels
                for row in participation_channels:
                    channel_id = str(row['channel_id'])
                    if channel_id not in channel_dict:
                        channel_dict[channel_id] = {
                            "id": channel_id,
                            "name": row['channel_name'],
                            "type": "voice", 
                            "category": "general",
                            "category_name": "General"
                        }
                
                # Add Stream/Restricted channel (private channel bot has access to)
                channel_dict["814699481912049709"] = {
                    "id": "814699481912049709",
                    "name": "🎥 Stream/Restricted",
                    "type": "voice",
                    "category": "restricted",
                    "category_name": "Restricted"
                }
                
                # Convert to list and sort by name
                channels = list(channel_dict.values())
                channels.sort(key=lambda x: x["name"])
            
            return {
                "channels": channels,
                "total_count": len(channels),
                "guild_id": guild_id
            }
                
    except Exception as e:
        logger.error(f"Error fetching Discord channels: {e}")
        # Return fallback channels if database query fails
        fallback_channels = [
            {"id": "123456789", "name": "🎤 General Voice", "type": "voice", "category": "general"},
            {"id": "123456790", "name": "⛏️ Mining Alpha", "type": "voice", "category": "mining"},
            {"id": "123456791", "name": "⛏️ Mining Beta", "type": "voice", "category": "mining"},
            {"id": "123456792", "name": "🔧 Salvage Ops", "type": "voice", "category": "salvage"},
            {"id": "814699481912049709", "name": "🎥 Stream/Restricted", "type": "voice", "category": "restricted"}
        ]
        return {
            "channels": fallback_channels,
            "total_count": len(fallback_channels),
            "guild_id": guild_id,
            "error": str(e),
            "note": "Using fallback data due to database error"
        }

@app.post("/discord/channels/sync")
async def sync_discord_channels(guild_id: str = "814699481912049704", current_user: SessionData = Depends(get_current_user)):
    """Sync Discord channels from Discord API using bot integration."""
    try:
        pool = await get_db_pool()
        if pool is None:
            return {
                "success": False,
                "message": "Database not available",
                "channels_synced": 0
            }
        
        logger.info(f"Starting Discord channel sync for guild {guild_id}")
        
        # Use the Discord API client to fetch and sync real channels
        result = await sync_discord_channels_to_db(guild_id, pool)
        
        logger.info(f"Discord channel sync completed: {result}")
        return result
                
    except Exception as e:
        logger.error(f"Error syncing Discord channels: {e}")
        return {
            "success": False,
            "message": f"Failed to sync channels: {str(e)}",
            "channels_synced": 0
        }

@app.post("/discord/channels/add-restricted")
async def add_restricted_channel(current_user: SessionData = Depends(get_current_user)):
    """Add the Stream/Restricted private channel that the bot has access to."""
    try:
        pool = await get_db_pool()
        if pool is None:
            return {
                "success": False,
                "message": "Database not available",
                "note": "Channel added to fallback lists only"
            }

        async with pool.acquire() as conn:
            # Insert or update the restricted channel
            await conn.execute("""
                INSERT INTO discord_channels (
                    guild_id, channel_id, channel_name, channel_type, 
                    channel_purpose, category_name, is_active, is_trackable, 
                    last_seen, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW(), NOW()
                ) ON CONFLICT (channel_id) DO UPDATE SET 
                    channel_name = EXCLUDED.channel_name,
                    channel_purpose = EXCLUDED.channel_purpose,
                    category_name = EXCLUDED.category_name,
                    is_active = true,
                    is_trackable = true,
                    updated_at = NOW()
            """, 
            814699481912049704,  # guild_id
            814699481912049709,   # channel_id  
            "Stream/Restricted",   # channel_name
            "voice",               # channel_type
            "restricted",          # channel_purpose
            "Restricted",          # category_name
            True,                  # is_active
            True                   # is_trackable
            )

            return {
                "success": True,
                "message": "Stream/Restricted channel added successfully",
                "channel": {
                    "id": "814699481912049709",
                    "name": "Stream/Restricted",
                    "type": "voice",
                    "category": "restricted"
                }
            }

    except Exception as e:
        logger.error(f"Error adding restricted channel: {e}")
        return {
            "success": False,
            "message": f"Failed to add restricted channel: {str(e)}"
        }


@app.post("/discord/channels/cleanup")
async def cleanup_fake_discord_channels(current_user: SessionData = Depends(get_current_user)):
    """Remove fake/sample Discord channels that don't exist in the actual Discord server."""
    try:
        pool = await get_db_pool()
        if pool is None:
            return {
                "success": False,
                "message": "Database not available",
                "channels_removed": 0
            }
        
        async with pool.acquire() as conn:
            # Find fake channels (channels with fake IDs that don't exist in Discord)
            fake_channels = await conn.fetch("""
                SELECT channel_id, channel_name, channel_purpose
                FROM discord_channels 
                WHERE channel_id < 1000000000000000000  -- Real Discord IDs are 18+ digits
                   OR channel_id::text LIKE '999999999999999%'  -- Our sample channels
                ORDER BY channel_name
            """)
            
            logger.info(f"Found {len(fake_channels)} fake channels to remove")
            for channel in fake_channels:
                logger.info(f"  - {channel['channel_name']} (ID: {channel['channel_id']})")
            
            if fake_channels:
                # Remove fake channels
                result = await conn.execute("""
                    DELETE FROM discord_channels 
                    WHERE channel_id < 1000000000000000000
                       OR channel_id::text LIKE '999999999999999%'
                """)
                
                # Get remaining real channels count
                real_count = await conn.fetchval("""
                    SELECT COUNT(*) FROM discord_channels WHERE is_active = true
                """)
                
                logger.info(f"Removed fake channels, {real_count} real channels remaining")
                
                return {
                    "success": True,
                    "message": f"Removed {len(fake_channels)} fake channels",
                    "channels_removed": len(fake_channels),
                    "real_channels_remaining": real_count
                }
            else:
                real_count = await conn.fetchval("""
                    SELECT COUNT(*) FROM discord_channels WHERE is_active = true
                """)
                return {
                    "success": True,
                    "message": "No fake channels found to remove",
                    "channels_removed": 0,
                    "real_channels_remaining": real_count
                }
                
    except Exception as e:
        logger.error(f"Error cleaning up fake Discord channels: {e}")
        return {
            "success": False,
            "message": f"Failed to cleanup fake channels: {str(e)}",
            "channels_removed": 0
        }

@app.get("/events/{event_id}/participants")
async def get_event_participants(event_id: str, current_user: SessionData = Depends(get_current_user)):
    """Get participants for a specific event with real-time duration for live events."""
    # Validate event ID format
    event_id = validate_event_id(event_id)
    log_validation_attempt("get_event_participants", current_user.user_id, {"event_id": event_id})

    try:
        pool = await get_db_pool()
        if pool is None:
            # Return mock data when database is not available
            from datetime import datetime, timedelta
            return [
                {
                    'user_id': 'user_001',
                    'username': 'RedLegionMiner',
                    'participation_minutes': 120,
                    'participation_percentage': 40
                },
                {
                    'user_id': 'user_002',
                    'username': 'SpaceTrucker',
                    'participation_minutes': 90,
                    'participation_percentage': 30
                }
            ]
        
        async with pool.acquire() as conn:
            participants = await conn.fetch("""
                SELECT 
                    user_id, 
                    COALESCE(display_name, username) as username,
                    SUM(
                        CASE 
                            WHEN duration_minutes IS NOT NULL THEN duration_minutes
                            WHEN left_at IS NULL THEN EXTRACT(EPOCH FROM (NOW() - joined_at)) / 60
                            ELSE 0
                        END
                    )::int as participation_minutes
                FROM participation 
                WHERE event_id = $1
                GROUP BY user_id, COALESCE(display_name, username)
                ORDER BY participation_minutes DESC
            """, event_id)
            
            # Calculate percentages after we have the totals
            if participants:
                total_minutes = sum(p['participation_minutes'] for p in participants if p['participation_minutes'])
                result = []
                for participant in participants:
                    participant_dict = dict(participant)
                    participant_dict['user_id'] = str(participant_dict['user_id'])
                    if total_minutes > 0:
                        participant_dict['participation_percentage'] = int((participant_dict['participation_minutes'] / total_minutes) * 100)
                    else:
                        participant_dict['participation_percentage'] = 0
                    result.append(participant_dict)
                return result
            else:
                return []
            
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error")

@app.post("/payroll/{event_id}/calculate")
async def calculate_payroll(event_id: str, request: PayrollCalculationRequest, current_user: SessionData = Depends(get_current_user)):
    """Calculate payroll for an event (simplified version of bot logic)."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Get event data
            event = await conn.fetchrow("""
                SELECT * FROM events WHERE event_id = $1
            """, event_id)
            
            if not event:
                raise HTTPException(status_code=404, detail="Event not found")
            
            # Get participants (aggregate by user to avoid duplicates)
            participants = await conn.fetch("""
                SELECT user_id, COALESCE(display_name, username) as username, 
                       SUM(duration_minutes) as participation_minutes, 
                       (SUM(duration_minutes)::float / NULLIF((SELECT SUM(duration_minutes) FROM participation WHERE event_id = $1), 0) * 100)::int as participation_percentage
                FROM participation 
                WHERE event_id = $1
                GROUP BY user_id, COALESCE(display_name, username)
                ORDER BY SUM(duration_minutes) DESC
            """, event_id)
            
            # Get UEX prices (simplified)
            uex_prices = await get_uex_prices()
            
            # Use custom prices if provided
            prices = request.custom_prices or uex_prices
            
            # Calculate total value and total SCU
            total_value = sum(quantity * prices.get(ore.upper(), 0) for ore, quantity in request.ore_quantities.items())
            total_scu = sum(quantity for quantity in request.ore_quantities.values())
            
            # Calculate individual payouts with donation logic
            donating_users = request.donating_users or []
            donating_user_ids = [str(user_id) for user_id in donating_users]  # Convert to strings for comparison
            
            # Debug logging
            logger.info(f"🔍 Debug - Received donating users: {donating_users}")
            logger.info(f"🔍 Debug - Converted to strings: {donating_user_ids}")
            logger.info(f"🔍 Debug - Participants from DB: {[(p['user_id'], p['username']) for p in participants]}")
            
            # Separate donating and non-donating participants
            non_donating_participants = [p for p in participants if str(p['user_id']) not in donating_user_ids]
            donating_participants = [p for p in participants if str(p['user_id']) in donating_user_ids]
            
            # Debug logging for separation
            logger.info(f"🔍 Debug - Non-donating participants: {[p['username'] for p in non_donating_participants]}")
            logger.info(f"🔍 Debug - Donating participants: {[p['username'] for p in donating_participants]}")
            
            # Calculate total participation minutes for non-donating participants
            total_non_donating_minutes = sum(p['participation_minutes'] or 0 for p in non_donating_participants)
            
            payouts = []
            
            # Calculate payouts for non-donating participants (they get the full pot redistributed)
            if total_non_donating_minutes > 0:
                for participant in non_donating_participants:
                    # Redistribute based on participation time among non-donating participants only
                    participation_mins = participant['participation_minutes'] or 0
                    redistribution_percentage = participation_mins / total_non_donating_minutes
                    individual_payout = total_value * redistribution_percentage
                    
                    payouts.append({
                        'user_id': str(participant['user_id']),
                        'username': participant['username'],
                        'participation_minutes': participation_mins,
                        'participation_percentage': participant['participation_percentage'] or 0,
                        'base_payout_auec': total_value * ((participant['participation_percentage'] or 0) / 100),
                        'final_payout_auec': round(individual_payout, 2)
                    })
            
            # Add donating participants with 0 payout
            for participant in donating_participants:
                base_payout = total_value * ((participant['participation_percentage'] or 0) / 100)
                payouts.append({
                    'user_id': str(participant['user_id']),
                    'username': participant['username'],
                    'participation_minutes': participant['participation_minutes'] or 0,
                    'participation_percentage': participant['participation_percentage'] or 0,
                    'base_payout_auec': base_payout,
                    'final_payout_auec': 0.0
                })
            
            return {
                'event_id': event_id,
                'total_value_auec': total_value,
                'total_scu': total_scu,
                'payouts': payouts,
                'ore_quantities': request.ore_quantities,
                'prices_used': prices,
                'donating_users': donating_users
            }
            
    except Exception as e:
        logger.error(f"Payroll calculation error: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Calculation error")

@app.post("/payroll/{event_id}/finalize")
async def finalize_payroll(event_id: str, request: PayrollCalculationRequest, current_user: SessionData = Depends(get_current_user)):
    """Save payroll calculation to database and mark as completed."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # First get the payroll calculation (reuse the existing calculate logic)
            # We'll call the existing calculate_payroll function to get the data
            import json
            from fastapi.encoders import jsonable_encoder
            
            # Create a temporary request to get calculation data
            temp_request = PayrollCalculationRequest(
                ore_quantities=request.ore_quantities,
                custom_prices=request.custom_prices,
                donating_users=request.donating_users
            )
            
            # Get event data first
            event = await conn.fetchrow("""
                SELECT * FROM events WHERE event_id = $1
            """, event_id)
            
            if not event:
                raise HTTPException(status_code=404, detail="Event not found")
                
            # Check if payroll already exists
            existing_payroll = await conn.fetchrow("""
                SELECT payroll_id FROM payrolls WHERE event_id = $1
            """, event_id)
            
            if existing_payroll:
                raise HTTPException(status_code=400, detail="Payroll already finalized for this event")
            
            # Calculate payroll using the existing endpoint logic (simplified here)
            # Get participants
            participants = await conn.fetch("""
                SELECT user_id, COALESCE(display_name, username) as username, 
                       SUM(duration_minutes) as participation_minutes, 
                       (SUM(duration_minutes)::float / NULLIF((SELECT SUM(duration_minutes) FROM participation WHERE event_id = $1), 0) * 100)::int as participation_percentage
                FROM participation 
                WHERE event_id = $1
                GROUP BY user_id, COALESCE(display_name, username)
                ORDER BY SUM(duration_minutes) DESC
            """, event_id)
            
            # Get prices and calculate total value and SCU
            uex_prices = await get_uex_prices()
            prices = request.custom_prices or uex_prices
            total_value = sum(quantity * prices.get(ore.upper(), 0) for ore, quantity in request.ore_quantities.items())
            total_scu = sum(quantity for quantity in request.ore_quantities.values())
            
            # Calculate payouts (simplified version)
            donating_users = request.donating_users or []
            donating_user_ids = [str(user_id) for user_id in donating_users]
            
            non_donating_participants = [p for p in participants if str(p['user_id']) not in donating_user_ids]
            donating_participants = [p for p in participants if str(p['user_id']) in donating_user_ids]
            
            total_non_donating_minutes = sum(p['participation_minutes'] or 0 for p in non_donating_participants)
            
            # Generate payroll ID and session ID
            import random
            import string
            payroll_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            session_id = f"web-{payroll_id}"
            
            # Create payroll session record
            await conn.execute("""
                INSERT INTO payroll_sessions (
                    session_id, user_id, guild_id, event_id, event_type,
                    current_step, ore_quantities, pricing_data, calculation_data,
                    is_completed, custom_prices
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """, session_id, 999999999999999999, 0, event_id, 'mining',
                 'completed', json.dumps(request.ore_quantities), json.dumps(prices),
                 json.dumps({"total_value": total_value}), True, json.dumps(request.custom_prices or {}))
            
            # Insert payroll record
            await conn.execute("""
                INSERT INTO payrolls (
                    payroll_id, event_id, total_scu_collected, total_value_auec,
                    ore_prices_used, mining_yields, calculated_by_id, calculated_by_name
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, payroll_id, event_id, total_scu, total_value,
                 json.dumps(prices), json.dumps(request.ore_quantities),
                 999999999999999999, 'WebApp User')  # TODO: Pass user info from frontend
            
            # Insert individual payouts
            for participant in non_donating_participants:
                participation_mins = participant['participation_minutes'] or 0
                if total_non_donating_minutes > 0:
                    redistribution_percentage = participation_mins / total_non_donating_minutes
                    individual_payout = total_value * redistribution_percentage
                else:
                    individual_payout = 0
                
                base_payout = total_value * ((participant['participation_percentage'] or 0) / 100)
                
                await conn.execute("""
                    INSERT INTO payouts (
                        payroll_id, user_id, username, participation_minutes,
                        base_payout_auec, final_payout_auec, is_donor
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, payroll_id, int(participant['user_id']), participant['username'],
                     participation_mins, base_payout, individual_payout, False)
            
            # Insert donating participants
            for participant in donating_participants:
                base_payout = total_value * ((participant['participation_percentage'] or 0) / 100)
                
                await conn.execute("""
                    INSERT INTO payouts (
                        payroll_id, user_id, username, participation_minutes,
                        base_payout_auec, final_payout_auec, is_donor
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, payroll_id, int(participant['user_id']), participant['username'],
                     participant['participation_minutes'] or 0, base_payout, 0, True)
            
            # Mark event as payroll_calculated
            await conn.execute("""
                UPDATE events 
                SET payroll_calculated = true
                WHERE event_id = $1
            """, event_id)
            
            return {
                'success': True,
                'payroll_id': payroll_id,
                'session_id': session_id,
                'message': f'Payroll {payroll_id} finalized and payroll session {session_id} completed'
            }
            
    except Exception as e:
        logger.error(f"Error finalizing payroll: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to finalize payroll")

@app.get("/uex-prices")
async def get_uex_prices_endpoint(current_user: SessionData = Depends(get_current_user)):
    """Get current UEX ore prices."""
    prices = await get_uex_prices()
    return prices

@app.get("/admin/events")
async def get_all_events(admin_user: SessionData = Depends(get_admin_user)):
    """Get all events with their associated payroll data for management."""
    try:
        pool = await get_db_pool()
        if pool is None:
            # Return mock data when database is not available
            mock_events = get_shared_mock_events()
            
            # Return events with admin fields
            return [
                {
                    **event,
                    'total_participants': event.get('participant_count', event.get('total_participants', 0)),
                    'status': event.get('status', 'completed' if event.get('ended_at') else 'active'),
                    'payroll_calculated': event.get('has_payroll', bool(event.get('ended_at')))
                }
                for event in mock_events
            ]
        
        async with pool.acquire() as conn:
            # Get all events with payroll information
            events = await conn.fetch("""
                SELECT 
                    e.event_id,
                    e.event_type,
                    e.event_name,
                    e.organizer_name,
                    e.organizer_id,
                    e.guild_id,
                    e.started_at,
                    e.ended_at,
                    e.status,
                    e.total_participants,
                    e.total_duration_minutes,
                    e.payroll_calculated,
                    e.location_notes,
                    e.description,
                    e.created_at
                FROM events e
                ORDER BY e.created_at DESC
            """)
            
            return [dict(event) for event in events]
            
    except Exception as e:
        logger.error(f"Error fetching all events: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.delete("/admin/events/{event_id}")
async def delete_event(event_id: str, admin_user: SessionData = Depends(get_admin_user)):
    """Delete an event and all associated data."""
    try:
        pool = await get_db_pool()
        if pool is None:
            # Return mock success response when database is not available
            # Ensure mock_events is initialized
            get_shared_mock_events()
            global mock_events
            
            # Actually remove the event from mock storage
            initial_count = len(mock_events)
            mock_events = [event for event in mock_events if event['event_id'] != event_id]
            final_count = len(mock_events)
            
            if initial_count == final_count:
                raise HTTPException(status_code=404, detail="Event not found")
            
            return {
                'success': True,
                'message': f'Event {event_id} deleted successfully (mock mode)',
                'event_id': event_id
            }
        
        async with pool.acquire() as conn:
            # Start a transaction
            async with conn.transaction():
                # Check if event exists
                event = await conn.fetchrow(
                    "SELECT event_id FROM events WHERE event_id = $1", 
                    event_id
                )
                
                if not event:
                    raise HTTPException(status_code=404, detail="Event not found")
                
                # Delete associated data in correct order (respecting foreign key constraints)
                
                # 1. Delete payouts (references payrolls)
                await conn.execute(
                    "DELETE FROM payouts WHERE payroll_id IN (SELECT payroll_id FROM payrolls WHERE event_id = $1)", 
                    event_id
                )
                
                # 2. Delete payroll_sessions (references events)
                await conn.execute(
                    "DELETE FROM payroll_sessions WHERE event_id = $1", 
                    event_id
                )
                
                # 3. Delete payrolls (references events)
                await conn.execute(
                    "DELETE FROM payrolls WHERE event_id = $1", 
                    event_id
                )
                
                # 4. Delete participation records (references events)
                await conn.execute(
                    "DELETE FROM participation WHERE event_id = $1", 
                    event_id
                )
                
                # 5. Delete salvage inventory if it exists (references events)
                await conn.execute(
                    "DELETE FROM salvage_inventory WHERE event_id = $1", 
                    event_id
                )
                
                # 6. Finally delete the event itself
                await conn.execute(
                    "DELETE FROM events WHERE event_id = $1", 
                    event_id
                )
                
                logger.info(f"Successfully deleted event {event_id} and all associated data")
                return {"success": True, "message": f"Event {event_id} deleted successfully"}
                
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error deleting event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/admin/payroll-summary/{event_id}")
async def get_payroll_summary(event_id: str, admin_user: SessionData = Depends(get_admin_user)):
    """Get detailed payroll summary for an event."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Get event information
            event = await conn.fetchrow("""
                SELECT event_id, event_name, event_type, organizer_name, 
                       started_at, ended_at, total_participants, total_duration_minutes
                FROM events 
                WHERE event_id = $1
            """, event_id)
            
            if not event:
                raise HTTPException(status_code=404, detail="Event not found")
            
            # Get payroll information
            payroll = await conn.fetchrow("""
                SELECT payroll_id, total_value_auec, total_scu_collected, mining_yields, 
                       ore_prices_used, calculated_by_name, calculated_at
                FROM payrolls 
                WHERE event_id = $1
            """, event_id)
            
            if not payroll:
                raise HTTPException(status_code=404, detail="Payroll not found for this event")
            
            # Get individual payouts
            payouts = await conn.fetch("""
                SELECT username, participation_minutes, base_payout_auec, 
                       final_payout_auec, is_donor
                FROM payouts 
                WHERE payroll_id = $1
                ORDER BY final_payout_auec DESC
            """, payroll['payroll_id'])
            
            # Calculate statistics
            total_participation_minutes = sum(p['participation_minutes'] for p in payouts)
            donor_count = sum(1 for p in payouts if p['is_donor'])
            
            # Parse mining_yields and ore_prices JSON if they exist
            import json
            mining_yields = None
            ore_prices = None
            ore_breakdown = None
            
            if payroll['mining_yields']:
                try:
                    mining_yields = json.loads(payroll['mining_yields'])
                except (json.JSONDecodeError, TypeError):
                    mining_yields = None
            
            if payroll['ore_prices_used']:
                try:
                    ore_prices = json.loads(payroll['ore_prices_used'])
                except (json.JSONDecodeError, TypeError):
                    ore_prices = None
            
            # Create ore breakdown with quantities and values
            if mining_yields and ore_prices:
                ore_breakdown = {}
                for ore, quantity in mining_yields.items():
                    if quantity > 0:  # Only include ores that were actually collected
                        price_per_scu = ore_prices.get(ore.upper(), 0)
                        total_value = quantity * price_per_scu
                        ore_breakdown[ore] = {
                            'quantity': quantity,
                            'price_per_scu': price_per_scu,
                            'total_value': total_value
                        }
            
            return {
                "event": dict(event),
                "payroll": dict(payroll),
                "payouts": [dict(p) for p in payouts],
                "statistics": {
                    "total_participants": len(payouts),
                    "total_participation_minutes": total_participation_minutes,
                    "donor_count": donor_count,
                    "total_payout_auec": float(payroll['total_value_auec']),
                    "average_payout_auec": float(payroll['total_value_auec']) / len(payouts) if payouts else 0,
                    "total_scu_collected": payroll['total_scu_collected'],
                    "mining_yields": mining_yields,
                    "ore_breakdown": ore_breakdown
                }
            }
            
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error fetching payroll summary for {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

def create_enhanced_pdf_header(story, event, styles):
    """Create an enhanced PDF header with Red Legion logo and better formatting."""
    import os
    
    # Try to load the Red Legion logo
    logo_path = None
    possible_paths = [
        "../red-legion-website/frontend/public/red-legion-logo.png",
        "../static/red-legion-logo.png",
        "./static/red-legion-logo.png"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            logo_path = path
            break
    
    # Header with logo and title
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        alignment=1,  # Center alignment
        spaceAfter=20,
        backColor=colors.HexColor('#1a1a1a'),  # Dark background
        textColor=colors.white,
        borderPadding=10
    )
    
    if logo_path:
        try:
            # Add logo
            logo = Image(logo_path, width=2*inch, height=2*inch)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 10))
        except Exception as e:
            logger.warning(f"Could not load logo: {e}")
    
    # Red Legion header
    red_legion_style = ParagraphStyle(
        'RedLegionTitle',
        parent=styles['Title'],
        fontSize=20,
        textColor=colors.HexColor('#dc2626'),  # Red color
        alignment=1,
        spaceAfter=5
    )
    story.append(Paragraph("RED LEGION", red_legion_style))
    
    # Event type icon and title
    event_icon = "⛏️ MINING" if event['event_type'] == 'mining' else "🔧 SALVAGE"
    title_style = ParagraphStyle(
        'EnhancedTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        textColor=colors.HexColor('#3b82f6'),  # Blue color
        alignment=1
    )
    title = Paragraph(f"{event_icon} OPERATION PAYROLL REPORT", title_style)
    story.append(title)
    
    # Add a horizontal line
    story.append(Spacer(1, 10))
    line_style = ParagraphStyle(
        'LineStyle',
        parent=styles['Normal'],
        borderWidth=1,
        borderColor=colors.HexColor('#4b5563'),
        spaceAfter=20
    )
    story.append(Paragraph("<hr/>", line_style))
    
    return story

async def generate_pdf_with_playwright(event_data: dict, payroll_data: dict) -> bytes:
    """Generate PDF using Playwright to render HTML template."""
    from playwright.async_api import async_playwright
    from jinja2 import Template
    import os
    from datetime import datetime
    
    # HTML template with Red Legion styling (matching the dark theme)
    html_template = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Payroll Summary</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
            
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                background: #1f2937;
                color: #ffffff;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                min-height: 100vh;
                padding: 18px;
                margin: 0;
            }
            
            .container {
                max-width: 100%;
                width: calc(100% - 36px);
                margin: 0 auto;
                background: #1f2937;
                border-radius: 6px;
                overflow: hidden;
            }
            
            .header {
                background: #374151;
                padding: 10px 15px;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .logo {
                width: 30px;
                height: 30px;
                border-radius: 4px;
                background: #dc2626;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 12px;
                font-weight: bold;
                color: white;
            }
            
            .header-title {
                font-size: 14px;
                font-weight: 700;
                color: #ffffff;
            }
            
            .content {
                padding: 0;
            }
            
            .event-header {
                display: flex;
                align-items: center;
                gap: 5px;
                margin-bottom: 15px;
            }
            
            .event-title {
                font-size: 12px;
                font-weight: 600;
                color: #ffffff;
            }
            
            .event-details {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
                margin-bottom: 15px;
                background: #374151;
                padding: 10px;
                border-radius: 4px;
            }
            
            .detail-item {
                display: flex;
                flex-direction: column;
                gap: 2px;
            }
            
            .detail-label {
                font-size: 6px;
                color: #9ca3af;
                font-weight: 500;
            }
            
            .detail-value {
                font-size: 7px;
                color: #ffffff;
                font-weight: 600;
            }
            
            .section {
                margin-bottom: 20px;
            }
            
            .section-title {
                display: flex;
                align-items: center;
                gap: 4px;
                font-size: 9px;
                font-weight: 600;
                color: #fbbf24;
                margin-bottom: 10px;
            }
            
            .payroll-summary {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
                background: #374151;
                padding: 10px;
                border-radius: 4px;
                margin-bottom: 15px;
            }
            
            .summary-item {
                display: flex;
                flex-direction: column;
                gap: 2px;
            }
            
            .summary-label {
                font-size: 6px;
                color: #9ca3af;
                font-weight: 500;
            }
            
            .summary-value {
                font-size: 8px;
                color: #ffffff;
                font-weight: 600;
            }
            
            .ore-breakdown {
                margin-bottom: 15px;
            }
            
            .ore-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 8px;
                margin-bottom: 8px;
            }
            
            .ore-card {
                background: #374151;
                border-radius: 4px;
                padding: 12px;
                border: 1px solid #4b5563;
                min-height: 120px;
            }
            
            .ore-header {
                font-size: 9px;
                font-weight: 600;
                color: #ffffff;
                margin-bottom: 8px;
                display: flex;
                align-items: flex-start;
                justify-content: space-between;
                min-height: 20px;
                line-height: 1.2;
            }
            
            .ore-scu {
                font-size: 7px;
                color: #9ca3af;
                font-weight: 500;
                white-space: nowrap;
            }
            
            .ore-detail {
                margin-bottom: 6px;
            }
            
            .ore-detail:last-child {
                margin-bottom: 0;
            }
            
            .ore-label {
                font-size: 6px;
                color: #9ca3af;
                margin-bottom: 3px;
            }
            
            .ore-value {
                font-size: 7px;
                font-weight: 600;
            }
            
            .ore-quantity {
                color: #10b981;
            }
            
            .ore-price {
                color: #3b82f6;
            }
            
            .ore-total {
                color: #f59e0b;
            }
            
            .participants-table {
                background: #374151;
                border-radius: 4px;
                overflow: hidden;
            }
            
            .table-header {
                background: #dc2626;
                display: grid;
                grid-template-columns: 20px 2fr 1fr 1.5fr 1.5fr 1fr;
                padding: 7px 10px;
                font-weight: 600;
                font-size: 5px;
            }
            
            .table-row {
                display: grid;
                grid-template-columns: 20px 2fr 1fr 1.5fr 1.5fr 1fr;
                padding: 5px 8px;
                border-bottom: 1px solid #4b5563;
                align-items: center;
                font-size: 5px;
            }
            
            .table-row:last-child {
                border-bottom: none;
            }
            
            .table-row:nth-child(even) {
                background: #2d3748;
            }
            
            .participant-name {
                font-weight: 500;
            }
            
            .time-value {
                color: #9ca3af;
            }
            
            .payout-base {
                color: #3b82f6;
                font-weight: 600;
            }
            
            .payout-final {
                color: #10b981;
                font-weight: 700;
            }
            
            .status-standard {
                background: #059669;
                color: white;
                padding: 2px 4px;
                border-radius: 2px;
                font-size: 5px;
                font-weight: 500;
                text-align: center;
            }
            
            .status-donor {
                background: #7c3aed;
                color: white;
                padding: 2px 4px;
                border-radius: 2px;
                font-size: 5px;
                font-weight: 500;
                text-align: center;
            }
            
            .print-only {
                page-break-inside: avoid;
            }
            
            .top-logo {
                text-align: center;
                padding: 15px 0;
                background: #1f2937;
                margin-bottom: 10px;
            }
            
            .top-logo .logo-large {
                width: 60px;
                height: 60px;
                margin-bottom: 8px;
            }
            
            .top-logo .logo-text {
                font-size: 12px;
                color: #ffffff;
                font-weight: 600;
            }
        </style>
    </head>
    <body>
        <div class="top-logo">
            <div class="logo-large">
                <div style="width: 60px; height: 60px; background: #dc2626; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 20px;">RL</div>
            </div>
            <div class="logo-text">RED LEGION</div>
        </div>
        <div class="container">
            <div class="header">
                <div class="logo">RL</div>
                <h1 class="header-title">📋 Payroll Summary</h1>
            </div>
            
            <div class="content">
                <div class="event-header">
                    <h2 class="event-title">← {{event_name}}</h2>
                </div>
                
                <div class="event-details">
                    <div class="detail-item">
                        <span class="detail-label">Event ID</span>
                        <span class="detail-value">{{event_id}}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Organizer</span>
                        <span class="detail-value">{{organizer}}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Duration</span>
                        <span class="detail-value">{{duration}}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Participants</span>
                        <span class="detail-value">{{participant_count}}</span>
                    </div>
                </div>
                
                <div class="section">
                    <h3 class="section-title">📋 Payroll Summary</h3>
                    <div class="payroll-summary">
                        <div class="summary-item">
                            <span class="summary-label">Total Payout</span>
                            <span class="summary-value">{{total_payout}} aUEC</span>
                        </div>
                        <div class="summary-item">
                            <span class="summary-label">Average Payout</span>
                            <span class="summary-value">{{average_payout}} aUEC</span>
                        </div>
                        <div class="summary-item">
                            <span class="summary-label">Total Participation</span>
                            <span class="summary-value">{{total_participation}}</span>
                        </div>
                        <div class="summary-item">
                            <span class="summary-label">Calculated By</span>
                            <span class="summary-value">{{calculated_by}}</span>
                        </div>
                        <div class="summary-item">
                            <span class="summary-label">Total SCU Collected</span>
                            <span class="summary-value">{{total_scu}}</span>
                        </div>
                        <div class="summary-item">
                            <span class="summary-label"></span>
                            <span class="summary-value"></span>
                        </div>
                    </div>
                </div>
                
                <div class="section ore-breakdown">
                    <h3 class="section-title">Ore Breakdown:</h3>
                    <div class="ore-grid">
                        {% for ore in ores %}
                        <div class="ore-card">
                            <div class="ore-header">
                                <span>{{ ore.name }}</span>
                                <span class="ore-scu">SCU</span>
                            </div>
                            <div class="ore-detail">
                                <div class="ore-label">Quantity:</div>
                                <div class="ore-value ore-quantity">{{ ore.quantity }}</div>
                            </div>
                            <div class="ore-detail">
                                <div class="ore-label">Price per unit:</div>
                                <div class="ore-value ore-price">{{ ore.price_per_unit }} aUEC</div>
                            </div>
                            <div class="ore-detail">
                                <div class="ore-label">Total Value:</div>
                                <div class="ore-value ore-total">{{ ore.total_value }} aUEC</div>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
                
                <div class="section">
                    <h3 class="section-title">👥 Individual Payouts</h3>
                    <div class="participants-table">
                        <div class="table-header">
                            <div>#</div>
                            <div>Participant</div>
                            <div>Time</div>
                            <div>Base Payout</div>
                            <div>Final Payout</div>
                            <div>Status</div>
                        </div>
                        {% for participant in participants %}
                        <div class="table-row">
                            <div>{{ loop.index }}</div>
                            <div class="participant-name">{{ participant.name }}</div>
                            <div class="time-value">{{ participant.time }}</div>
                            <div class="payout-base">{{ participant.base_payout }}</div>
                            <div class="payout-final">{{ participant.final_payout }}</div>
                            <div>
                                <span class="{% if participant.is_donor %}status-donor{% else %}status-standard{% endif %}">
                                    {% if participant.is_donor %}Donor{% else %}Standard{% endif %}
                                </span>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    
    try:
        # Render template with data
        template = Template(html_template)
        
        # Calculate duration string
        duration = "N/A"
        if event_data.get('total_duration_minutes'):
            hours = event_data['total_duration_minutes'] // 60
            minutes = event_data['total_duration_minutes'] % 60
            duration = f"{hours}h {minutes}m"
        
        html_content = template.render(
            event_name=event_data.get('event_name', 'Unknown Event'),
            event_id=event_data.get('event_id', 'Unknown'),
            organizer=event_data.get('organizer_name', 'Unknown'),
            duration=duration,
            participant_count=len(payroll_data.get('participants', [])),
            total_payout=payroll_data.get('total_payout', '0'),
            total_scu=payroll_data.get('total_scu', '0'),
            average_payout=payroll_data.get('average_payout', '0'),
            calculated_by=payroll_data.get('calculated_by', 'System'),
            total_participation=f"{len(payroll_data.get('participants', []))} members",
            ores=payroll_data.get('ores', []),
            participants=payroll_data.get('participants', [])
        )
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # Set content and wait for load
            await page.set_content(html_content, wait_until='networkidle')
            
            # Generate PDF with A4 format
            pdf_bytes = await page.pdf(
                format='A4',
                margin={'top': '10mm', 'right': '10mm', 'bottom': '10mm', 'left': '10mm'},
                print_background=True
            )
            
            await browser.close()
            return pdf_bytes
            
    except Exception as e:
        logger.error(f"Error generating PDF with Playwright: {e}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

@app.get("/admin/payroll-export/{event_id}")
async def export_payroll_pdf(event_id: str, admin_user: SessionData = Depends(get_admin_user)):
    """Export payroll summary as PDF using Playwright."""
    try:
        pool = await get_db_pool()
        if pool is None:
            raise HTTPException(status_code=503, detail="Database not available")
            
        async with pool.acquire() as conn:
            # Get event information
            event = await conn.fetchrow("""
                SELECT event_id, event_name, event_type, organizer_name, 
                       started_at, ended_at, total_participants, total_duration_minutes
                FROM events 
                WHERE event_id = $1
            """, event_id)
            
            if not event:
                raise HTTPException(status_code=404, detail="Event not found")
            
            # Get payroll information
            payroll = await conn.fetchrow("""
                SELECT payroll_id, total_value_auec, calculated_by_name, calculated_at,
                       total_scu_collected, ore_prices_used, mining_yields
                FROM payrolls 
                WHERE event_id = $1
            """, event_id)
            
            if not payroll:
                raise HTTPException(status_code=404, detail="Payroll not found for this event")
            
            # Get individual payouts
            payouts = await conn.fetch("""
                SELECT username, participation_minutes, base_payout_auec, 
                       final_payout_auec, is_donor
                FROM payouts 
                WHERE payroll_id = $1
                ORDER BY final_payout_auec DESC
            """, payroll['payroll_id'])
            
            # Prepare data for PDF generation
            import json
            from datetime import datetime
            from fastapi.responses import Response
            
            # Parse mining yields and ore prices
            mining_yields = {}
            ore_prices = {}
            
            if payroll.get('mining_yields'):
                try:
                    mining_yields = json.loads(payroll['mining_yields'])
                except (json.JSONDecodeError, TypeError):
                    mining_yields = {}
            
            if payroll.get('ore_prices_used'):
                try:
                    ore_prices = json.loads(payroll['ore_prices_used'])
                except (json.JSONDecodeError, TypeError):
                    ore_prices = {}
            
            # Prepare event data
            event_data = {
                'event_id': event['event_id'],
                'event_name': event.get('event_name', 'N/A'),
                'organizer_name': event.get('organizer_name', 'Unknown'),
                'total_duration_minutes': event.get('total_duration_minutes', 0),
                'participant_count': len(payouts),
                'created_at': event.get('created_at', datetime.now())
            }
            
            # Prepare payroll data
            ores_list = []
            for ore_name, quantity in mining_yields.items():
                if quantity > 0:  # Only include ores that were actually collected
                    price_per_unit = ore_prices.get(ore_name.upper(), 0)
                    total_value = quantity * price_per_unit
                    ores_list.append({
                        'name': ore_name.title(),
                        'quantity': f"{quantity:,.0f}",
                        'price_per_unit': f"{price_per_unit:,.2f}",
                        'total_value': f"{total_value:,.2f}"
                    })
            
            participants_list = []
            for payout in payouts:
                participants_list.append({
                    'name': payout['username'],
                    'time': f"{payout['participation_minutes']} min",
                    'base_payout': f"{float(payout['base_payout_auec']):,.2f}",
                    'final_payout': f"{float(payout['final_payout_auec']):,.2f}",
                    'is_donor': payout['is_donor']
                })
            
            total_payout = float(payroll['total_value_auec'])
            non_donors = len([p for p in payouts if not p['is_donor']])
            average_payout = total_payout / non_donors if non_donors > 0 else 0
            
            payroll_summary = {
                'ores': ores_list,
                'participants': participants_list,
                'total_payout': f"{total_payout:,.2f}",
                'total_scu': f"{float(payroll.get('total_scu_collected', 0)):,.0f}",
                'average_payout': f"{average_payout:,.2f}",
                'calculated_by': payroll.get('calculated_by_name', 'System')
            }
            
            # Generate PDF using Playwright
            pdf_content = await generate_pdf_with_playwright(event_data, payroll_summary)
            
            # Return PDF as response
            filename = f"payroll_{event_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            return Response(
                content=pdf_content,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}",
                    "Content-Type": "application/pdf"
                }
            )
            
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error generating export for {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Export generation error: {str(e)}")
            
#            # Generate PDF
#            pdf_buffer = io.BytesIO()
#            doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, topMargin=0.75*inch, 
#                                  bottomMargin=0.75*inch, leftMargin=1*inch, rightMargin=1*inch)
#            styles = getSampleStyleSheet()
#            story = []
            
#            # Enhanced header with logo
#            story = create_enhanced_pdf_header(story, event, styles)
            
#            # Event Information
#            event_info_style = ParagraphStyle(
#                'EventInfo',
#                parent=styles['Normal'],
#                fontSize=10,
#                spaceAfter=10
#            )
            
#            event_info = f"""
#            <b>Event:</b> {event['event_name'] or 'N/A'}<br/>
#            <b>Event ID:</b> {event['event_id']}<br/>
#            <b>Type:</b> {event['event_type'].title()}<br/>
#            <b>Organizer:</b> {event['organizer_name']}<br/>
#            <b>Duration:</b> {event['total_duration_minutes']} minutes ({event['total_duration_minutes'] // 60}h {event['total_duration_minutes'] % 60}m)<br/>
#            <b>Participants:</b> {event['total_participants']}<br/>
#            <b>Date:</b> {event['started_at'].strftime('%Y-%m-%d %H:%M') if event['started_at'] else 'N/A'}<br/>
#            """
#            story.append(Paragraph(event_info, event_info_style))
#            story.append(Spacer(1, 20))
            
#            # Payroll Summary
#            summary_style = ParagraphStyle(
#                'SummaryHeader',
#                parent=styles['Heading2'],
#                fontSize=14,
#                spaceAfter=10,
#                textColor=colors.darkgreen
#            )
#            story.append(Paragraph("💰 Payroll Summary", summary_style))
            
#            total_payout = float(payroll['total_value_auec'])
#            average_payout = total_payout / len(payouts) if payouts else 0
            
#            summary_info = f"""
#            <b>Total Payout:</b> {total_payout:,.0f} aUEC<br/>
#            <b>Average Payout:</b> {average_payout:,.0f} aUEC<br/>
#            <b>Calculated By:</b> {payroll['calculated_by_name']}<br/>
#            <b>Calculated At:</b> {payroll['calculated_at'].strftime('%Y-%m-%d %H:%M') if payroll['calculated_at'] else 'N/A'}<br/>
#            """
#            story.append(Paragraph(summary_info, event_info_style))
#            story.append(Spacer(1, 20))
            
#            # Individual Payouts Table
#            payout_header_style = ParagraphStyle(
#                'PayoutHeader',
#                parent=styles['Heading2'],
#                fontSize=14,
#                spaceAfter=10,
#                textColor=colors.darkred
#            )
#            story.append(Paragraph("👥 Individual Payouts", payout_header_style))
            
#            # Create table data
#            table_data = [
#                ['#', 'Participant', 'Time (min)', 'Base Payout (aUEC)', 'Final Payout (aUEC)', 'Status']
#            ]
            
#            for i, payout in enumerate(payouts, 1):
#                status = "Donor" if payout['is_donor'] else "Standard"
#                table_data.append([
#                    str(i),
#                    str(payout['username']),
#                    str(payout['participation_minutes']),
#                    f"{float(payout['base_payout_auec']):,.0f}",
#                    f"{float(payout['final_payout_auec']):,.0f}",
#                    status
#                ])
            
#            # Create table with enhanced styling
#            table = Table(table_data, colWidths=[0.5*inch, 2*inch, 0.8*inch, 1.2*inch, 1.2*inch, 0.8*inch])
#            table.setStyle(TableStyle([
#                # Header styling
#                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.8, 0.2, 0.2)),  # Red Legion red
#                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
#                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#                ('FONTSIZE', (0, 0), (-1, 0), 11),
#                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
#                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
#                ('TOPPADDING', (0, 0), (-1, 0), 8),
#                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                
#                # Data rows styling
#                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
#                ('FONTSIZE', (0, 1), (-1, -1), 9),
#                ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
#                ('ALIGN', (1, 1), (1, -1), 'LEFT'),  # Left align usernames
#                ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
#                ('TOPPADDING', (0, 1), (-1, -1), 6),
#                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                
#                # Alternating row colors
#                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.Color(0.97, 0.97, 0.97), colors.Color(0.92, 0.92, 0.92)]),
                
#                # Borders and grid
#                ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.6, 0.6, 0.6)),
#                ('LINEBELOW', (0, 0), (-1, 0), 2, colors.Color(0.8, 0.2, 0.2)),  # Thick underline for header
                
#                # Special formatting for status column
#                ('TEXTCOLOR', (5, 1), (5, -1), colors.Color(0.2, 0.6, 0.2)),  # Green for status
#            ])
#            story.append(table)
            
#            # Footer
#            story.append(Spacer(1, 30))
#            footer_style = ParagraphStyle(
#                'Footer',
#                parent=styles['Normal'],
#                fontSize=8,
#                textColor=colors.grey,
#                alignment=1  # Center alignment
#            )
#            story.append(Paragraph("Generated by Red Legion Web Payroll System", footer_style))
#            story.append(Paragraph(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", footer_style))
            
#            # Build PDF
#            doc.build(story)
#            pdf_buffer.seek(0)
            
#            # Return PDF as response
#            filename = f"payroll_{event['event_id']}.pdf"
#            return Response(
#                content=pdf_buffer.read(),
#                media_type="application/pdf",
#                headers={"Content-Disposition": f"attachment; filename={filename}"}
#            )
            
#    except HTTPException:
#        raise  # Re-raise HTTP exceptions
#    except Exception as e:
#        logger.error(f"Error generating PDF for {event_id}: {e}")
#        raise HTTPException(status_code=500, detail=f"PDF generation error: {str(e)}")

@app.post("/admin/create-test-event/{event_type}")
async def create_test_event(event_type: str, admin_user: SessionData = Depends(get_admin_user)):
    """Create a test event with random participants and data."""
    if event_type not in ["mining", "salvage"]:
        raise HTTPException(status_code=400, detail="Event type must be 'mining' or 'salvage'")
    
    try:
        pool = await get_db_pool()
        if pool is None:
            # Return mock success response when database is not available
            import random
            import uuid
            from datetime import datetime, timedelta
            
            # Ensure mock_events is initialized
            get_shared_mock_events()
            global mock_events
            
            event_id = f'test_{uuid.uuid4().hex[:8]}'
            num_participants = random.randint(5, 25)
            duration_hours = random.randint(1, 7)
            event_name = f'Test {event_type.title()} Op {random.randint(100, 999)}'
            
            # Create new event object
            new_event = {
                'event_id': event_id,
                'event_name': event_name,
                'event_type': event_type,
                'organizer_name': 'TestBot',
                'started_at': (datetime.now() - timedelta(hours=duration_hours)).isoformat(),
                'ended_at': datetime.now().isoformat(),
                'total_duration_minutes': duration_hours * 60,
                'participant_count': num_participants,
                'total_participants': num_participants,
                'status': 'completed',
                'has_payroll': False
            }
            
            # Add to mock storage
            mock_events.append(new_event)
            
            return {
                'success': True,
                'message': f'Test {event_type} event created successfully (mock mode)',
                'event': {
                    'event_id': event_id,
                    'event_name': event_name,
                    'event_type': event_type,
                    'organizer_name': 'TestBot',
                    'participants': num_participants,
                    'duration_hours': duration_hours,
                    'started_at': new_event['started_at'],
                    'ended_at': new_event['ended_at'],
                    'status': 'completed'
                }
            }
        
        async with pool.acquire() as conn:
            async with conn.transaction():
                # Import needed modules for database path
                import random as rand
                from datetime import datetime, timedelta
                
                # Generate random event data
                event_id = generate_event_id()
                num_participants = rand.randint(5, 25)
                duration_hours = rand.randint(1, 7)
                duration_minutes = duration_hours * 60
                
                # Random start time between 1-30 days ago
                days_ago = rand.randint(1, 30)
                started_at = datetime.utcnow() - timedelta(days=days_ago)
                ended_at = started_at + timedelta(hours=duration_hours)
                
                event_name = f"Test {event_type.title()} Op {rand.randint(100, 999)}"
                
                # Generate realistic Discord display names
                test_display_names = [
                    "NewSticks", "Saladin80", "Tealstone", "LowNslow", "Ferny133",
                    "Jaeger31", "Blitz0117", "Prometheus114", "RockHound", "CrystalCrafter",
                    "VoidRunner", "AsteroidAce", "QuantumMiner", "StellarSalvage",
                    "SpaceRanger", "CosmicCrawler", "MetalHarvester", "SystemScanner"
                ]
                organizer_name = rand.choice(test_display_names)
                organizer_id = rand.randint(100000000000000000, 999999999999999999)
                
                # Create the event
                await conn.execute("""
                    INSERT INTO events (
                        event_id, event_type, event_name, organizer_name, organizer_id,
                        guild_id, started_at, ended_at, status, total_participants,
                        total_duration_minutes, payroll_calculated, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """, 
                    event_id, event_type, event_name, organizer_name, organizer_id,
                    814699481912049704, started_at, ended_at, 'closed', num_participants,
                    duration_minutes, False, datetime.utcnow()
                )
                
                # Generate random participants
                fake_users = await generate_fake_participants(num_participants)
                total_participation_time = 0
                
                for user in fake_users:
                    # Random participation time (15-240 minutes)
                    participation_minutes = rand.randint(15, min(240, duration_minutes))
                    total_participation_time += participation_minutes
                    
                    # Random join time within event duration
                    max_join_offset = max(1, duration_minutes - participation_minutes)
                    join_offset = rand.randint(0, max_join_offset)
                    joined_at = started_at + timedelta(minutes=join_offset)
                    left_at = joined_at + timedelta(minutes=participation_minutes)
                    
                    await conn.execute("""
                        INSERT INTO participation (
                            event_id, user_id, username, display_name, joined_at, left_at,
                            was_active, duration_minutes, created_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """, 
                        event_id, user['user_id'], user['username'], user['display_name'],
                        joined_at, left_at, True, participation_minutes, datetime.utcnow()
                    )
                
                # Update event totals
                await conn.execute("""
                    UPDATE events 
                    SET total_participants = $1, total_duration_minutes = $2
                    WHERE event_id = $3
                """, num_participants, total_participation_time, event_id)
                
                logger.info(f"Created test {event_type} event {event_id} with {num_participants} participants")
                
                # Return event details
                event_data = await conn.fetchrow("""
                    SELECT * FROM events WHERE event_id = $1
                """, event_id)
                
                return {
                    "success": True,
                    "message": f"Test {event_type} event created successfully",
                    "event": dict(event_data)
                }
                
    except Exception as e:
        logger.error(f"Error creating test {event_type} event: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

def generate_event_id():
    """Generate event ID matching pattern used by payroll system: sm-[a-z0-9]{6}"""
    import random as rand
    import string
    suffix = ''.join(rand.choices(string.ascii_lowercase + string.digits, k=6))
    return f"sm-{suffix}"

async def generate_fake_participants(count: int):
    """Generate fake participant data for testing."""
    import random as rand
    
    fake_usernames = [
        "MinerAlpha", "SalvageKing", "RedLegionPilot", "SpaceRanger", "StarCollector",
        "OreMaster", "QuantumMiner", "AsteroidHunter", "CrystalSeeker", "VoidRunner",
        "DeepSpaceMiner", "StellarSalvage", "GalaxyHarvester", "NebulaNavigator", 
        "CosmicCrawler", "PlanetaryProspector", "InterstellarMiner", "SpacePirate",
        "RockHound", "CrystalCrafter", "MetalHarvester", "ElementExtractor",
        "QuantumScavenger", "AsteroidAce", "SystemScanner", "ResourceRaider"
    ]
    
    fake_display_names = [
        "Alpha Miner", "The Salvage King", "Red Legion Elite", "Space Ranger X",
        "Crystal Collector", "Ore Master Pro", "Quantum Explorer", "Asteroid Hunter",
        "Crystal Seeker", "Void Runner", "Deep Space Miner", "Stellar Salvage",
        "Galaxy Harvester", "Nebula Navigator", "Cosmic Crawler", "Planetary Prospector",
        "Interstellar Miner", "Space Pirate", "Rock Hound", "Crystal Crafter"
    ]
    
    participants = []
    used_names = set()
    
    for i in range(count):
        # Ensure unique usernames
        username = rand.choice(fake_usernames)
        counter = 1
        original_username = username
        while username in used_names:
            username = f"{original_username}{counter}"
            counter += 1
        used_names.add(username)
        
        display_name = rand.choice(fake_display_names)
        user_id = rand.randint(100000000000000000, 999999999999999999)
        
        participants.append({
            'user_id': user_id,
            'username': username,
            'display_name': display_name
        })
    
    return participants

@app.post("/events/create")
async def create_event(request: EventCreationRequest, current_user: SessionData = Depends(get_current_user)):
    """Create a new mining event compatible with payroll system."""
    try:
        pool = await get_db_pool()
        if pool is None:
            # Return mock success response when database is not available
            from datetime import datetime
            import uuid
            return {
                'event_id': f'evt_{uuid.uuid4().hex[:8]}',
                'event_name': request.event_name,
                'organizer_name': request.organizer_name,
                'event_type': request.event_type,
                'started_at': datetime.now().isoformat(),
                'ended_at': None,
                'status': 'active',
                'scheduled_start_time': request.scheduled_start_time.isoformat() if request.scheduled_start_time else None,
                'auto_start_enabled': request.auto_start_enabled,
                'tracked_channels': request.tracked_channels,
                'primary_channel_id': request.primary_channel_id,
                'event_status': 'live' if request.scheduled_start_time is None else 'scheduled',
                'message': 'Event created successfully (mock mode)'
            }
        
        async with pool.acquire() as conn:
            # Generate event ID matching the database constraint: [a-z]{2,4}-[a-z0-9]{6}
            import random
            import string
            event_id = f"web-{''.join(random.choices(string.ascii_lowercase + string.digits, k=6))}"
            
            # Normalize scheduled_start_time to handle timezone-aware datetimes
            scheduled_start_time = None
            if request.scheduled_start_time is not None:
                if request.scheduled_start_time.tzinfo is not None:
                    # Convert timezone-aware datetime to UTC and make it naive
                    scheduled_start_time = request.scheduled_start_time.astimezone(timezone.utc).replace(tzinfo=None)
                else:
                    # Already timezone-naive
                    scheduled_start_time = request.scheduled_start_time
            
            # Insert new event
            await conn.execute("""
                INSERT INTO events (
                    event_id, event_type, event_name, organizer_name, organizer_id, 
                    guild_id, started_at, status, location_notes, description, created_at,
                    scheduled_start_time, auto_start_enabled, tracked_channels, primary_channel_id, event_status
                ) VALUES ($1, $2, $3, $4, $5, $6, NOW(), 'open', $7, $8, NOW(), $9, $10, $11, $12, $13)
            """, 
                event_id, 
                request.event_type,
                request.event_name,
                request.organizer_name,
                int(request.organizer_id) if request.organizer_id else 0,
                int(request.guild_id),
                request.location_notes,
                request.session_notes,
                scheduled_start_time,
                request.auto_start_enabled,
                json.dumps(request.tracked_channels) if request.tracked_channels else None,
                request.primary_channel_id,
                'live' if scheduled_start_time is None else 'scheduled'
            )
            
            # Fetch the created event
            event_data = await conn.fetchrow("""
                SELECT event_id, event_name, organizer_name, started_at, status, 
                       location_notes, description, event_type, organizer_id,
                       scheduled_start_time, auto_start_enabled, tracked_channels, 
                       primary_channel_id, event_status
                FROM events WHERE event_id = $1
            """, event_id)
            
            # Prepare event data for Discord integration
            discord_event_data = {
                "event_id": event_data["event_id"],
                "event_name": event_data["event_name"],
                "event_type": event_data["event_type"],
                "organizer_name": event_data["organizer_name"],
                "organizer_id": str(event_data["organizer_id"]),
                "location": event_data["location_notes"],
                "notes": event_data["description"],
                "tracked_channels": event_data["tracked_channels"],
                "primary_channel_id": event_data["primary_channel_id"]
            }
            
            # Try to start Discord voice tracking (non-blocking)
            try:
                logger.info(f"🎯 Attempting to start Discord voice tracking for event: {event_id}")
                discord_result = await trigger_voice_tracking_on_event_start(discord_event_data)
                
                if discord_result.get("success"):
                    logger.info(f"✅ Discord voice tracking started successfully for event: {event_id}")
                    discord_message = "Discord voice tracking started"
                else:
                    logger.warning(f"⚠️ Discord voice tracking failed for event {event_id}: {discord_result.get('error', 'Unknown error')}")
                    discord_message = f"Event created but Discord voice tracking failed: {discord_result.get('error', 'Unknown error')}"
                    
            except Exception as e:
                logger.error(f"❌ Exception during Discord voice tracking setup for event {event_id}: {e}")
                discord_message = f"Event created but Discord integration failed: {str(e)}"
            
            return {
                "success": True,
                "message": f"Mining event created successfully. {discord_message}",
                "event": dict(event_data),
                "discord_integration": discord_result if 'discord_result' in locals() else {"success": False, "error": "Integration not attempted"}
            }
            
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to create event")

@app.post("/events/{event_id}/start")
async def start_event(event_id: str, current_user: SessionData = Depends(get_current_user)):
    """Start a scheduled mining event and begin voice tracking."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Update event status and start time
            result = await conn.fetchrow("""
                UPDATE events 
                SET status = 'live',
                    started_at = NOW(),
                    updated_at = NOW()
                WHERE event_id = $1 
                AND status = 'scheduled'
                RETURNING event_id, event_name, organizer_name, event_type, 
                         tracked_channels, primary_channel_id, status, started_at
            """, event_id)
            
            if not result:
                raise HTTPException(status_code=404, detail="Event not found or not in scheduled status")
            
            # Prepare Discord event data for voice tracking
            discord_event_data = {
                'event_id': result['event_id'],
                'event_name': result['event_name'],
                'organizer_name': result['organizer_name'],
                'event_type': result['event_type'],
                'tracked_channels': result['tracked_channels'] or [],
                'primary_channel_id': result['primary_channel_id'],
                'started_at': result['started_at']
            }
            
            # Start Discord voice tracking
            try:
                logger.info(f"🎯 Attempting to start Discord voice tracking for event: {event_id}")
                discord_result = await trigger_voice_tracking_on_event_start(discord_event_data)
                
                if discord_result.get('success'):
                    logger.info(f"✅ Discord voice tracking started successfully for event: {event_id}")
                else:
                    logger.warning(f"⚠️ Discord voice tracking start had issues for event: {event_id}")
                    
            except Exception as discord_error:
                logger.error(f"❌ Failed to start Discord voice tracking for event {event_id}: {discord_error}")
                # Continue anyway - the event is still started
                
            return {
                "success": True,
                "message": f"Event '{result['event_name']}' started successfully",
                "event": {
                    "event_id": result['event_id'],
                    "event_name": result['event_name'],
                    "status": result['status'],
                    "started_at": result['started_at'].isoformat()
                },
                "discord_tracking": discord_result if 'discord_result' in locals() else None
            }
            
    except Exception as e:
        logger.error(f"❌ Error starting event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start event: {str(e)}")


@app.post("/events/{event_id}/close")
async def close_event(event_id: str, current_user: SessionData = Depends(get_current_user)):
    """Close a mining event and calculate final stats."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Update event status and end time
            result = await conn.fetchrow("""
                UPDATE events 
                SET status = 'closed',
                    ended_at = NOW(),
                    updated_at = NOW()
                WHERE event_id = $1 
                AND status = 'open'
                RETURNING *
            """, event_id)
            
            if not result:
                raise HTTPException(status_code=404, detail="Event not found or already closed")
            
            # Calculate final participation metrics
            participation_stats = await conn.fetchrow("""
                SELECT COUNT(DISTINCT user_id) as total_participants
                FROM participation 
                WHERE event_id = $1
            """, event_id)
            
            total_participants = participation_stats['total_participants'] if participation_stats else 0
            
            # Calculate event duration based on actual start/end times
            event_times = await conn.fetchrow("""
                SELECT started_at, ended_at
                FROM events
                WHERE event_id = $1
            """, event_id)
            
            total_duration_minutes = 0
            if event_times and event_times['started_at'] and event_times['ended_at']:
                duration_seconds = (event_times['ended_at'] - event_times['started_at']).total_seconds()
                total_duration_minutes = int(duration_seconds / 60)
            
            # Update the event with final stats
            await conn.execute("""
                UPDATE events 
                SET total_participants = $1,
                    total_duration_minutes = $2,
                    updated_at = NOW()
                WHERE event_id = $3
            """, total_participants, total_duration_minutes, event_id)
            
            # Try to stop Discord voice tracking (non-blocking)
            try:
                logger.info(f"🛑 Attempting to stop Discord voice tracking for event: {event_id}")
                discord_result = await trigger_voice_tracking_on_event_stop(event_id)
                
                if discord_result.get("success"):
                    logger.info(f"✅ Discord voice tracking stopped successfully for event: {event_id}")
                    discord_message = "Discord voice tracking stopped"
                else:
                    logger.warning(f"⚠️ Discord voice tracking stop failed for event {event_id}: {discord_result.get('error', 'Unknown error')}")
                    discord_message = f"Event closed but Discord voice tracking stop failed: {discord_result.get('error', 'Unknown error')}"
                    
            except Exception as e:
                logger.error(f"❌ Exception during Discord voice tracking stop for event {event_id}: {e}")
                discord_message = f"Event closed but Discord integration failed: {str(e)}"
            
            return {
                'success': True,
                'event_id': event_id,
                'total_participants': total_participants,
                'total_duration_minutes': total_duration_minutes,
                'message': f'Event closed successfully. {discord_message}',
                'discord_integration': discord_result if 'discord_result' in locals() else {"success": False, "error": "Integration not attempted"}
            }
            
    except Exception as e:
        logger.error(f"Error closing event: {e}")
        raise HTTPException(status_code=500, detail="Failed to close event")

@app.get("/discord/bot-status")
async def discord_bot_status_endpoint(current_user: SessionData = Depends(get_current_user)):
    """Get Discord bot connection status for admin dashboard."""
    try:
        logger.info("🔍 Checking Discord bot status")
        status = await get_discord_bot_status()
        
        logger.info(f"🤖 Discord bot status: {'✅ Connected' if status.get('connected') else '❌ Disconnected'}")
        
        return {
            "success": True,
            "bot_status": status,
            "message": "Discord bot status retrieved successfully"
        }
    except Exception as e:
        logger.error(f"❌ Error checking Discord bot status: {e}")
        return {
            "success": False,
            "error": str(e),
            "bot_status": {"connected": False, "error": "Status check failed"},
            "message": "Failed to check Discord bot status"
        }

# Trading Locations and Pricing Endpoints

@app.get("/trading-locations")
async def get_trading_locations(current_user: SessionData = Depends(get_current_user)):
    """Get all active trading locations."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            locations = await conn.fetch("""
                SELECT location_id, location_name, system_name, planet_moon, 
                       station_outpost, location_type
                FROM trading_locations 
                WHERE is_active = true 
                ORDER BY system_name, location_name
            """)
            
            return [dict(location) for location in locations]
            
    except Exception as e:
        logger.error(f"Error fetching trading locations: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/material-prices/{material_names}")
async def get_material_prices(material_names: str, location_id: int = None, current_user: SessionData = Depends(get_current_user)):
    """Get material prices, optionally for a specific location.
    
    material_names can be a comma-separated list of material names.
    If location_id is provided, returns prices for that location only.
    Otherwise returns all prices with highest price info.
    """
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Parse material names
            materials = [name.strip() for name in material_names.split(',')]
            
            if location_id:
                # Get prices for specific location
                prices = await conn.fetch("""
                    SELECT m.name as material_name, m.category, mp.sell_price,
                           tl.location_name, tl.system_name, tl.station_outpost
                    FROM materials m
                    JOIN material_prices mp ON m.material_id = mp.material_id
                    JOIN trading_locations tl ON mp.location_id = tl.location_id
                    WHERE m.name = ANY($1) AND mp.location_id = $2 
                    AND m.is_active = true AND mp.is_current = true
                    ORDER BY m.name
                """, materials, location_id)
                
                return [dict(price) for price in prices]
            else:
                # Get all prices with highest price info
                prices = await conn.fetch("""
                    WITH ranked_prices AS (
                        SELECT m.material_id, m.name as material_name, m.category,
                               mp.sell_price,
                               tl.location_name, tl.system_name, tl.station_outpost,
                               ROW_NUMBER() OVER (
                                   PARTITION BY m.material_id 
                                   ORDER BY mp.sell_price DESC
                               ) as price_rank
                        FROM materials m
                        JOIN material_prices mp ON m.material_id = mp.material_id
                        JOIN trading_locations tl ON mp.location_id = tl.location_id
                        WHERE m.name = ANY($1) AND m.is_active = true AND mp.is_current = true
                    )
                    SELECT material_id, material_name, category, 
                           sell_price as highest_price, 
                           location_name as best_location, 
                           system_name as best_system, 
                           station_outpost as best_station
                    FROM ranked_prices
                    WHERE price_rank = 1
                    ORDER BY material_name
                """, materials)
                
                return [dict(price) for price in prices]
                
    except Exception as e:
        logger.error(f"Error fetching material prices: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/location-prices/{location_id}")
async def get_location_prices(location_id: int, material_names: str = None, current_user: SessionData = Depends(get_current_user)):
    """Get all material prices for a specific location.
    
    Optionally filter by material_names (comma-separated).
    """
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            if material_names:
                materials = [name.strip() for name in material_names.split(',')]
                prices = await conn.fetch("""
                    SELECT m.name as material_name, m.category, m.base_value,
                           mp.sell_price, mp.last_updated,
                           tl.location_name, tl.system_name
                    FROM materials m
                    JOIN material_prices mp ON m.material_id = mp.material_id
                    JOIN trading_locations tl ON mp.location_id = tl.location_id
                    WHERE mp.location_id = $1 AND m.name = ANY($2)
                    AND m.is_active = true AND mp.is_current = true
                    ORDER BY m.category, m.name
                """, location_id, materials)
            else:
                prices = await conn.fetch("""
                    SELECT m.name as material_name, m.category, m.base_value,
                           mp.sell_price, mp.last_updated,
                           tl.location_name, tl.system_name
                    FROM materials m
                    JOIN material_prices mp ON m.material_id = mp.material_id
                    JOIN trading_locations tl ON mp.location_id = tl.location_id
                    WHERE mp.location_id = $1
                    AND m.is_active = true AND mp.is_current = true
                    ORDER BY m.category, m.name
                """, location_id)
                
            return [dict(price) for price in prices]
            
    except Exception as e:
        logger.error(f"Error fetching location prices: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

async def get_uex_prices() -> Dict[str, float]:
    """Get UEX ore prices from the real UEX cache system."""
    try:
        # Try to import and use the UEX cache system
        import importlib.util
        from pathlib import Path
        
        # Path to the UEX cache module
        cache_file_path = Path(__file__).parent.parent.parent / "red-legion-bots" / "src" / "services" / "uex_cache.py"
        
        if cache_file_path.exists():
            # Load the UEX cache module
            spec = importlib.util.spec_from_file_location("uex_cache", cache_file_path)
            if spec and spec.loader:
                uex_cache = importlib.util.module_from_spec(spec)
                sys.modules["uex_cache"] = uex_cache
                spec.loader.exec_module(uex_cache)
                
                # Get the cache instance and fetch current prices
                if hasattr(uex_cache, 'UEXCache'):
                    cache_instance = uex_cache.UEXCache()
                    cache_data = await cache_instance.get_cached_data()
                    
                    if cache_data and 'ores' in cache_data:
                        prices = {}
                        for ore_code, ore_data in cache_data['ores'].items():
                            # Use price_sell as the selling price (what miners get when selling)
                            if isinstance(ore_data, dict) and 'price_sell' in ore_data:
                                prices[ore_code.upper()] = float(ore_data['price_sell'])
                        
                        # Add salvage materials if available
                        if 'salvage' in cache_data:
                            for material_code, material_data in cache_data['salvage'].items():
                                if isinstance(material_data, dict) and 'price_sell' in material_data:
                                    prices[material_code.upper()] = float(material_data['price_sell'])
                        
                        # Add some manual mappings for salvage materials if not present
                        if 'RECYCLED MATERIAL COMPOSITE' not in prices:
                            prices['RECYCLED MATERIAL COMPOSITE'] = 9869.0  # RMC fallback
                        if 'CONSTRUCTION MATERIALS' not in prices:
                            prices['CONSTRUCTION MATERIALS'] = 2157.0  # CMAT fallback
                        
                        logger.info(f"✅ Successfully loaded {len(prices)} prices from UEX cache")
                        return prices
    
    except Exception as e:
        logger.warning(f"⚠️ Could not load UEX cache, using fallback prices: {e}")
    
    # Fallback to default prices if UEX cache is unavailable
    logger.info("📋 Using fallback hardcoded prices")
    default_prices = {
        # Mining Ore Prices
        'QUANTAINIUM': 21869.0,
        'BEXALITE': 19175.0,
        'TARANITE': 18425.0,
        'BORASE': 15280.0,
        'LARANITE': 14875.0,
        'TITANIUM': 8232.0,
        'DIAMOND': 7936.0,
        'GOLD': 5832.0,
        'COPPER': 6125.0,
        'BERYL': 4850.0,
        'TUNGSTEN': 3580.0,
        'CORUNDUM': 359.0,
        'QUARTZ': 1356.0,
        'ALUMINIUM': 1.23,
        'HEPHAESTANITE': 18500.0,
        'HADANITE': 22750.0,
        'APHORITE': 17200.0,
        'DOLIVINE': 425.0,
        'AGRICIUM': 44250.0,
        'RICCITE': 20585.0,
        'INERT_MATERIALS': 0.01,
        
        # Salvage Material Prices (from UEX API)
        'RECYCLED MATERIAL COMPOSITE': 9869.0,  # RMC
        'CONSTRUCTION MATERIALS': 2157.0,       # CMAT
    }
    return default_prices

@app.post("/admin/refresh-uex-cache")
async def refresh_uex_cache(admin_user: SessionData = Depends(get_admin_user)):
    """Force refresh of UEX price cache to get current market prices."""
    logger.info("🔄 Manual UEX cache refresh requested")
    
    import sys
    import importlib.util
    from pathlib import Path
    
    # Direct import of the UEX cache module - go up to red-legion directory first
    cache_file_path = Path(__file__).parent.parent.parent / "red-legion-bots" / "src" / "services" / "uex_cache.py"
    logger.info(f"🔍 Looking for UEX cache at: {cache_file_path}")
    
    try:
        # Load the module directly
        spec = importlib.util.spec_from_file_location("uex_cache", cache_file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load spec from {cache_file_path}")
        
        uex_cache_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(uex_cache_module)
        get_uex_cache = uex_cache_module.get_uex_cache
        
        cache = get_uex_cache()
        
        # Force refresh all price categories
        categories = ["ores", "high_value", "all"]
        refresh_results = {}
        
        for category in categories:
            try:
                logger.info(f"🔄 Refreshing {category} prices...")
                prices = await cache.get_ore_prices(category=category, force_refresh=True)
                
                if prices:
                    refresh_results[category] = {
                        "success": True,
                        "item_count": len(prices),
                        "timestamp": datetime.now().isoformat()
                    }
                    logger.info(f"✅ Refreshed {len(prices)} {category} prices")
                else:
                    refresh_results[category] = {
                        "success": False,
                        "error": "No data returned from API",
                        "timestamp": datetime.now().isoformat()
                    }
                    logger.warning(f"⚠️ Failed to refresh {category} prices - no data")
                    
            except Exception as e:
                logger.error(f"❌ Error refreshing {category} prices: {e}")
                refresh_results[category] = {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        # Get cache stats for response
        stats = cache.get_cache_stats()
        
        success_count = sum(1 for result in refresh_results.values() if result["success"])
        total_count = len(refresh_results)
        
        return {
            "success": success_count > 0,
            "message": f"Refreshed {success_count}/{total_count} price categories",
            "results": refresh_results,
            "cache_stats": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except ImportError as e:
        logger.error(f"❌ Could not import UEX cache system: {e}")
        return {
            "success": False,
            "error": f"UEX cache system not available: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Unexpected error during UEX cache refresh: {e}")
        return {
            "success": False,
            "error": f"Cache refresh failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

# =====================================================
# EVENT SCHEDULING & MONITORING ENDPOINTS
# =====================================================

@app.get("/events/scheduled")
async def get_scheduled_events(current_user: SessionData = Depends(get_current_user)):
    """Get all scheduled events (event_status = 'scheduled')."""
    try:
        pool = await get_db_pool()
        if pool is None:
            # Return mock scheduled events when database is not available
            mock_scheduled = [
                {
                    'event_id': 'sch-demo01',
                    'event_name': 'Sunday Mining Session',
                    'event_type': 'mining',
                    'scheduled_start_time': (datetime.now() + timedelta(days=1)).isoformat(),
                    'organizer_name': 'Red Legion Admin',
                    'event_status': 'scheduled',
                    'auto_start_enabled': True
                }
            ]
            return {"events": mock_scheduled, "count": len(mock_scheduled)}
        
        async with pool.acquire() as conn:
            events = await conn.fetch("""
                SELECT event_id, event_name, event_type, organizer_name, 
                       scheduled_start_time, auto_start_enabled, event_status,
                       tracked_channels, primary_channel_id, created_at
                FROM events 
                WHERE event_status IN ('planned', 'scheduled')
                ORDER BY scheduled_start_time ASC NULLS LAST, created_at DESC
            """)
            
            return {
                "events": [dict(event) for event in events],
                "count": len(events)
            }
            
    except Exception as e:
        logger.error(f"Error fetching scheduled events: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch scheduled events")

@app.get("/events/{event_id}/live-metrics")
async def get_event_live_metrics(event_id: str, current_user: SessionData = Depends(get_current_user)):
    """Get real-time metrics for a live event."""
    try:
        pool = await get_db_pool()
        if pool is None:
            # Return mock live metrics when database is not available
            return {
                'event_id': event_id,
                'current_participants': 5,
                'total_unique_participants': 12,
                'event_duration_minutes': 45,
                'channel_breakdown': {
                    'Mining Alpha': 3,
                    'Mining Bravo': 2
                },
                'participant_list': [
                    {'username': 'Pilot1', 'duration_minutes': 45, 'is_active': True},
                    {'username': 'Pilot2', 'duration_minutes': 30, 'is_active': True}
                ]
            }
        
        async with pool.acquire() as conn:
            # Get current event status
            event_info = await conn.fetchrow("""
                SELECT event_id, event_name, event_status, started_at
                FROM events WHERE event_id = $1
            """, event_id)
            
            if not event_info:
                raise HTTPException(status_code=404, detail="Event not found")
            
            # Get current participant metrics
            participant_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(DISTINCT user_id) as total_participants,
                    COUNT(DISTINCT CASE WHEN is_currently_active THEN user_id END) as active_participants
                FROM participation 
                WHERE event_id = $1
            """, event_id)
            
            # Get channel breakdown
            channel_breakdown = await conn.fetch("""
                SELECT channel_name, COUNT(DISTINCT user_id) as participant_count
                FROM participation 
                WHERE event_id = $1 AND is_currently_active = true
                GROUP BY channel_name
            """, event_id)
            
            # Get individual participant list
            participants = await conn.fetch("""
                SELECT user_id, username, display_name, channel_name,
                       session_duration_seconds, is_currently_active,
                       joined_at, last_activity_update
                FROM participation 
                WHERE event_id = $1
                ORDER BY is_currently_active DESC, session_duration_seconds DESC
            """, event_id)
            
            # Calculate event duration
            event_duration_minutes = 0
            if event_info['started_at']:
                duration_seconds = (datetime.now() - event_info['started_at']).total_seconds()
                event_duration_minutes = int(duration_seconds / 60)
            
            return {
                'event_id': event_id,
                'event_name': event_info['event_name'],
                'event_status': event_info['event_status'],
                'event_duration_minutes': event_duration_minutes,
                'current_participants': participant_stats['active_participants'] if participant_stats else 0,
                'total_unique_participants': participant_stats['total_participants'] if participant_stats else 0,
                'channel_breakdown': {row['channel_name']: row['participant_count'] for row in channel_breakdown},
                'participant_list': [
                    {
                        'user_id': p['user_id'],
                        'username': p['username'],
                        'display_name': p['display_name'],
                        'channel_name': p['channel_name'],
                        'duration_minutes': int((p['session_duration_seconds'] or 0) / 60),
                        'is_active': p['is_currently_active'],
                        'last_activity': p['last_activity_update'].isoformat() if p['last_activity_update'] else None
                    }
                    for p in participants
                ]
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching live metrics for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch live metrics")

@app.get("/events/{event_id}/participant-history")
async def get_event_participant_history(event_id: str, hours: int = 24, current_user: SessionData = Depends(get_current_user)):
    """Get participant count history for graphing (from event_participant_snapshots)."""
    try:
        pool = await get_db_pool()
        if pool is None:
            # Return mock participant history
            now = datetime.now()
            mock_history = []
            for i in range(0, hours * 6):  # Every 10 minutes
                timestamp = now - timedelta(minutes=i * 10)
                mock_history.append({
                    'timestamp': timestamp.isoformat(),
                    'total_participants': random.randint(3, 15),
                    'active_participants': random.randint(1, 10)
                })
            return {'history': mock_history[::-1], 'event_id': event_id}
        
        async with pool.acquire() as conn:
            # Get participant snapshots for the last N hours
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            snapshots = await conn.fetch("""
                SELECT snapshot_time, total_participants, active_participants, channel_breakdown
                FROM event_participant_snapshots
                WHERE event_id = $1 AND snapshot_time >= $2
                ORDER BY snapshot_time ASC
            """, event_id, cutoff_time)
            
            return {
                'event_id': event_id,
                'history': [
                    {
                        'timestamp': snap['snapshot_time'].isoformat(),
                        'total_participants': snap['total_participants'],
                        'active_participants': snap['active_participants'],
                        'channel_breakdown': snap['channel_breakdown']
                    }
                    for snap in snapshots
                ]
            }
            
    except Exception as e:
        logger.error(f"Error fetching participant history for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch participant history")

# Session Management Admin Endpoints
@app.get("/admin/sessions/stats")
async def get_session_stats(admin_user: SessionData = Depends(get_admin_user)):
    """Get session statistics for monitoring (admin only)."""
    stats = session_manager.get_session_stats()

    # Add additional runtime stats
    stats.update({
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "admin_user": admin_user.username
    })

    return stats

@app.post("/admin/sessions/cleanup")
async def cleanup_expired_sessions(admin_user: SessionData = Depends(get_admin_user)):
    """Manually trigger cleanup of expired sessions (admin only)."""
    cleaned_count = await session_manager.cleanup_expired_sessions()

    return {
        "message": f"Cleaned up {cleaned_count} expired sessions",
        "cleaned_sessions": cleaned_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "admin_user": admin_user.username
    }

@app.delete("/admin/sessions/user/{user_id}")
async def invalidate_user_sessions(
    user_id: str,
    admin_user: SessionData = Depends(get_admin_user)
):
    """Invalidate all sessions for a specific user (admin only)."""
    # Validate user ID format
    validate_discord_id(user_id, "User ID")

    await session_manager.invalidate_all_user_sessions(user_id)

    return {
        "message": f"All sessions invalidated for user {user_id}",
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "admin_user": admin_user.username
    }

@app.post("/auth/refresh")
async def refresh_current_session(
    request: Request,
    current_user: SessionData = Depends(get_current_user)
):
    """Refresh current user's session."""
    # Get session token from cookies
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="No session token found")

    session_data = await session_manager.refresh_session(session_token)

    return {
        "message": "Session refreshed successfully",
        "expires_at": session_data.expires_at.isoformat(),
        "refresh_count": session_data.refresh_count,
        "user_id": current_user.user_id
    }

@app.get("/ping")
async def ping():
    """Simple ping endpoint for basic connectivity test."""
    return {
        "status": "ok",
        "message": "Red Legion backend is running",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/health")
async def health():
    """Health check endpoint with session and database status."""
    try:
        pool = await get_db_pool()
        db_status = "disconnected"
        mode = "mock"

        if pool is not None:
            # Test database connection
            async with pool.acquire() as connection:
                await connection.execute("SELECT 1")
            db_status = "connected"
            mode = "database"

        # Get session statistics safely
        try:
            session_stats = session_manager.get_session_stats()
            session_info = {
                "active": session_stats["active_sessions"],
                "total": session_stats["total_sessions"],
                "unique_users": session_stats["unique_users"]
            }
        except Exception as se:
            logger.warning(f"Session stats error: {se}")
            session_info = {"error": "session stats unavailable"}

        return {
            "status": "healthy",
            "database": db_status,
            "mode": mode,
            "sessions": session_info,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {"status": "degraded", "database": "error", "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)