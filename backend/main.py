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
import random
import string
import uuid
from datetime import datetime, timedelta, timezone
import json
from validation import (
    validate_discord_id, validate_event_id, validate_text_input,
    validate_positive_integer, validate_decimal_amount,
    EventCreateRequest, PayrollCalculateRequest, ChannelAddRequest,
    validate_pagination_params, log_validation_attempt
)

# Load environment variables
load_dotenv()

# Pydantic models for admin functions
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
                if 'id' not in channel or 'name' not in channel:
                    raise ValueError("Each tracked channel must have 'id' and 'name' fields")
        return v

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

# Bot API configuration
BOT_API_URL = os.getenv("BOT_API_URL", "http://localhost:8001")

async def start_bot_voice_tracking(event_id: str, guild_id: str, tracked_channels: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Start voice tracking for an event by calling the Discord bot API."""
    try:
        # Convert tracked_channels to the format expected by the bot
        channels = {}
        if tracked_channels:
            for i, channel in enumerate(tracked_channels):
                if isinstance(channel, dict) and 'id' in channel:
                    channel_name = channel.get('name', f'channel_{i}')
                    channels[channel_name] = str(channel['id'])

        # If no channels provided, use default mining channels
        if not channels:
            # Bot will use default channels for the guild
            channels = None

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{BOT_API_URL}/events/{event_id}/start-tracking",
                json={
                    "event_id": event_id,
                    "guild_id": int(guild_id),
                    "channels": channels
                }
            )

            if response.status_code == 200:
                bot_data = response.json()
                return {
                    "success": True,
                    "message": "Voice tracking started successfully",
                    "channels_tracked": bot_data.get("channels_tracked", 0),
                    "bot_response": bot_data
                }
            else:
                error_detail = response.text
                logger.error(f"Bot API error for event {event_id}: {response.status_code} - {error_detail}")
                return {
                    "success": False,
                    "error": f"Bot API returned {response.status_code}: {error_detail}",
                    "fallback": "Event created but voice tracking not started"
                }

    except httpx.TimeoutException:
        logger.error(f"Bot API timeout for event {event_id}")
        return {
            "success": False,
            "error": "Bot API timeout",
            "fallback": "Event created but voice tracking not started"
        }
    except Exception as e:
        logger.error(f"Bot integration error for event {event_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "fallback": "Event created but voice tracking not started"
        }

async def stop_bot_voice_tracking(event_id: str) -> Dict[str, Any]:
    """Stop voice tracking for an event by calling the Discord bot API."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{BOT_API_URL}/events/{event_id}/stop-tracking"
            )

            if response.status_code == 200:
                bot_data = response.json()
                return {
                    "success": True,
                    "message": "Voice tracking stopped successfully",
                    "bot_response": bot_data
                }
            else:
                error_detail = response.text
                logger.error(f"Bot API error stopping event {event_id}: {response.status_code} - {error_detail}")
                return {
                    "success": False,
                    "error": f"Bot API returned {response.status_code}: {error_detail}"
                }

    except httpx.TimeoutException:
        logger.error(f"Bot API timeout stopping event {event_id}")
        return {
            "success": False,
            "error": "Bot API timeout"
        }
    except Exception as e:
        logger.error(f"Bot integration error stopping event {event_id}: {e}")
        return {
            "success": False,
            "error": str(e)
        }

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
                    e.event_id, e.event_name, e.event_type, e.organizer_name, e.organizer_id,
                    e.status, e.started_at, e.ended_at, e.created_at, e.updated_at,
                    e.total_participants, e.total_duration_minutes,
                    e.location_notes, e.description as additional_notes,
                    false as payroll_calculated
                FROM events e
                ORDER BY e.created_at DESC
            """)

            return [dict(event) for event in events]

    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch events")

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
                SELECT DISTINCT ON (user_id)
                    id as participant_id, user_id, username, display_name,
                    joined_at, left_at, duration_minutes, is_org_member as is_organizer
                FROM participation
                WHERE event_id = $1
                ORDER BY user_id, joined_at ASC
            """, event_id)

            return [dict(participant) for participant in participants]

    except Exception as e:
        logger.error(f"Error fetching participants for {event_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch participants")

@app.get("/events/scheduled")
@app.get("/mgmt/api/events/scheduled")
async def get_scheduled_events():
    """Get scheduled events (future planned events)."""
    try:
        # Current system only tracks active mining sessions (open/closed)
        # No scheduled events exist in the current unified schema
        # Return empty array for frontend compatibility
        return []

    except Exception as e:
        logger.error(f"Error fetching scheduled events: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch scheduled events")

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

