"""UEX Corporation price integration service."""

import httpx
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class UEXService:
    """Service for managing UEX Corporation price data."""

    def __init__(self, bot_api_url: str):
        self.bot_api_url = bot_api_url

    async def get_uex_prices(self) -> Dict[str, Any]:
        """Get current UEX ore prices from bot API with fallback and status info."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.bot_api_url}/api/uex-prices")
                if response.status_code == 200:
                    data = response.json()
                    logger.info("✅ UEX prices fetched from live API")
                    return {
                        "prices": data,
                        "source": "live_api",
                        "status": "connected",
                        "message": "Live UEX prices from bot API",
                        "last_updated": datetime.now().isoformat()
                    }
                else:
                    logger.warning(f"⚠️ UEX API returned {response.status_code}, using fallback")
                    return {
                        "prices": self.get_fallback_uex_prices(),
                        "source": "fallback",
                        "status": "api_error",
                        "message": f"UEX API error {response.status_code} - using fallback prices",
                        "last_updated": datetime.now().isoformat()
                    }
        except Exception as e:
            logger.error(f"❌ Error fetching UEX prices: {e}")
            return {
                "prices": self.get_fallback_uex_prices(),
                "source": "fallback",
                "status": "disconnected",
                "message": f"UEX API unavailable - using fallback prices",
                "error": str(e),
                "last_updated": datetime.now().isoformat()
            }

    def get_fallback_uex_prices(self) -> Dict[str, float]:
        """Fallback UEX prices when API is unavailable."""
        return {
            'QUANTAINIUM': 17500.0,
            'BEXALITE': 8500.0,
            'TARANITE': 7500.0,
            'LARANITE': 5200.0,
            'AGRICIUM': 4200.0,
            'HEPHAESTANITE': 3800.0,
            'HADANITE': 3500.0,
            'APHORITE': 3200.0,
            'DOLIVINE': 3000.0,
            'TITANIUM': 8.50,
            'DIAMOND': 7.40,
            'GOLD': 6.20,
            'COPPER': 4.80,
            'BERYL': 4.60,
            'TUNGSTEN': 4.20,
            'CORUNDUM': 3.50,
            'QUARTZ': 1.90,
            'ALUMINUM': 1.20,
            'INERT_MATERIALS': 0.01
        }

    def get_best_selling_locations(self) -> Dict[str, Dict[str, str]]:
        """Get best selling locations for different materials."""
        return {
            'QUANTAINIUM': {"location": "Orison", "system": "Stanton", "station": "Crusader"},
            'BEXALITE': {"location": "Area 18", "system": "Stanton", "station": "ArcCorp"},
            'TARANITE': {"location": "Orison", "system": "Stanton", "station": "Crusader"},
            'LARANITE': {"location": "Port Olisar", "system": "Stanton", "station": "Crusader"},
            'AGRICIUM': {"location": "Area 18", "system": "Stanton", "station": "ArcCorp"},
            'HEPHAESTANITE': {"location": "Lorville", "system": "Stanton", "station": "Hurston"},
            'HADANITE': {"location": "Area 18", "system": "Stanton", "station": "ArcCorp"},
            'APHORITE': {"location": "Orison", "system": "Stanton", "station": "Crusader"},
            'DOLIVINE': {"location": "Lorville", "system": "Stanton", "station": "Hurston"},
            'TITANIUM': {"location": "Area 18", "system": "Stanton", "station": "ArcCorp"},
            'DIAMOND': {"location": "Orison", "system": "Stanton", "station": "Crusader"},
            'GOLD': {"location": "Lorville", "system": "Stanton", "station": "Hurston"},
            'COPPER': {"location": "Area 18", "system": "Stanton", "station": "ArcCorp"},
            'BERYL': {"location": "New Babbage", "system": "Stanton", "station": "microTech"},
            'TUNGSTEN': {"location": "Lorville", "system": "Stanton", "station": "Hurston"},
            'CORUNDUM': {"location": "New Babbage", "system": "Stanton", "station": "microTech"},
            'QUARTZ': {"location": "Port Olisar", "system": "Stanton", "station": "Crusader"},
            'ALUMINUM': {"location": "New Babbage", "system": "Stanton", "station": "microTech"},
            'INERT_MATERIALS': {"location": "Any Location", "system": "Stanton", "station": "Any"}
        }

    async def get_material_prices(self, materials: str) -> Dict[str, Any]:
        """Get prices for specific materials with status information."""
        material_names = [name.strip().upper() for name in materials.split(',')]

        # Get UEX prices with status
        price_data = await self.get_uex_prices()
        uex_prices = price_data["prices"]
        best_locations = self.get_best_selling_locations()

        price_list = []
        for material in material_names:
            if material in uex_prices:
                best_loc = best_locations.get(material, {
                    "location": "Orison",
                    "system": "Stanton",
                    "station": "Crusader"
                })
                price_list.append({
                    "material_name": material,
                    "highest_price": uex_prices[material],
                    "best_location": best_loc["location"],
                    "best_system": best_loc["system"],
                    "best_station": best_loc["station"]
                })

        return {
            "materials": price_list,
            "source": price_data["source"],
            "status": price_data["status"],
            "message": price_data["message"],
            "last_updated": price_data["last_updated"]
        }

    async def get_location_prices(self, location_id: int, materials: str) -> Dict[str, Any]:
        """Get prices for materials at a specific location with status information."""
        material_names = [name.strip().upper() for name in materials.split(',') if name.strip()]

        # Get base UEX prices with status
        price_data = await self.get_uex_prices()
        base_prices = price_data["prices"]

        # Apply location modifiers using numeric IDs
        location_modifiers = {
            4: 1.0,     # Orison - Base prices
            1: 0.95,    # Area 18 - Slightly lower
            2: 0.90,    # Lorville - Lower prices
            3: 0.92,    # New Babbage - Moderate
            5: 0.85,    # Port Olisar - Lowest prices
        }

        modifier = location_modifiers.get(location_id, 1.0)

        # Location names for display
        location_names = {
            1: "Area 18 (ArcCorp)",
            2: "Lorville (Hurston)",
            3: "New Babbage (microTech)",
            4: "Orison (Crusader)",
            5: "Port Olisar (Crusader)"
        }

        location_name = location_names.get(location_id, f"Location {location_id}")

        price_list = []
        for material in material_names:
            if material in base_prices:
                adjusted_price = base_prices[material] * modifier
                price_list.append({
                    "material_name": material,
                    "price": round(adjusted_price, 2),
                    "location_id": location_id,
                    "location_name": location_name,
                    "base_price": base_prices[material],
                    "modifier": modifier
                })

        return {
            "location_prices": price_list,
            "source": price_data["source"],
            "status": price_data["status"],
            "message": price_data["message"],
            "last_updated": price_data["last_updated"]
        }

    async def get_trading_locations(self) -> List[Dict[str, Any]]:
        """Get list of trading locations."""
        return [
            {
                "id": 1,
                "name": "Area 18",
                "system": "Stanton",
                "planet": "ArcCorp",
                "type": "Trading Hub"
            },
            {
                "id": 2,
                "name": "Lorville",
                "system": "Stanton",
                "planet": "Hurston",
                "type": "Trading Hub"
            },
            {
                "id": 3,
                "name": "New Babbage",
                "system": "Stanton",
                "planet": "microTech",
                "type": "Trading Hub"
            },
            {
                "id": 4,
                "name": "Orison",
                "system": "Stanton",
                "planet": "Crusader",
                "type": "Trading Hub"
            },
            {
                "id": 5,
                "name": "Port Olisar",
                "system": "Stanton",
                "planet": "Crusader",
                "type": "Space Station"
            }
        ]

    async def refresh_uex_cache(self) -> Dict[str, Any]:
        """Force refresh of UEX price cache via bot API."""
        logger.info("🔄 Manual UEX cache refresh requested")
        try:
            # Try to trigger cache refresh via the bot API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{self.bot_api_url}/api/refresh-uex-cache")
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
                        "error": f"Bot API returned {response.status_code}",
                        "fallback_note": "Using fallback UEX prices",
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