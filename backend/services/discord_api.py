"""
Discord API client for fetching real guild channels and updating database.
"""

import asyncio
import httpx
import asyncpg
from typing import List, Dict, Optional, Any
import logging
import os
from google.cloud import secretmanager

logger = logging.getLogger(__name__)

class DiscordAPIClient:
    """Discord API client for fetching guild information."""
    
    def __init__(self, bot_token: str = None):
        self.bot_token = bot_token
        self.base_url = "https://discord.com/api/v10"
        self.session = None
        
        if not self.bot_token:
            self.bot_token = self._get_bot_token()
    
    def _get_bot_token(self) -> Optional[str]:
        """Get Discord bot token from environment or Google Cloud Secrets."""
        # Try environment variable first
        token = os.getenv('DISCORD_TOKEN')
        if token:
            return token
        
        # Try Google Cloud Secrets
        try:
            client = secretmanager.SecretManagerServiceClient()
            project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'rl-prod-471116')
            secret_path = f"projects/{project_id}/secrets/discord-token/versions/latest"
            response = client.access_secret_version(request={"name": secret_path})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.warning(f"Could not get Discord token from Secret Manager: {e}")
            return None
    
    async def __aenter__(self):
        """Async context manager entry."""
        if not self.bot_token:
            raise ValueError("Discord bot token not available")
        
        self.session = httpx.AsyncClient(
            headers={
                "Authorization": f"Bot {self.bot_token}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.aclose()
    
    async def get_guild_channels(self, guild_id: str) -> List[Dict[str, Any]]:
        """Fetch all channels for a Discord guild."""
        if not self.session:
            raise RuntimeError("Discord API client not initialized. Use async context manager.")
        
        try:
            url = f"{self.base_url}/guilds/{guild_id}/channels"
            logger.info(f"Fetching guild channels from Discord API: {url}")
            
            response = await self.session.get(url)
            response.raise_for_status()
            
            channels_data = response.json()
            logger.info(f"Retrieved {len(channels_data)} channels from Discord API")
            
            # Filter and format channel data
            formatted_channels = []
            for channel in channels_data:
                # Only process voice and text channels
                if channel.get('type') in [0, 2]:  # 0=text, 2=voice
                    formatted_channel = {
                        'channel_id': int(channel['id']),
                        'channel_name': channel['name'],
                        'channel_type': 'voice' if channel.get('type') == 2 else 'text',
                        'category_id': int(channel['parent_id']) if channel.get('parent_id') else None,
                        'position': channel.get('position', 0)
                    }
                    formatted_channels.append(formatted_channel)
            
            # Get category information for better organization
            categories = {ch['id']: ch['name'] for ch in channels_data if ch.get('type') == 4}  # 4=category
            
            # Add category names to channels
            for channel in formatted_channels:
                if channel['category_id'] and str(channel['category_id']) in categories:
                    channel['category_name'] = categories[str(channel['category_id'])]
                else:
                    channel['category_name'] = None
            
            return formatted_channels
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.error("Discord API authentication failed. Check bot token.")
                raise ValueError("Discord bot token invalid or expired")
            elif e.response.status_code == 403:
                logger.error("Discord bot lacks permission to view guild channels")
                raise ValueError("Discord bot missing permissions")
            elif e.response.status_code == 404:
                logger.error(f"Discord guild {guild_id} not found")
                raise ValueError(f"Guild {guild_id} not found or bot not in guild")
            else:
                logger.error(f"Discord API error: {e.response.status_code} - {e.response.text}")
                raise ValueError(f"Discord API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching Discord guild channels: {e}")
            raise

async def sync_discord_channels_to_db(guild_id: str, db_pool: asyncpg.Pool) -> Dict[str, Any]:
    """Sync Discord channels to database."""
    try:
        # Fetch channels from Discord API
        async with DiscordAPIClient() as discord_client:
            channels = await discord_client.get_guild_channels(guild_id)
        
        if not channels:
            return {
                "success": False,
                "message": "No channels retrieved from Discord API",
                "channels_synced": 0
            }
        
        # Update database with real channels
        async with db_pool.acquire() as conn:
            channels_synced = 0
            
            for channel in channels:
                # Only sync voice channels for now
                if channel['channel_type'] != 'voice':
                    continue
                
                try:
                    # Use the upsert function we created in the migration
                    await conn.execute("""
                        SELECT upsert_discord_channel($1, $2, $3, $4, $5, $6, $7)
                    """, 
                    int(guild_id),
                    channel['channel_id'],
                    channel['channel_name'],
                    channel['channel_type'],
                    channel.get('category_id'),
                    channel.get('category_name'),
                    channel.get('position')
                    )
                    channels_synced += 1
                except Exception as e:
                    logger.warning(f"Failed to sync channel {channel['channel_name']}: {e}")
                    continue
        
        # Clean up inactive channels (haven't been seen in 24 hours)
        try:
            async with db_pool.acquire() as conn:
                cleanup_count = await conn.fetchval("""
                    SELECT cleanup_inactive_channels($1, 24)
                """, int(guild_id))
                logger.info(f"Marked {cleanup_count} channels as inactive")
        except Exception as e:
            logger.warning(f"Failed to cleanup inactive channels: {e}")
        
        return {
            "success": True,
            "message": f"Successfully synced {channels_synced} voice channels",
            "channels_synced": channels_synced,
            "total_fetched": len([ch for ch in channels if ch['channel_type'] == 'voice'])
        }
        
    except Exception as e:
        logger.error(f"Error syncing Discord channels: {e}")
        return {
            "success": False,
            "message": f"Error syncing channels: {str(e)}",
            "channels_synced": 0
        }

async def get_discord_guild_info(guild_id: str) -> Optional[Dict[str, Any]]:
    """Get basic guild information from Discord API."""
    try:
        async with DiscordAPIClient() as discord_client:
            if not discord_client.session:
                return None
            
            url = f"{discord_client.base_url}/guilds/{guild_id}"
            response = await discord_client.session.get(url)
            response.raise_for_status()
            
            guild_data = response.json()
            return {
                'id': guild_data['id'],
                'name': guild_data['name'],
                'member_count': guild_data.get('approximate_member_count', 0),
                'icon': guild_data.get('icon'),
                'description': guild_data.get('description')
            }
    except Exception as e:
        logger.error(f"Error fetching Discord guild info: {e}")
        return None