@app.get("/trading-locations")
@app.get("/mgmt/api/trading-locations")
async def get_trading_locations():
    """Get trading locations for payroll calculator."""
    try:
        # Return common Star Citizen trading locations
        # Orison should be the default option
        return [
            {
                "location_id": 4,
                "location_name": "Orison",
                "station_outpost": "Crusader",
                "system_name": "Stanton",
                "is_default": True
            },
            {
                "location_id": 1,
                "location_name": "Area 18",
                "station_outpost": "ArcCorp",
                "system_name": "Stanton",
                "is_default": False
            },
            {
                "location_id": 2,
                "location_name": "Lorville",
                "station_outpost": "Hurston",
                "system_name": "Stanton",
                "is_default": False
            },
            {
                "location_id": 3,
                "location_name": "New Babbage",
                "station_outpost": "microTech",
                "system_name": "Stanton",
                "is_default": False
            }
        ]
    except Exception as e:
        logger.error(f"Error fetching trading locations: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch trading locations")

@app.get("/material-prices/{materials}")
@app.get("/mgmt/api/material-prices/{materials}")
async def get_material_prices(materials: str):
    """Get material prices for specified materials."""
    try:
        # Parse the materials parameter
        material_names = [name.strip().upper() for name in materials.split(',')]

        # Get UEX prices
        uex_prices = get_fallback_uex_prices()

        # Define best selling locations for different materials
        best_locations = {
            'QUANTAINIUM': {"location": "Orison", "system": "Stanton", "station": "Crusader"},
            'BEXALITE': {"location": "Area 18", "system": "Stanton", "station": "ArcCorp"},
            'TARANITE': {"location": "Lorville", "system": "Stanton", "station": "Hurston"},
            'LARANITE': {"location": "New Babbage", "system": "Stanton", "station": "microTech"},
            'TITANIUM': {"location": "Area 18", "system": "Stanton", "station": "ArcCorp"},
            'COPPER': {"location": "Lorville", "system": "Stanton", "station": "Hurston"},
            'DIAMOND': {"location": "Orison", "system": "Stanton", "station": "Crusader"},
            'GOLD': {"location": "Area 18", "system": "Stanton", "station": "ArcCorp"},
            'AGRICIUM': {"location": "Orison", "system": "Stanton", "station": "Crusader"},
            'BERYL': {"location": "New Babbage", "system": "Stanton", "station": "microTech"},
            'BORASE': {"location": "Lorville", "system": "Stanton", "station": "Hurston"},
            'HEPHAESTANITE': {"location": "Area 18", "system": "Stanton", "station": "ArcCorp"},
            'HADANITE': {"location": "Orison", "system": "Stanton", "station": "Crusader"},
        }

        # Filter for requested materials and format as array
        price_list = []
        for material in material_names:
            if material in uex_prices:
                best_loc = best_locations.get(material, {"location": "Orison", "system": "Stanton", "station": "Crusader"})
                price_list.append({
                    "material_name": material,
                    "highest_price": uex_prices[material],
                    "best_location": best_loc["location"],
                    "best_system": best_loc["system"],
                    "best_station": best_loc["station"]
                })

        return price_list
    except Exception as e:
        logger.error(f"Error fetching material prices for {materials}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch material prices")

@app.get("/location-prices/{location_id}")
@app.get("/mgmt/api/location-prices/{location_id}")
async def get_location_prices(location_id: str, materials: str = ""):
    """Get location-specific material prices."""
    try:
        # Parse the materials parameter
        material_names = [name.strip().upper() for name in materials.split(',') if name.strip()]

        # Get base UEX prices
        base_prices = get_fallback_uex_prices()

        # Apply location modifiers using numeric IDs
        location_modifiers = {
            4: 1.0,     # Orison - Base prices
            1: 0.95,    # Area 18 - Slightly lower
            2: 0.92,    # Lorville - Lower prices
            3: 0.98     # New Babbage - Slightly lower
        }

        try:
            location_id_int = int(location_id)
            modifier = location_modifiers.get(location_id_int, 1.0)
        except ValueError:
            modifier = 1.0

        # Filter for requested materials and apply location modifier, format as array
        price_list = []
        for material in material_names:
            if material in base_prices:
                price_list.append({
                    "material_name": material,
                    "sell_price": round(base_prices[material] * modifier, 2)
                })

        return price_list
    except Exception as e:
        logger.error(f"Error fetching location prices for {location_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch location prices")

# Pydantic models for payroll calculation
class PayrollCalculateRequest(BaseModel):
    ore_quantities: Dict[str, float]
    custom_prices: Optional[Dict[str, float]] = None
    donating_users: List[str] = []

