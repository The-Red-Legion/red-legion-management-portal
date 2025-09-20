"""Admin functionality endpoints."""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
from datetime import datetime

from database import get_db_pool
from validation import validate_event_id
from services.test_data_service import TestDataService
from services.uex_service import UEXService
from services.payroll_service import PayrollService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/admin/create-test-event/{event_type}")
@router.post("/mgmt/api/admin/create-test-event/{event_type}")
async def create_test_event_endpoint(event_type: str):
    """Create a test event with random participants and data."""
    try:
        pool = await get_db_pool()
        test_service = TestDataService(pool)

        result = await test_service.create_test_event(event_type)
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating test {event_type} event: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/admin/events/{event_id}")
@router.delete("/mgmt/api/admin/events/{event_id}")
async def delete_admin_event_endpoint(event_id: str):
    """Delete an event and all associated data (admin only)."""
    event_id = validate_event_id(event_id)

    try:
        pool = await get_db_pool()
        if pool is None:
            return {
                "success": True,
                "message": f"Event {event_id} deleted successfully (mock mode)",
                "event_id": event_id
            }

        async with pool.acquire() as conn:
            async with conn.transaction():
                # Check if event exists
                event = await conn.fetchrow("SELECT * FROM events WHERE event_id = $1", event_id)
                if not event:
                    raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

                # Delete participation records
                deleted_participants = await conn.execute(
                    "DELETE FROM participation WHERE event_id = $1", event_id
                )

                # Delete payroll sessions
                deleted_payroll = await conn.execute(
                    "DELETE FROM payroll_sessions WHERE event_id = $1", event_id
                )

                # Delete the event
                deleted_event = await conn.execute(
                    "DELETE FROM events WHERE event_id = $1", event_id
                )

                logger.info(f"🗑️ Admin deleted event {event_id} and all associated data")

                return {
                    "success": True,
                    "message": f"Event {event_id} and all associated data deleted successfully",
                    "event_id": event_id,
                    "deleted_participants": deleted_participants,
                    "deleted_payroll_sessions": deleted_payroll,
                    "deleted_events": deleted_event
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/admin/payroll-export/{event_id}")
@router.get("/mgmt/api/admin/payroll-export/{event_id}")
async def export_payroll_admin_endpoint(event_id: str):
    """Export payroll data in admin format."""
    event_id = validate_event_id(event_id)

    try:
        pool = await get_db_pool()
        if pool is None:
            return {
                "success": False,
                "error": "Database not available - admin export not possible in mock mode"
            }

        payroll_service = PayrollService(pool)
        result = await payroll_service.export_payroll(event_id)

        # Add admin-specific metadata
        if result.get("success"):
            result["admin_export"] = True
            result["exported_at"] = datetime.now().isoformat()
            result["exported_by"] = "admin"

        return result

    except Exception as e:
        logger.error(f"Error exporting admin payroll for {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Admin payroll export failed: {str(e)}")

@router.post("/admin/refresh-uex-cache")
@router.post("/mgmt/api/admin/refresh-uex-cache")
async def refresh_uex_cache_endpoint():
    """Force refresh of UEX price cache via bot API."""
    import os

    bot_api_url = os.getenv("BOT_API_URL", "http://localhost:8001")
    uex_service = UEXService(bot_api_url)

    result = await uex_service.refresh_uex_cache()
    return result