"""UEX prices and trading location endpoints."""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
import logging
import os

from services.uex_service import UEXService

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize UEX service
BOT_API_URL = os.getenv("BOT_API_URL", "http://localhost:8001")
uex_service = UEXService(BOT_API_URL)

@router.get("/uex-prices")
@router.get("/mgmt/api/uex-prices")
async def get_uex_prices_endpoint():
    """Get current UEX ore prices."""
    try:
        prices = await uex_service.get_uex_prices()
        return prices
    except Exception as e:
        logger.error(f"Error fetching UEX prices: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch UEX prices")

@router.get("/trading-locations")
@router.get("/mgmt/api/trading-locations")
async def get_trading_locations_endpoint():
    """Get list of trading locations."""
    try:
        locations = await uex_service.get_trading_locations()
        return locations
    except Exception as e:
        logger.error(f"Error fetching trading locations: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch trading locations")

@router.get("/material-prices/{materials}")
@router.get("/mgmt/api/material-prices/{materials}")
async def get_material_prices_endpoint(materials: str):
    """Get best prices for specific materials."""
    try:
        if not materials:
            raise HTTPException(status_code=400, detail="Materials parameter is required")

        prices = await uex_service.get_material_prices(materials)
        return prices

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching material prices for '{materials}': {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch material prices")

@router.get("/location-prices/{location_id}")
@router.get("/mgmt/api/location-prices/{location_id}")
async def get_location_prices_endpoint(location_id: int, materials: str):
    """Get prices for materials at a specific location."""
    try:
        if not materials:
            raise HTTPException(status_code=400, detail="Materials query parameter is required")

        prices = await uex_service.get_location_prices(location_id, materials)
        return prices

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching location prices for location {location_id}, materials '{materials}': {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch location prices")