@app.post("/payroll/{event_id}/calculate")
@app.post("/mgmt/api/payroll/{event_id}/calculate")
async def calculate_payroll(event_id: str, request: PayrollCalculateRequest):
    """Calculate payroll for a mining event."""
    try:
        event_id = validate_event_id(event_id)

        # Get event details
        pool = await get_db_pool()
        if pool is None:
            # Mock mode - generate test payroll calculation
            return await generate_mock_payroll_calculation(event_id, request)

        async with pool.acquire() as conn:
            # Get event info
            event = await conn.fetchrow("""
                SELECT event_id, event_name, total_participants, total_duration_minutes
                FROM events
                WHERE event_id = $1
            """, event_id)

            if not event:
                raise HTTPException(status_code=404, detail="Event not found")

            # Get event participants with their time contributions
            participants = await conn.fetch("""
                SELECT user_id, username, display_name, duration_minutes, is_org_member
                FROM participation
                WHERE event_id = $1 AND duration_minutes > 0
                ORDER BY duration_minutes DESC
            """, event_id)

        # Use custom prices if provided, otherwise get UEX prices
        if request.custom_prices:
            prices = request.custom_prices
        else:
            prices = get_fallback_uex_prices()

        # Calculate total ore value
        total_ore_value = 0
        ore_breakdown = {}

        for ore, quantity in request.ore_quantities.items():
            ore_upper = ore.upper()
            price_per_scu = prices.get(ore_upper, 0)
            ore_value = quantity * price_per_scu
            total_ore_value += ore_value
            ore_breakdown[ore_upper] = {
                "quantity": quantity,
                "price_per_scu": price_per_scu,
                "total_value": ore_value
            }

        # Calculate total participation time
        total_participation_time = sum(p['duration_minutes'] for p in participants)

        if total_participation_time == 0:
            raise HTTPException(status_code=400, detail="No valid participation time found")

        # Calculate payouts based on time participation
        payouts = []
        total_donated = 0

        # Debug logging for donation logic
        logger.info(f"💰 Payroll calculation for {event_id}:")
        logger.info(f"  - Total participants: {len(participants)}")
        logger.info(f"  - Donating user IDs received: {request.donating_users}")
        logger.info(f"  - Total ore value: {total_ore_value:,.2f} aUEC")

        for participant in participants:
            user_id_str = str(participant['user_id'])
            time_percentage = participant['duration_minutes'] / total_participation_time
            base_payout = total_ore_value * time_percentage

            # Check if user is donating their share
            is_donating = user_id_str in request.donating_users

            logger.info(f"  - {participant['username']} (ID: {user_id_str}): {base_payout:.2f} aUEC, donating: {is_donating}")

            if is_donating:
                total_donated += base_payout
                final_payout = 0
            else:
                final_payout = base_payout

            payouts.append({
                "user_id": participant['user_id'],
                "username": participant['username'],
                "display_name": participant['display_name'],
                "duration_minutes": participant['duration_minutes'],
                "participation_minutes": participant['duration_minutes'],  # Frontend expects this field name
                "time_percentage": round(time_percentage * 100, 2),
                "participation_percentage": round(time_percentage * 100, 2),  # Frontend expects this field name
                "base_payout": round(base_payout, 2),
                "is_donating": is_donating,
                "final_payout": round(final_payout, 2),
                "final_payout_auec": round(final_payout, 2),  # Frontend expects this field name
                "is_org_member": participant['is_org_member']
            })

        # Redistribute donations among non-donating participants
        non_donating_participants = [p for p in payouts if not p['is_donating']]

        logger.info(f"🎁 Donation redistribution:")
        logger.info(f"  - Total donated: {total_donated:,.2f} aUEC")
        logger.info(f"  - Non-donating participants: {len(non_donating_participants)}")

        if non_donating_participants and total_donated > 0:
            donation_per_person = total_donated / len(non_donating_participants)
            logger.info(f"  - Donation per person: {donation_per_person:,.2f} aUEC")

            for payout in payouts:
                if not payout['is_donating']:
                    payout['donation_bonus'] = round(donation_per_person, 2)
                    new_final_payout = round(payout['final_payout'] + donation_per_person, 2)
                    payout['final_payout'] = new_final_payout
                    payout['final_payout_auec'] = new_final_payout  # Keep both fields in sync
                    logger.info(f"    + {payout['username']}: {payout['final_payout']:.2f} aUEC (base: {payout['base_payout']:.2f} + bonus: {donation_per_person:.2f})")
                else:
                    payout['donation_bonus'] = 0
                    logger.info(f"    - {payout['username']}: 0 aUEC (donated)")
        else:
            logger.info(f"  - No redistribution needed")
            for payout in payouts:
                payout['donation_bonus'] = 0

        # Calculate summary
        total_payouts = sum(p['final_payout'] for p in payouts)
        total_scu = sum(request.ore_quantities.values())

        result = {
            "event_id": event_id,
            "event_name": event['event_name'],
            "calculation_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_ore_value_auec": round(total_ore_value, 2),
            "total_value_auec": round(total_ore_value, 2),  # Frontend compatibility
            "total_donated_auec": round(total_donated, 2),
            "total_payouts_auec": round(total_payouts, 2),
            "total_scu": round(total_scu, 2),  # Add total SCU for frontend
            "ore_breakdown": ore_breakdown,
            "payouts": payouts,
            "summary": {
                "total_participants": len(participants),
                "donating_participants": len([p for p in payouts if p['is_donating']]),
                "total_participation_minutes": total_participation_time,
                "average_payout": round(total_payouts / len(payouts), 2) if payouts else 0
            }
        }

        return result

    except Exception as e:
        logger.error(f"Error calculating payroll for {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate payroll: {str(e)}")

