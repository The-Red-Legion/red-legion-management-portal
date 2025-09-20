"""
Discord Bot Integration Service

Handles communication between the Red Legion web server and Discord bot
for automatic voice activity tracking when events are created.
"""

import asyncio
import aiohttp
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DiscordBotConfig:
    """Configuration for Discord bot integration."""
    BOT_API_BASE_URL = os.getenv("BOT_API_URL", "http://10.128.0.2:8001")
    REQUEST_TIMEOUT = 30
    DEFAULT_GUILD_ID = "814699481912049704"  # Red Legion Discord server ID

class StartEventRequest(BaseModel):
    """Request model for starting Discord bot event tracking."""
    event_id: str
    event_name: str
    event_type: str = "mining"
    organizer_name: str
    organizer_id: Optional[str] = None
    guild_id: str = DiscordBotConfig.DEFAULT_GUILD_ID
    location: Optional[str] = None
    notes: Optional[str] = None

class DiscordBotClient:
    """Client for communicating with Discord bot web API."""
    
    def __init__(self):
        self.base_url = DiscordBotConfig.BOT_API_BASE_URL
        self.timeout = DiscordBotConfig.REQUEST_TIMEOUT
    
    async def check_bot_status(self) -> Dict[str, Any]:
        """Check if Discord bot is online and ready."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/bot/status",
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"🤖 Discord bot status: {'✅ Connected' if data.get('connected') else '❌ Disconnected'}")
                        return data
                    else:
                        logger.error(f"❌ Discord bot status check failed: HTTP {response.status}")
                        return {"connected": False, "error": f"HTTP {response.status}"}
        except asyncio.TimeoutError:
            logger.error("⏰ Discord bot status check timed out")
            return {"connected": False, "error": "Timeout"}
        except Exception as e:
            logger.error(f"❌ Discord bot status check error: {e}")
            return {"connected": False, "error": str(e)}
    
    async def start_event_tracking(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Start Discord voice tracking for an event."""
        try:
            # Prepare request data
            request_data = StartEventRequest(
                event_id=event_data["event_id"],
                event_name=event_data.get("event_name", "Red Legion Event"),
                event_type=event_data.get("event_type", "mining"),
                organizer_name=event_data.get("organizer_name", "Web Interface"),
                organizer_id=str(event_data.get("organizer_id", "web-interface")),
                location=event_data.get("location"),
                notes=event_data.get("notes")
            )
            
            logger.info(f"🎯 Starting Discord voice tracking for event: {request_data.event_id}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/events/start",
                    json=request_data.dict(),
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    response_data = await response.json()
                    
                    if response.status == 200:
                        logger.info(f"✅ Successfully started Discord voice tracking for event {request_data.event_id}")
                        return {
                            "success": True,
                            "message": "Discord voice tracking started",
                            "data": response_data
                        }
                    else:
                        error_msg = response_data.get("detail", f"HTTP {response.status}")
                        logger.error(f"❌ Failed to start Discord voice tracking: {error_msg}")
                        return {
                            "success": False,
                            "error": error_msg,
                            "status_code": response.status
                        }
                        
        except asyncio.TimeoutError:
            logger.error(f"⏰ Discord voice tracking start timed out for event {event_data['event_id']}")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"❌ Error starting Discord voice tracking for event {event_data['event_id']}: {e}")
            return {"success": False, "error": str(e)}
    
    async def stop_event_tracking(self, event_id: str) -> Dict[str, Any]:
        """Stop Discord voice tracking for an event."""
        try:
            logger.info(f"🛑 Stopping Discord voice tracking for event: {event_id}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/events/{event_id}/stop",
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    response_data = await response.json()
                    
                    if response.status == 200:
                        logger.info(f"✅ Successfully stopped Discord voice tracking for event {event_id}")
                        return {
                            "success": True,
                            "message": "Discord voice tracking stopped",
                            "data": response_data
                        }
                    else:
                        error_msg = response_data.get("detail", f"HTTP {response.status}")
                        logger.error(f"❌ Failed to stop Discord voice tracking: {error_msg}")
                        return {
                            "success": False,
                            "error": error_msg,
                            "status_code": response.status
                        }
                        
        except asyncio.TimeoutError:
            logger.error(f"⏰ Discord voice tracking stop timed out for event {event_id}")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"❌ Error stopping Discord voice tracking for event {event_id}: {e}")
            return {"success": False, "error": str(e)}

# Global client instance
_discord_client: Optional[DiscordBotClient] = None

def get_discord_client() -> DiscordBotClient:
    """Get the global Discord bot client instance."""
    global _discord_client
    if _discord_client is None:
        _discord_client = DiscordBotClient()
    return _discord_client

async def trigger_voice_tracking_on_event_start(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Trigger Discord voice tracking when a new event is started.
    
    Args:
        event_data: Dictionary containing event information
        
    Returns:
        Dict containing success status and details
    """
    client = get_discord_client()
    
    # Check if bot is available first
    bot_status = await client.check_bot_status()
    if not bot_status.get("connected", False):
        logger.warning(f"⚠️ Discord bot not available for event {event_data.get('event_id', 'unknown')} - continuing without voice tracking")
        return {
            "success": False,
            "error": "Discord bot not connected",
            "bot_status": bot_status
        }
    
    # Start voice tracking
    result = await client.start_event_tracking(event_data)
    return result

async def trigger_voice_tracking_on_event_stop(event_id: str) -> Dict[str, Any]:
    """
    Stop Discord voice tracking when an event is stopped.
    
    Args:
        event_id: The ID of the event to stop tracking
        
    Returns:
        Dict containing success status and details
    """
    client = get_discord_client()
    
    # Check if bot is available first
    bot_status = await client.check_bot_status()
    if not bot_status.get("connected", False):
        logger.warning(f"⚠️ Discord bot not available for stopping event {event_id} - event may still be tracked")
        return {
            "success": False,
            "error": "Discord bot not connected",
            "bot_status": bot_status
        }
    
    # Stop voice tracking
    result = await client.stop_event_tracking(event_id)
    return result

async def get_discord_bot_status() -> Dict[str, Any]:
    """Get current Discord bot connection status."""
    client = get_discord_client()
    return await client.check_bot_status()