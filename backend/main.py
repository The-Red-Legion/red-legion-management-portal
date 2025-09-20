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
            raise HTTPException(status_code=500, detail="Database connection failed")

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
            raise HTTPException(status_code=500, detail="Database connection failed")

        async with pool.acquire() as conn:
            # TODO: Implement proper payroll storage using correct database schema
            # For now, just return the calculated result
            logger.info(f"Payroll calculation completed for event {event_id}: {len(result['payouts'])} participants")

        # Add a payroll_id for the response
        result["payroll_id"] = f"payroll-{event_id}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        result["status"] = "finalized"

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

            # Get updated event info
            event = await conn.fetchrow("""
                SELECT event_id, event_name, total_participants, total_duration_minutes, status, ended_at
                FROM events
                WHERE event_id = $1
            """, event_id)

            return {
                "event_id": event_id,
                "status": "closed",
                "ended_at": event['ended_at'].isoformat() if event['ended_at'] else None,
                "total_participants": event['total_participants'] or 0,
                "total_duration_minutes": event['total_duration_minutes'] or 0,
                "message": f"Event {event_id} has been closed successfully"
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