@app.post("/payroll/{event_id}/finalize")
@app.post("/mgmt/api/payroll/{event_id}/finalize")
async def finalize_payroll(event_id: str, request: PayrollCalculateRequest):
    """Finalize and save payroll to database."""
    try:
        event_id = validate_event_id(event_id)

        # First calculate the payroll
        result = await calculate_payroll(event_id, request)

        pool = await get_db_pool()
        if pool is None:
            # Mock mode - return calculated result with generated payroll_id
            result["payroll_id"] = f"payroll-{event_id}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
            result["status"] = "closed"
            result["message"] = "Payroll finalized successfully (mock mode)"
            return result

        async with pool.acquire() as conn:
            async with conn.transaction():
                # Generate unique payroll ID
                payroll_id = f"payroll-{event_id}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

                # Insert payroll record
                await conn.execute("""
                    INSERT INTO payrolls (
                        payroll_id, event_id, status, calculation_timestamp,
                        total_ore_value_auec, total_donated_auec, total_payouts_auec,
                        total_scu, ore_breakdown, summary_data, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
                """,
                    payroll_id, event_id, 'closed', datetime.now(timezone.utc),
                    result['total_ore_value_auec'], result['total_donated_auec'],
                    result['total_payouts_auec'], result['total_scu'],
                    json.dumps(result['ore_breakdown']), json.dumps(result['summary']),
                )

                # Insert individual payouts
                for payout in result['payouts']:
                    await conn.execute("""
                        INSERT INTO payouts (
                            payroll_id, user_id, username, display_name,
                            duration_minutes, participation_percentage, base_payout_auec,
                            donation_bonus_auec, final_payout_auec, is_donating, is_org_member
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    """,
                        payroll_id, payout['user_id'], payout['username'], payout['display_name'],
                        payout['duration_minutes'], payout['participation_percentage'],
                        payout['base_payout'], payout.get('donation_bonus', 0),
                        payout['final_payout'], payout['is_donating'], payout['is_org_member']
                    )

                logger.info(f"✅ Payroll {payroll_id} finalized and saved to database: {len(result['payouts'])} participants")

        # Add payroll metadata to response
        result["payroll_id"] = payroll_id
        result["status"] = "closed"
        result["message"] = "Payroll finalized and saved to database"

        return result

    except Exception as e:
        logger.error(f"Error finalizing payroll for {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to finalize payroll: {str(e)}")

@app.get("/admin/payroll-export/{event_id}")
@app.get("/mgmt/api/admin/payroll-export/{event_id}")
async def export_payroll(event_id: str):
    """Export payroll as PDF (placeholder implementation)."""
    try:
        # For now, return a placeholder response
        # In a real implementation, this would generate a PDF
        return {
            "export_url": f"/downloads/payroll-{event_id}.pdf",
            "filename": f"payroll-{event_id}.pdf",
            "status": "generated",
            "message": "PDF export functionality is not implemented yet"
        }

    except Exception as e:
        logger.error(f"Error exporting payroll for {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export payroll: {str(e)}")

@app.post("/events/{event_id}/close")
@app.post("/mgmt/api/events/{event_id}/close")
async def close_event(event_id: str):
    """Close an active mining event."""
    try:
        event_id = validate_event_id(event_id)

        pool = await get_db_pool()
        if pool is None:
            raise HTTPException(status_code=500, detail="Database connection failed")

        async with pool.acquire() as conn:
            async with conn.transaction():
                # Update event to closed status
                result = await conn.execute("""
                    UPDATE events
                    SET status = 'closed',
                        ended_at = NOW(),
                        updated_at = NOW()
                    WHERE event_id = $1 AND status = 'open'
                """, event_id)

                if result == "UPDATE 0":
                    raise HTTPException(status_code=404, detail="Event not found or already closed")

                # Create an open payroll for this event
                payroll_id = f"payroll-{event_id}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
                await conn.execute("""
                    INSERT INTO payrolls (
                        payroll_id, event_id, status, created_at
                    ) VALUES ($1, $2, $3, NOW())
                """, payroll_id, event_id, 'open')

                # Get updated event info
                event = await conn.fetchrow("""
                    SELECT event_id, event_name, total_participants, total_duration_minutes, status, ended_at
                    FROM events
                    WHERE event_id = $1
                """, event_id)

                logger.info(f"✅ Event {event_id} closed and payroll {payroll_id} created with status 'open'")

                # Stop voice tracking via bot API
                bot_integration_result = await stop_bot_voice_tracking(event_id)

                return {
                    "event_id": event_id,
                    "status": "closed",
                    "ended_at": event['ended_at'].isoformat() if event['ended_at'] else None,
                    "total_participants": event['total_participants'] or 0,
                    "total_duration_minutes": event['total_duration_minutes'] or 0,
                    "payroll_id": payroll_id,
                    "payroll_status": "open",
                    "message": f"Event {event_id} closed and payroll {payroll_id} created (ready for calculations)",
                    "discord_integration": bot_integration_result
                }

    except Exception as e:
        logger.error(f"Error closing event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to close event: {str(e)}")

