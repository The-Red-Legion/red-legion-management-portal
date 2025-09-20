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
        self._cached_prices = None
        self._cache_timestamp = None

    async def initialize_cache(self):
        """Initialize the price cache with current data from Discord bot."""
        try:
            # Try to get initial prices to populate cache
            await self.get_uex_prices()
            logger.info("✅ UEX price cache initialized")
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize UEX price cache: {e}")

    async def get_uex_prices(self) -> Dict[str, Any]:
        """Get current UEX ore prices from bot API with fallback and status info."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.bot_api_url}/prices/current")
                if response.status_code == 200:
                    data = response.json()
                    logger.info("✅ UEX prices fetched from live API")

                    # Extract just the price values from the Discord bot API response
                    if "prices" in data and data.get("success"):
                        price_dict = {material: info["price"] for material, info in data["prices"].items()}

                        # Cache the successful response for future fallback use
                        self._cached_prices = price_dict
                        self._cache_timestamp = data.get("timestamp", datetime.now().isoformat())

                        return {
                            "prices": price_dict,
                            "source": "live_api",
                            "status": "connected",
                            "message": "Live UEX prices from bot API",
                            "last_updated": self._cache_timestamp
                        }
                    else:
                        logger.warning("⚠️ Invalid response format from bot API, using fallback")
                        return {
                            "prices": self.get_dynamic_fallback_prices(),
                            "source": "cached_fallback",
                            "status": "api_error",
                            "message": "Invalid bot API response format - using cached fallback prices",
                            "last_updated": self._cache_timestamp or datetime.now().isoformat()
                        }
                else:
                    logger.warning(f"⚠️ UEX API returned {response.status_code}, using fallback")
                    return {
                        "prices": self.get_dynamic_fallback_prices(),
                        "source": "cached_fallback",
                        "status": "api_error",
                        "message": f"UEX API error {response.status_code} - using cached fallback prices",
                        "last_updated": self._cache_timestamp or datetime.now().isoformat()
                    }
        except Exception as e:
            logger.error(f"❌ Error fetching UEX prices: {e}")
            return {
                "prices": self.get_dynamic_fallback_prices(),
                "source": "cached_fallback",
                "status": "disconnected",
                "message": f"UEX API unavailable - using cached fallback prices",
                "error": str(e),
                "last_updated": self._cache_timestamp or datetime.now().isoformat()
            }

    def get_fallback_uex_prices(self) -> Dict[str, float]:
        """Static fallback UEX prices when no cached data is available (last resort)."""
        return {
            'QUANTAINIUM': 22210.0,
            'BEXALITE': 6729.0,
            'BORASE': 3059.0,
            'TARANITE': 8718.0,
            'LARANITE': 2606.0,
            'AGRICIUM': 2349.0,
            'HEPHAESTANITE': 2334.0,
            'HADANITE': 3500.0,  # Not in live data, keeping previous
            'APHORITE': 3200.0,  # Not in live data, keeping previous
            'DOLIVINE': 3000.0,  # Not in live data, keeping previous
            'TITANIUM': 447.0,
            'DIAMOND': 7.40,     # Not in live data, keeping previous
            'GOLD': 5858.0,
            'COPPER': 342.0,
            'BERYL': 2559.0,
            'TUNGSTEN': 606.0,
            'CORUNDUM': 351.0,
            'QUARTZ': 368.0,
            'ALUMINUM': 293.0,
            'ASTATINE': 1637.0,  # New from live data
            'IRON': 376.0,      # New from live data
            'SILICON': 198.0,   # New from live data
            'TIN': 320.0,       # New from live data
            'STILERON': 29243.0, # New from live data
            'RICCITE': 20728.0,  # New from live data
            'GOLDEN MEDMON': 19766.0, # New from live data
            'HEXAPOLYMESH COATING': 1.0, # New from live data
            'INERT_MATERIALS': 0.01
        }

    def get_dynamic_fallback_prices(self) -> Dict[str, float]:
        """Get fallback prices - use cached prices if available, otherwise static fallback."""
        if self._cached_prices:
            cache_age_hours = 0
            if self._cache_timestamp:
                try:
                    cache_time = datetime.fromisoformat(self._cache_timestamp.replace('Z', '+00:00'))
                    cache_age = datetime.now() - cache_time.replace(tzinfo=None)
                    cache_age_hours = cache_age.total_seconds() / 3600
                except:
                    pass

            logger.info(f"🔄 Using cached UEX prices (cache age: {cache_age_hours:.1f} hours)")
            return self._cached_prices
        else:
            logger.warning("⚠️ No cached prices available, using static fallback")
            return self.get_fallback_uex_prices()

    def get_best_selling_locations(self) -> Dict[str, Dict[str, str]]:
        """Get best selling locations for different materials."""
        return {
            'QUANTAINIUM': {"location": "Orison", "system": "Stanton", "station": "Crusader"},
            'BEXALITE': {"location": "Area 18", "system": "Stanton", "station": "ArcCorp"},
            'BORASE': {"location": "Area 18", "system": "Stanton", "station": "ArcCorp"},
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
            else:
                # Add unknown materials with default price to prevent missing data
                logger.warning(f"Material '{material}' not found in UEX prices, using default")
                price_list.append({
                    "material_name": material,
                    "highest_price": 1000.0,  # Default fallback price
                    "best_location": "Orison",
                    "best_system": "Stanton",
                    "best_station": "Crusader"
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
            # Stanton System - Major Trading Hubs
            1: 0.95,    # Area 18 - Slightly lower
            2: 0.90,    # Lorville - Lower prices
            3: 0.92,    # New Babbage - Moderate
            4: 1.0,     # Orison - Base prices (best for most materials)
            # Stanton System - Space Stations & Outposts
            5: 0.85,    # Port Olisar - Lower prices
            6: 0.80,    # Grim HEX - Lower outpost prices
            7: 0.88,    # Everus Harbor - Refinery station
            8: 0.87,    # Baijini Point - Orbital station
            # Pyro System - Frontier pricing
            10: 0.75,   # Ruin Station - Lower frontier prices
            11: 0.70,   # Checkmate Co-op - Mining cooperative
            12: 0.65,   # Shady Glen - Frontier settlement
        }

        modifier = location_modifiers.get(location_id, 1.0)

        # Location names for display
        location_names = {
            1: "Area 18 (ArcCorp)",
            2: "Lorville (Hurston)",
            3: "New Babbage (microTech)",
            4: "Orison (Crusader)",
            5: "Port Olisar (Crusader)",
            6: "Grim HEX (Yela)",
            7: "Everus Harbor (Hurston)",
            8: "Baijini Point (microTech)",
            10: "Ruin Station (Pyro I)",
            11: "Checkmate Co-op (Pyro III)",
            12: "Shady Glen (Pyro IV)"
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
            else:
                # Add unknown materials with default price to prevent missing data
                logger.warning(f"Material '{material}' not found in location prices, using default")
                default_price = 1000.0
                adjusted_price = default_price * modifier
                price_list.append({
                    "material_name": material,
                    "price": round(adjusted_price, 2),
                    "location_id": location_id,
                    "location_name": location_name,
                    "base_price": default_price,
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
        """Get list of trading locations across Stanton and Pyro systems."""
        return [
            # Stanton System - Major Trading Hubs
            {
                "id": 1,
                "name": "Area 18",
                "system": "Stanton",
                "planet": "ArcCorp",
                "type": "Trading Hub",
                "description": "ArcCorp's primary commercial center"
            },
            {
                "id": 2,
                "name": "Lorville",
                "system": "Stanton",
                "planet": "Hurston",
                "type": "Trading Hub",
                "description": "Hurston Dynamics corporate headquarters"
            },
            {
                "id": 3,
                "name": "New Babbage",
                "system": "Stanton",
                "planet": "microTech",
                "type": "Trading Hub",
                "description": "microTech's technological hub"
            },
            {
                "id": 4,
                "name": "Orison",
                "system": "Stanton",
                "planet": "Crusader",
                "type": "Trading Hub",
                "description": "Floating city in Crusader's clouds"
            },
            # Stanton System - Space Stations
            {
                "id": 5,
                "name": "Port Olisar",
                "system": "Stanton",
                "planet": "Crusader",
                "type": "Space Station",
                "description": "Crusader orbital station"
            },
            {
                "id": 6,
                "name": "Grim HEX",
                "system": "Stanton",
                "planet": "Yela (Crusader)",
                "type": "Outpost",
                "description": "Asteroid mining station"
            },
            {
                "id": 7,
                "name": "Everus Harbor",
                "system": "Stanton",
                "planet": "Hurston",
                "type": "Space Station",
                "description": "Hurston orbital refinery"
            },
            {
                "id": 8,
                "name": "Baijini Point",
                "system": "Stanton",
                "planet": "microTech",
                "type": "Space Station",
                "description": "microTech orbital station"
            },
            # Pyro System - Major Locations
            {
                "id": 10,
                "name": "Ruin Station",
                "system": "Pyro",
                "planet": "Pyro I",
                "type": "Trading Hub",
                "description": "Primary trading hub in Pyro system"
            },
            {
                "id": 11,
                "name": "Checkmate Co-op",
                "system": "Pyro",
                "planet": "Pyro III",
                "type": "Outpost",
                "description": "Mining cooperative station"
            },
            {
                "id": 12,
                "name": "Shady Glen",
                "system": "Pyro",
                "planet": "Pyro IV",
                "type": "Outpost",
                "description": "Frontier settlement"
            }
        ]

    async def refresh_uex_cache(self) -> Dict[str, Any]:
        """Force refresh of UEX price cache via bot API."""
        logger.info("🔄 Manual UEX cache refresh requested")
        try:
            # Try to trigger cache refresh via the bot API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{self.bot_api_url}/prices/refresh")
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