"""
Red Legion Web Payroll - FastAPI Backend (No Authentication)
Simple web interface for Discord bot payroll system without OAuth

Updated: 2025-09-20 - Refactored with service architecture and routers
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from dotenv import load_dotenv

# Import routers
from routers.health import router as health_router
from routers.events import router as events_router
from routers.payroll import router as payroll_router
from routers.admin import router as admin_router
from routers.discord import router as discord_router
from routers.trading import router as trading_router

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
BOT_API_URL = os.getenv("BOT_API_URL", "http://10.128.0.2:8001")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

logger.info(f"Configuration loaded - DATABASE_URL: {'✓' if DATABASE_URL else '✗'}")
logger.info(f"Configuration loaded - BOT_API_URL: {BOT_API_URL}")
logger.info(f"Configuration loaded - FRONTEND_URL: {FRONTEND_URL}")

# CORS configuration
cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "https://dev.redlegion.gg",
    "http://dev.redlegion.gg"
]

# FastAPI app
app = FastAPI(
    title="Red Legion Management Portal API",
    description="Backend API for Red Legion web management portal",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(health_router, tags=["Health"])
app.include_router(events_router, tags=["Events"])
app.include_router(payroll_router, tags=["Payroll"])
app.include_router(admin_router, tags=["Admin"])
app.include_router(discord_router, tags=["Discord"])
app.include_router(trading_router, tags=["Trading"])

@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("Red Legion Management Portal API started (no authentication)")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Red Legion Management Portal API shutting down")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)