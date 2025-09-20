"""Discord integration endpoints."""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
import logging
import os
import httpx

from database import get_db_pool

logger = logging.getLogger(__name__)
router = APIRouter()

# Bot API configuration
BOT_API_URL = os.getenv("BOT_API_URL", "http://localhost:8001")

@router.get("/discord/channels")
@router.get("/mgmt/api/discord/channels")
async def get_discord_channels_endpoint(guild_id: str = "814699481912049704"):
    """Get Discord voice channels with database fallbacks."""
    try:
        # Try to get channels from Discord bot API first
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{BOT_API_URL}/discord/channels/{guild_id}")
            if response.status_code == 200:
                discord_data = response.json()
                logger.info(f"✅ Successfully fetched {len(discord_data.get('channels', []))} Discord channels from bot API")
                return discord_data

        # If Discord API fails, try database fallback
        pool = await get_db_pool()
        if pool:
            async with pool.acquire() as conn:
                channels = await conn.fetch("""
                    SELECT channel_id, channel_name, is_primary
                    FROM mining_channels
                    WHERE guild_id = $1 AND is_active = true
                    ORDER BY is_primary DESC, channel_name ASC
                """, int(guild_id))

                if channels:
                    channel_list = []
                    for ch in channels:
                        channel_list.append({
                            "id": str(ch['channel_id']),
                            "name": ch['channel_name'],
                            "type": "voice",
                            "is_primary": ch['is_primary']
                        })

                    logger.info(f"📊 Using database fallback: {len(channel_list)} channels")
                    return {
                        "channels": channel_list,
                        "source": "database",
                        "message": "Discord bot unavailable - using database channels"
                    }

        # No Discord connection and no database - return empty with clear error
        logger.error("❌ No Discord bot connection and no database channels available")
        return {
            "channels": [],
            "source": "unavailable",
            "message": "Discord bot is offline and no database backup available"
        }

    except Exception as e:
        logger.error(f"Error fetching Discord channels: {e}")
        return {
            "channels": [],
            "source": "error",
            "message": f"Error fetching channels: {str(e)}"
        }

@router.post("/discord/channels/sync")
@router.post("/mgmt/api/discord/channels/sync")
async def sync_discord_channels_endpoint():
    """Sync Discord channels from bot API to database."""
    try:
        # Get channels from Discord bot API
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{BOT_API_URL}/discord/channels/814699481912049704")
            if response.status_code != 200:
                raise HTTPException(status_code=503, detail="Discord bot API unavailable")

            discord_data = response.json()
            channels = discord_data.get('channels', [])

            if not channels:
                return {
                    "success": False,
                    "message": "No channels received from Discord API",
                    "synced_count": 0
                }

        # Sync to database
        pool = await get_db_pool()
        if not pool:
            return {
                "success": False,
                "message": "Database not available - cannot sync channels",
                "synced_count": 0
            }

        async with pool.acquire() as conn:
            async with conn.transaction():
                synced_count = 0

                for channel in channels:
                    if channel.get('type') == 'voice':  # Only sync voice channels
                        await conn.execute("""
                            INSERT INTO mining_channels (
                                guild_id, channel_id, channel_name, is_active, is_primary
                            ) VALUES ($1, $2, $3, true, false)
                            ON CONFLICT (guild_id, channel_id) DO UPDATE SET
                                channel_name = EXCLUDED.channel_name,
                                is_active = true
                        """, 814699481912049704, int(channel['id']), channel['name'])
                        synced_count += 1

                logger.info(f"🔄 Synced {synced_count} Discord channels to database")

                return {
                    "success": True,
                    "message": f"Successfully synced {synced_count} Discord channels",
                    "synced_count": synced_count,
                    "total_channels": len(channels)
                }

    except Exception as e:
        logger.error(f"Error syncing Discord channels: {e}")
        raise HTTPException(status_code=500, detail=f"Channel sync failed: {str(e)}")