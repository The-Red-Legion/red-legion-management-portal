"""
Simple Red Legion Backend API
Minimal working version for frontend connectivity
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Red Legion Web API",
    description="Simple API for Red Legion payroll system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/redlegion')

async def get_db_pool():
    """Get database connection pool."""
    try:
        return await asyncpg.create_pool(DATABASE_URL)
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Red Legion Web API", "status": "running"}

@app.get("/events")
async def get_events():
    """Get all events - mock data for now."""
    # Return sample events for testing
    from datetime import datetime, timedelta
    
    sample_events = [
        {
            'event_id': 'evt_001',
            'event_name': 'Sunday Mining Operation',
            'event_type': 'mining',
            'started_at': (datetime.now() - timedelta(hours=2)).isoformat(),
            'ended_at': None,  # Currently active
            'organizer_id': 'user_123',
            'organizer_name': 'CommanderRed',
            'created_at': (datetime.now() - timedelta(hours=3)).isoformat()
        },
        {
            'event_id': 'evt_002', 
            'event_name': 'Salvage Operation Alpha',
            'event_type': 'salvage',
            'started_at': (datetime.now() - timedelta(days=1)).isoformat(),
            'ended_at': (datetime.now() - timedelta(days=1, hours=-3)).isoformat(),
            'organizer_id': 'user_456',
            'organizer_name': 'SalvageKing',
            'created_at': (datetime.now() - timedelta(days=1, hours=1)).isoformat()
        },
        {
            'event_id': 'evt_003',
            'event_name': 'Weekly Mining Expedition',
            'event_type': 'mining', 
            'started_at': (datetime.now() - timedelta(days=7)).isoformat(),
            'ended_at': (datetime.now() - timedelta(days=7, hours=-4)).isoformat(),
            'organizer_id': 'user_789',
            'organizer_name': 'MinerMax',
            'created_at': (datetime.now() - timedelta(days=7, hours=1)).isoformat()
        }
    ]
    
    return sample_events

@app.get("/events/{event_id}/participants")
async def get_event_participants(event_id: str):
    """Get participants for a specific event - mock data."""
    from datetime import datetime, timedelta
    
    # Return sample participants for testing
    sample_participants = [
        {
            'user_id': 'user_001',
            'username': 'RedLegionMiner',
            'participation_minutes': 120,
            'joined_at': (datetime.now() - timedelta(hours=2)).isoformat(),
            'left_at': None  # Still active
        },
        {
            'user_id': 'user_002',
            'username': 'SpaceTrucker',
            'participation_minutes': 90,
            'joined_at': (datetime.now() - timedelta(hours=1, minutes=30)).isoformat(),
            'left_at': None
        },
        {
            'user_id': 'user_003',
            'username': 'SalvageExpert',
            'participation_minutes': 60,
            'joined_at': (datetime.now() - timedelta(hours=1)).isoformat(),
            'left_at': (datetime.now() - timedelta(minutes=30)).isoformat()
        }
    ]
    
    return sample_participants

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)