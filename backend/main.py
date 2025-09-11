"""
Red Legion Web Payroll - FastAPI Backend
Simple web interface for Discord bot payroll system
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import os
import asyncpg
import httpx
from dotenv import load_dotenv
from typing import List, Dict, Optional
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Red Legion Web Payroll",
    description="Web interface for Discord bot payroll system",
    version="1.0.0"
)

# CORS configuration for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")

# Database connection pool
db_pool = None

async def get_db_pool():
    """Get database connection pool."""
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(DATABASE_URL)
    return db_pool

@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup."""
    await get_db_pool()
    logger.info("Database connection pool initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown."""
    if db_pool:
        await db_pool.close()
        logger.info("Database connection pool closed")

# Routes

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Red Legion Web Payroll API", "version": "1.0.0"}

@app.get("/auth/login")
async def discord_login():
    """Redirect to Discord OAuth."""
    discord_auth_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={DISCORD_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify"
    )
    return RedirectResponse(discord_auth_url)

@app.get("/auth/callback")
async def discord_callback(code: str):
    """Handle Discord OAuth callback."""
    try:
        # Exchange code for access token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://discord.com/api/oauth2/token",
                data={
                    "client_id": DISCORD_CLIENT_ID,
                    "client_secret": DISCORD_CLIENT_SECRET,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": DISCORD_REDIRECT_URI,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            token_data = token_response.json()
            
            # Get user info
            user_response = await client.get(
                "https://discord.com/api/users/@me",
                headers={"Authorization": f"Bearer {token_data['access_token']}"}
            )
            user_data = user_response.json()
            
        # Redirect to frontend with user data
        return RedirectResponse(f"http://localhost:5173/?user={user_data['username']}&id={user_data['id']}")
        
    except Exception as e:
        logger.error(f"Discord auth error: {e}")
        raise HTTPException(status_code=400, detail="Authentication failed")

@app.get("/events")
async def get_events():
    """Get all mining events from database."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Query events table (similar to your bot's database structure)
            events = await conn.fetch("""
                SELECT event_id, event_name, organizer_name, started_at, 
                       total_duration_minutes, participant_count
                FROM mining_events 
                WHERE event_id LIKE 'sm-%'
                ORDER BY started_at DESC 
                LIMIT 50
            """)
            
            return [dict(event) for event in events]
            
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error")

@app.get("/events/{event_id}/participants")
async def get_event_participants(event_id: str):
    """Get participants for a specific event."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            participants = await conn.fetch("""
                SELECT user_id, username, participation_minutes, 
                       participation_percentage
                FROM event_participants 
                WHERE event_id = $1
                ORDER BY participation_minutes DESC
            """, event_id)
            
            return [dict(participant) for participant in participants]
            
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error")

@app.post("/payroll/{event_id}/calculate")
async def calculate_payroll(event_id: str, ore_quantities: Dict[str, float], custom_prices: Optional[Dict[str, float]] = None):
    """Calculate payroll for an event (simplified version of bot logic)."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Get event data
            event = await conn.fetchrow("""
                SELECT * FROM mining_events WHERE event_id = $1
            """, event_id)
            
            if not event:
                raise HTTPException(status_code=404, detail="Event not found")
            
            # Get participants
            participants = await conn.fetch("""
                SELECT user_id, username, participation_minutes, 
                       participation_percentage
                FROM event_participants 
                WHERE event_id = $1
            """, event_id)
            
            # Get UEX prices (simplified)
            uex_prices = await get_uex_prices()
            
            # Use custom prices if provided
            prices = custom_prices or uex_prices
            
            # Calculate total value
            total_value = sum(quantity * prices.get(ore.upper(), 0) for ore, quantity in ore_quantities.items())
            
            # Calculate individual payouts
            payouts = []
            for participant in participants:
                base_payout = total_value * (participant['participation_percentage'] / 100)
                payouts.append({
                    'user_id': participant['user_id'],
                    'username': participant['username'],
                    'participation_minutes': participant['participation_minutes'],
                    'participation_percentage': participant['participation_percentage'],
                    'base_payout_auec': base_payout,
                    'final_payout_auec': base_payout
                })
            
            return {
                'event_id': event_id,
                'total_value_auec': total_value,
                'payouts': payouts,
                'ore_quantities': ore_quantities,
                'prices_used': prices
            }
            
    except Exception as e:
        logger.error(f"Payroll calculation error: {e}")
        raise HTTPException(status_code=500, detail="Calculation error")

async def get_uex_prices() -> Dict[str, float]:
    """Get UEX ore prices (simplified)."""
    # This is a simplified version - you'd implement the full UEX API logic here
    default_prices = {
        'QUANTAINIUM': 21869.0,
        'GOLD': 5832.0,
        'COPPER': 344.0,
        'RICCITE': 20585.0,
        'CORUNDUM': 359.0,
    }
    return default_prices

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)