@app.get("/payroll/{event_id}/export")
@app.get("/mgmt/api/payroll/{event_id}/export")
async def export_payroll(event_id: str):
    """Export payroll data for an event (placeholder for PDF generation)."""
    try:
        event_id = validate_event_id(event_id)

        pool = await get_db_pool()
        if pool is None:
            raise HTTPException(status_code=500, detail="Database connection failed")

        async with pool.acquire() as conn:
            # Get event details
            event = await conn.fetchrow("""
                SELECT event_id, event_name, status, created_at, ended_at,
                       total_participants, total_duration_minutes
                FROM events
                WHERE event_id = $1
            """, event_id)

            if not event:
                raise HTTPException(status_code=404, detail="Event not found")

            # TODO: Implement proper payroll data retrieval from correct database schema
            # For now, return empty data
            payroll_data = []

            # Calculate totals
            total_payout = sum(p['final_payout_auec'] for p in payroll_data if p['final_payout_auec'])
            total_participants = len(payroll_data)

            export_data = {
                "event_id": event_id,
                "event_name": event['event_name'],
                "status": event['status'],
                "created_at": event['created_at'].isoformat() if event['created_at'] else None,
                "ended_at": event['ended_at'].isoformat() if event['ended_at'] else None,
                "total_participants": total_participants,
                "total_payout_auec": total_payout,
                "participants": [
                    {
                        "user_id": p['user_id'],
                        "username": p['username'],
                        "participation_minutes": p['participation_minutes'] or 0,
                        "participation_percentage": round(p['participation_percentage'] or 0, 2),
                        "final_payout_auec": int(p['final_payout_auec'] or 0)
                    }
                    for p in payroll_data
                ],
                "export_timestamp": datetime.now().isoformat(),
                "pdf_url": f"/payroll/{event_id}/export.pdf"  # Placeholder for future PDF endpoint
            }

            logger.info(f"Exported payroll data for event {event_id}: {total_participants} participants, {total_payout:,} aUEC total")
            return export_data

    except Exception as e:
        logger.error(f"Error exporting payroll for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export payroll: {str(e)}")

@app.get("/payroll/{event_id}/summary")
@app.get("/mgmt/api/payroll/{event_id}/summary")
async def get_payroll_summary(event_id: str):
    """Get payroll summary for a closed event."""
    try:
        event_id = validate_event_id(event_id)

        pool = await get_db_pool()
        if pool is None:
            raise HTTPException(status_code=500, detail="Database connection failed")

        async with pool.acquire() as conn:
            # Get event details
            event = await conn.fetchrow("""
                SELECT event_id, event_name, event_type, organizer_name, status,
                       started_at, ended_at, total_participants, total_duration_minutes
                FROM events
                WHERE event_id = $1
            """, event_id)

            if not event:
                raise HTTPException(status_code=404, detail="Event not found")

            # TODO: Implement proper payroll data retrieval from correct database schema
            # For now, return empty data
            payroll_data = []

            # Return empty structure if no payroll data (expected for now)
            if not payroll_data:
                logger.info(f"No payroll data found for event {event_id} (expected during transition)")

            # Calculate statistics
            total_payout = sum(p['final_payout_auec'] for p in payroll_data if p['final_payout_auec'])
            total_participation = sum(p['participation_minutes'] for p in payroll_data if p['participation_minutes'])
            average_payout = total_payout / len(payroll_data) if payroll_data else 0

            # TODO: Get latest payroll calculation metadata from correct schema
            # For now, use placeholder data
            payroll_meta = None

            # Structure response similar to what the frontend expects
            summary_data = {
                "event": {
                    "event_id": event['event_id'],
                    "event_name": event['event_name'],
                    "event_type": event['event_type'],
                    "organizer_name": event['organizer_name'],
                    "status": event['status'],
                    "started_at": event['started_at'].isoformat() if event['started_at'] else None,
                    "ended_at": event['ended_at'].isoformat() if event['ended_at'] else None,
                    "total_participants": event['total_participants'] or 0,
                    "total_duration_minutes": event['total_duration_minutes'] or 0
                },
                "payroll": {
                    "calculated_by_name": payroll_meta['calculated_by_name'] if payroll_meta else "Unknown",
                    "calculation_timestamp": payroll_meta['calculation_timestamp'].isoformat() if payroll_meta and payroll_meta['calculation_timestamp'] else None
                },
                "statistics": {
                    "total_payout_auec": int(total_payout),
                    "average_payout_auec": int(average_payout),
                    "total_participation_minutes": int(total_participation),
                    "total_scu_collected": None,  # Could be calculated from ore_quantities if available
                    "ore_breakdown": None  # Could be reconstructed if ore_quantities stored
                },
                "payouts": [
                    {
                        "user_id": p['user_id'],
                        "username": p['username'],
                        "participation_minutes": p['participation_minutes'] or 0,
                        "participation_percentage": round(p['participation_percentage'] or 0, 2),
                        "base_payout_auec": int(p['base_payout_auec'] or 0),
                        "final_payout_auec": int(p['final_payout_auec'] or 0),
                        "donation_bonus": int(p['donation_bonus'] or 0),
                        "is_donor": bool(p['is_donating'])
                    }
                    for p in payroll_data
                ]
            }

            logger.info(f"Retrieved payroll summary for event {event_id}: {len(payroll_data)} participants, {total_payout:,} aUEC total")
            return summary_data

    except Exception as e:
        logger.error(f"Error getting payroll summary for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get payroll summary: {str(e)}")

