"""Event management endpoints."""

from fastapi import APIRouter, HTTPException, Request
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any
import random
import string
import json
import logging

from database import get_db_pool
from validation import validate_event_id, EventCreationRequest
from services.discord_integration import trigger_voice_tracking_on_event_start, trigger_voice_tracking_on_event_stop

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/events")
@router.get("/mgmt/api/events")
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
                    CASE WHEN p.payroll_id IS NOT NULL THEN true ELSE false END as payroll_calculated
                FROM events e
                LEFT JOIN payrolls p ON e.event_id = p.event_id
                ORDER BY e.created_at DESC
            """)

            return [dict(event) for event in events]

    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch events")

@router.get("/events/{event_id}/participants")
@router.get("/mgmt/api/events/{event_id}/participants")
async def get_event_participants(event_id: str):
    """Get participants for a specific event."""
    event_id = validate_event_id(event_id)

    try:
        pool = await get_db_pool()
        if pool is None:
            return []

        async with pool.acquire() as conn:
            # First get the participants with their individual durations
            participants = await conn.fetch("""
                SELECT DISTINCT ON (user_id)
                    id as participant_id, user_id, username, display_name,
                    joined_at, left_at, duration_minutes, is_org_member as is_organizer
                FROM participation
                WHERE event_id = $1
                ORDER BY user_id, joined_at ASC
            """, event_id)

            # Calculate total duration for percentage calculation
            total_duration = sum(p['duration_minutes'] for p in participants if p['duration_minutes'])

            # Build response with the expected field names
            result = []
            for participant in participants:
                duration_mins = participant['duration_minutes'] or 0
                percentage = (duration_mins / total_duration * 100) if total_duration > 0 else 0

                result.append({
                    'participant_id': participant['participant_id'],
                    'user_id': participant['user_id'],
                    'username': participant['username'],
                    'display_name': participant['display_name'],
                    'joined_at': participant['joined_at'],
                    'left_at': participant['left_at'],
                    'duration_minutes': duration_mins,
                    'participation_minutes': duration_mins,  # Frontend expects this field name
                    'participation_percentage': round(percentage, 1),  # Frontend expects this field name
                    'is_organizer': participant['is_organizer']
                })

            return result

    except Exception as e:
        logger.error(f"Error fetching participants for {event_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch participants")

@router.get("/events/scheduled")
@router.get("/mgmt/api/events/scheduled")
async def get_scheduled_events():
    """Get scheduled events from database."""
    try:
        pool = await get_db_pool()
        if pool is None:
            return []

        async with pool.acquire() as conn:
            events = await conn.fetch("""
                SELECT * FROM events
                WHERE event_status = 'scheduled' AND scheduled_start_time > NOW()
                ORDER BY scheduled_start_time ASC
            """)

            return [dict(event) for event in events]

    except Exception as e:
        logger.error(f"Error fetching scheduled events: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch scheduled events")

@router.post("/events/create")
@router.post("/mgmt/api/events/create")
async def create_event(request: EventCreationRequest):
    """Create a new event compatible with payroll system (no-auth version)."""
    try:
        pool = await get_db_pool()
        if pool is None:
            # Return mock success response when database is not available
            return {
                'event_id': f'evt_{random.randint(10000000, 99999999):08x}',
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
            event_data_for_discord = {
                "event_id": event_id,
                "event_name": request.event_name,
                "event_type": request.event_type,
                "organizer_name": request.organizer_name,
                "organizer_id": request.organizer_id,
                "location": request.location_notes,
                "notes": request.session_notes
            }
            bot_integration_result = await trigger_voice_tracking_on_event_start(event_data_for_discord)

            return {
                "success": True,
                "message": "Event created successfully",
                "event": dict(event_data),
                "discord_integration": bot_integration_result
            }

    except Exception as e:
        logger.error(f"Error creating event: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/events/{event_id}/close")
@router.post("/mgmt/api/events/{event_id}/close")
async def close_event(event_id: str):
    """Close an event and prepare it for payroll calculation."""
    event_id = validate_event_id(event_id)

    try:
        pool = await get_db_pool()
        if pool is None:
            return {
                "event_id": event_id,
                "status": "closed",
                "message": "Event closed successfully (mock mode)",
                "payroll_id": f"pr-{event_id}",
                "payroll_status": "open"
            }

        async with pool.acquire() as conn:
            async with conn.transaction():
                # Check if event exists and is open
                event = await conn.fetchrow("""
                    SELECT event_id, event_name, organizer_name, status, started_at
                    FROM events WHERE event_id = $1
                """, event_id)

                if not event:
                    raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

                if event['status'] != 'open':
                    raise HTTPException(status_code=400, detail=f"Event {event_id} is already {event['status']}")

                # Close the event
                await conn.execute("""
                    UPDATE events
                    SET status = 'closed', ended_at = NOW()
                    WHERE event_id = $1
                """, event_id)

                # Calculate totals from participation table
                totals = await conn.fetchrow("""
                    SELECT
                        COUNT(DISTINCT user_id) as total_participants,
                        COALESCE(SUM(duration_minutes), 0) as total_duration_minutes
                    FROM participation
                    WHERE event_id = $1
                """, event_id)

                # Update event totals
                await conn.execute("""
                    UPDATE events
                    SET total_participants = $1, total_duration_minutes = $2
                    WHERE event_id = $3
                """, totals['total_participants'], totals['total_duration_minutes'], event_id)

                # Create payroll record using bot schema
                payroll_id = f"pr-{event_id}"
                await conn.execute("""
                    INSERT INTO payrolls (
                        payroll_id, event_id, total_scu_collected, total_value_auec,
                        ore_prices_used, mining_yields, calculated_by_id, calculated_by_name
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (payroll_id) DO UPDATE SET
                        total_scu_collected = EXCLUDED.total_scu_collected,
                        total_value_auec = EXCLUDED.total_value_auec,
                        ore_prices_used = EXCLUDED.ore_prices_used,
                        mining_yields = EXCLUDED.mining_yields
                """, payroll_id, event_id,
                    0,  # total_scu_collected (will be updated when finalized)
                    0.0,  # total_value_auec (will be updated when finalized)
                    '{}',  # ore_prices_used (empty until finalized)
                    '{}',  # mining_yields (empty until finalized)
                    0,  # calculated_by_id (placeholder)
                    "Management Portal"  # calculated_by_name
                )

                logger.info(f"✅ Event {event_id} closed and payroll {payroll_id} created")

                # Stop voice tracking via bot API
                bot_integration_result = await trigger_voice_tracking_on_event_stop(event_id)

                # Get updated event data for response
                updated_event = await conn.fetchrow("""
                    SELECT total_participants, total_duration_minutes, ended_at
                    FROM events WHERE event_id = $1
                """, event_id)

                return {
                    "event_id": event_id,
                    "status": "closed",
                    "ended_at": updated_event['ended_at'].isoformat() if updated_event['ended_at'] else None,
                    "total_participants": updated_event['total_participants'] or 0,
                    "total_duration_minutes": updated_event['total_duration_minutes'] or 0,
                    "payroll_id": payroll_id,
                    "payroll_status": "created",
                    "message": f"Event {event_id} closed and payroll {payroll_id} created (ready for calculations)",
                    "discord_integration": bot_integration_result
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")