# Admin Functions
@app.post("/admin/create-test-event/{event_type}")
@app.post("/mgmt/api/admin/create-test-event/{event_type}")
async def create_test_event(event_type: str):
    """Create a test event with random participants and data."""
    valid_event_types = ["mining", "salvage", "combat", "exploration", "trading", "social"]
    if event_type not in valid_event_types:
        raise HTTPException(status_code=400, detail=f"Event type must be one of: {', '.join(valid_event_types)}")

    try:
        pool = await get_db_pool()
        if pool is None:
            # Return mock success response when database is not available
            event_id = f'test_{uuid.uuid4().hex[:8]}'
            num_participants = random.randint(5, 25)
            duration_hours = random.randint(1, 7)
            event_name = f'Test {event_type.title()} Op {random.randint(100, 999)}'

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
                    'status': 'completed'
                }
            }

        async with pool.acquire() as conn:
            async with conn.transaction():
                # Generate random event data
                event_id = generate_event_id()
                num_participants = random.randint(5, 25)
                duration_hours = random.randint(1, 7)
                duration_minutes = duration_hours * 60

                # Random start time between 1-30 days ago
                days_ago = random.randint(1, 30)
                started_at = datetime.utcnow() - timedelta(days=days_ago)
                ended_at = started_at + timedelta(hours=duration_hours)

                event_name = f"Test {event_type.title()} Op {random.randint(100, 999)}"

                # Generate realistic organizer data
                test_display_names = [
                    "NewSticks", "Saladin80", "Tealstone", "LowNslow", "Ferny133",
                    "Jaeger31", "Blitz0117", "Prometheus114", "RockHound", "CrystalCrafter",
                    "VoidRunner", "AsteroidAce", "QuantumMiner", "StellarSalvage",
                    "SpaceRanger", "CosmicCrawler", "MetalHarvester", "SystemScanner",
                    "FleetCommander", "WingLeader", "TradeCaptain", "ExplorerOne",
                    "CombatVet", "CargoHauler", "RouteRunner", "DeepSpaceScout"
                ]
                organizer_name = random.choice(test_display_names)
                organizer_id = random.randint(100000000000000000, 999999999999999999)

                # Create the event
                await conn.execute("""
                    INSERT INTO events (
                        event_id, event_type, event_name, organizer_name, organizer_id,
                        guild_id, started_at, ended_at, status, total_participants,
                        total_duration_minutes, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                    event_id, event_type, event_name, organizer_name, organizer_id,
                    814699481912049704, started_at, ended_at, 'closed', num_participants,
                    duration_minutes, datetime.utcnow()
                )

                # Generate random participants
                fake_users = await generate_fake_participants(num_participants)
                total_participation_time = 0

                for user in fake_users:
                    # Random participation time (15-240 minutes)
                    participation_minutes = random.randint(15, min(240, duration_minutes))
                    total_participation_time += participation_minutes

                    # Random join time within event duration
                    max_join_offset = max(1, duration_minutes - participation_minutes)
                    join_offset = random.randint(0, max_join_offset)
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
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"sm-{suffix}"

async def generate_fake_participants(count: int):
    """Generate fake participant data for testing."""
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
        username = random.choice(fake_usernames)
        counter = 1
        original_username = username
        while username in used_names:
            username = f"{original_username}{counter}"
            counter += 1
        used_names.add(username)

        display_name = random.choice(fake_display_names)
        user_id = random.randint(100000000000000000, 999999999999999999)

        participants.append({
            'user_id': user_id,
            'username': username,
            'display_name': display_name
        })

    return participants

async def generate_mock_payroll_calculation(event_id: str, request: PayrollCalculateRequest):
    """Generate mock payroll calculation for testing donations."""
    # Mock event and participants data
    mock_participants = [
        {"user_id": 123456789, "username": "TestMiner1", "display_name": "Test Miner One", "duration_minutes": 120, "is_org_member": True},
        {"user_id": 987654321, "username": "TestMiner2", "display_name": "Test Miner Two", "duration_minutes": 90, "is_org_member": True},
        {"user_id": 555666777, "username": "TestMiner3", "display_name": "Test Miner Three", "duration_minutes": 60, "is_org_member": True},
        {"user_id": 111222333, "username": "TestMiner4", "display_name": "Test Miner Four", "duration_minutes": 180, "is_org_member": True},
    ]

    # Calculate ore values
    default_prices = {
        'QUANTAINIUM': 275500.0,
        'BEXALITE': 10750.0,
        'TARANITE': 8750.0,
        'AGRICIUM': 44250.0,
    }

    total_ore_value = 0
    ore_breakdown = {}

    for ore_name, quantity in request.ore_quantities.items():
        ore_upper = ore_name.upper()
        if request.custom_prices and ore_upper in request.custom_prices:
            price_per_scu = request.custom_prices[ore_upper]
        else:
            price_per_scu = default_prices.get(ore_upper, 10000.0)  # Default fallback

        ore_value = quantity * price_per_scu
        total_ore_value += ore_value
        ore_breakdown[ore_upper] = {
            "quantity": quantity,
            "price_per_scu": price_per_scu,
            "total_value": ore_value
        }

    # Calculate payouts with donation logic
    total_participation_time = sum(p['duration_minutes'] for p in mock_participants)
    payouts = []
    total_donated = 0

    logger.info(f"💰 Mock payroll calculation for {event_id}:")
    logger.info(f"  - Total participants: {len(mock_participants)}")
    logger.info(f"  - Donating user IDs received: {request.donating_users}")
    logger.info(f"  - Total ore value: {total_ore_value:,.2f} aUEC")

    for participant in mock_participants:
        user_id_str = str(participant['user_id'])
        time_percentage = participant['duration_minutes'] / total_participation_time
        base_payout = total_ore_value * time_percentage

        # Check if user is donating their share
        is_donating = user_id_str in request.donating_users
        logger.info(f"  - {participant['username']} (ID: {user_id_str}): {base_payout:.2f} aUEC, donating: {is_donating}")

        if is_donating:
            total_donated += base_payout
            final_payout = 0
        else:
            final_payout = base_payout

        payouts.append({
            "user_id": participant['user_id'],
            "username": participant['username'],
            "display_name": participant['display_name'],
            "duration_minutes": participant['duration_minutes'],
            "participation_minutes": participant['duration_minutes'],
            "time_percentage": round(time_percentage * 100, 2),
            "participation_percentage": round(time_percentage * 100, 2),
            "base_payout": round(base_payout, 2),
            "is_donating": is_donating,
            "final_payout": round(final_payout, 2),
            "final_payout_auec": round(final_payout, 2),
            "is_org_member": participant['is_org_member']
        })

    # Redistribute donations among non-donating participants
    non_donating_participants = [p for p in payouts if not p['is_donating']]
    logger.info(f"🎁 Mock donation redistribution:")
    logger.info(f"  - Total donated: {total_donated:,.2f} aUEC")
    logger.info(f"  - Non-donating participants: {len(non_donating_participants)}")

    if non_donating_participants and total_donated > 0:
        donation_per_person = total_donated / len(non_donating_participants)
        logger.info(f"  - Donation per person: {donation_per_person:,.2f} aUEC")

        for payout in payouts:
            if not payout['is_donating']:
                payout['donation_bonus'] = round(donation_per_person, 2)
                new_final_payout = round(payout['final_payout'] + donation_per_person, 2)
                payout['final_payout'] = new_final_payout
                payout['final_payout_auec'] = new_final_payout
                logger.info(f"    + {payout['username']}: {payout['final_payout']:.2f} aUEC (base: {payout['base_payout']:.2f} + bonus: {donation_per_person:.2f})")
            else:
                payout['donation_bonus'] = 0
                logger.info(f"    - {payout['username']}: 0 aUEC (donated)")
    else:
        logger.info(f"  - No redistribution needed")
        for payout in payouts:
            payout['donation_bonus'] = 0

    # Calculate summary
    total_payouts = sum(p['final_payout'] for p in payouts)
    total_scu = sum(request.ore_quantities.values())

    return {
        "event_id": event_id,
        "event_name": f"Mock Event {event_id}",
        "calculation_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_ore_value_auec": round(total_ore_value, 2),
        "total_value_auec": round(total_ore_value, 2),
        "total_donated_auec": round(total_donated, 2),
        "total_payouts_auec": round(total_payouts, 2),
        "total_scu": round(total_scu, 2),
        "ore_breakdown": ore_breakdown,
        "payouts": payouts,
        "summary": {
            "total_participants": len(mock_participants),
            "donating_participants": len([p for p in payouts if p['is_donating']]),
            "total_participation_minutes": total_participation_time,
            "average_payout": round(total_payouts / len(payouts), 2) if payouts else 0
        },
        "mock_mode": True
    }

@app.delete("/admin/events/{event_id}")
@app.delete("/mgmt/api/admin/events/{event_id}")
async def delete_event(event_id: str):
    """Delete an event and all associated data."""
    try:
        event_id = validate_event_id(event_id)

        pool = await get_db_pool()
        if pool is None:
            raise HTTPException(status_code=500, detail="Database connection failed")

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

                # 2. Delete payrolls (references events)
                await conn.execute(
                    "DELETE FROM payrolls WHERE event_id = $1",
                    event_id
                )

                # 3. Delete participation records (references events)
                await conn.execute(
                    "DELETE FROM participation WHERE event_id = $1",
                    event_id
                )

                # 4. Delete salvage inventory if it exists (references events)
                await conn.execute(
                    "DELETE FROM salvage_inventory WHERE event_id = $1",
                    event_id
                )

                # 5. Finally delete the event itself
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

@app.post("/admin/refresh-uex-cache")
@app.post("/mgmt/api/admin/refresh-uex-cache")
async def refresh_uex_cache():
    """Force refresh of UEX price cache via bot API."""
    logger.info("🔄 Manual UEX cache refresh requested")
    try:
        # Try to trigger cache refresh via the bot API
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{BOT_API_URL}/api/refresh-uex-cache")
            if response.status_code == 200:
                refresh_data = response.json()
                logger.info("✅ Successfully triggered UEX cache refresh via bot API")
                return {
                    "success": True,
                    "message": "UEX cache refresh triggered via bot API",
                    "bot_response": refresh_data,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                logger.warning(f"⚠️ Bot API refresh endpoint returned {response.status_code}: {response.text}")
                return {
                    "success": False,
                    "error": f"Bot API returned {response.status_code}: {response.text}",
                    "timestamp": datetime.now().isoformat()
                }
    except Exception as e:
        logger.error(f"❌ Could not trigger UEX cache refresh via bot API: {e}")
        return {
            "success": False,
            "error": f"Failed to communicate with bot API: {str(e)}",
            "fallback_note": "UEX cache refresh must be done manually on the bot server",
            "timestamp": datetime.now().isoformat()
        }

@app.post("/events/create")
@app.post("/mgmt/api/events/create")
async def create_event(request: EventCreationRequest):
    """Create a new event compatible with payroll system (no-auth version)."""
    try:
        pool = await get_db_pool()
        if pool is None:
            # Return mock success response when database is not available
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

            # Integrate with Discord bot for voice tracking
            bot_integration_result = await start_bot_voice_tracking(
                event_id,
                request.guild_id,
                request.tracked_channels
            )

            return {
                "success": True,
                "message": "Event created successfully",
                "event": dict(event_data),
                "discord_integration": bot_integration_result
            }

    except Exception as e:
        logger.error(f"Error creating event: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to create event")

@app.get("/discord/channels")
@app.get("/mgmt/api/discord/channels")
async def get_discord_channels(guild_id: str = "814699481912049704"):
    """Get all available Discord voice channels for the guild."""
    try:
        pool = await get_db_pool()
        if pool is None:
            # Return empty channels when database is not available - no point in fake channels
            return {
                "channels": [],
                "message": "Discord channels unavailable - database not connected"
            }

        async with pool.acquire() as conn:
            # Try to get channels from discord_channels table
            try:
                channels = await conn.fetch("""
                    SELECT channel_id, channel_name, channel_type, category_name, is_active
                    FROM discord_channels
                    WHERE guild_id = $1 AND channel_type = 'voice' AND is_active = true
                    ORDER BY category_name, channel_name
                """, int(guild_id))

                if channels:
                    channel_list = [
                        {
                            "id": str(row["channel_id"]),
                            "name": row["channel_name"],
                            "type": row["channel_type"],
                            "category": row["category_name"] or "general"
                        }
                        for row in channels
                    ]
                    return {
                        "channels": channel_list,
                        "message": f"Loaded {len(channel_list)} voice channels from database"
                    }
                else:
                    # No channels in database
                    return {
                        "channels": [],
                        "message": "No Discord channels found in database - sync channels first"
                    }

            except Exception as table_error:
                logger.warning(f"discord_channels table not available, using fallback: {table_error}")
                # Fallback to mining_channels table
                try:
                    mining_channels = await conn.fetch("""
                        SELECT channel_id, channel_name
                        FROM mining_channels
                        WHERE is_active = true
                        ORDER BY channel_name
                    """)

                    if mining_channels:
                        channel_list = [
                            {
                                "id": str(row["channel_id"]),
                                "name": row["channel_name"],
                                "type": "voice",
                                "category": "mining"
                            }
                            for row in mining_channels
                        ]
                        return {
                            "channels": channel_list,
                            "message": f"Loaded {len(channel_list)} mining channels from database"
                        }
                except Exception:
                    pass

                # No tables available
                return {
                    "channels": [],
                    "message": "Discord channels table not found - database not set up"
                }

    except Exception as e:
        logger.error(f"Error fetching Discord channels: {e}")
        # Return empty channels on any error - no point in fake channels
        return {
            "channels": [],
            "message": f"Discord channels unavailable - error: {str(e)}"
        }

@app.post("/discord/channels/sync")
@app.post("/mgmt/api/discord/channels/sync")
async def sync_discord_channels(guild_id: str = "814699481912049704"):
    """Sync Discord channels from Discord API using bot integration."""
    try:
        pool = await get_db_pool()
        if pool is None:
            return {
                "success": False,
                "message": "Database not available - cannot sync channels",
                "channels_synced": 0
            }

        # Import and use the Discord API client
        from services.discord_api import sync_discord_channels_to_db

        # Use the Discord API client to fetch and sync real channels
        result = await sync_discord_channels_to_db(guild_id, pool)

        return result

    except ImportError:
        logger.error("Discord API service not available")
        return {
            "success": False,
            "message": "Discord API service not available",
            "channels_synced": 0
        }
    except Exception as e:
        logger.error(f"Error syncing Discord channels: {e}")
        return {
            "success": False,
            "message": f"Failed to sync channels: {str(e)}",
            "channels_synced": 0
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