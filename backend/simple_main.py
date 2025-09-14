#!/usr/bin/env python3
"""
Minimal fallback version of main.py for debugging deployment issues.
This version starts with minimal dependencies and provides basic endpoints.
"""

import os
import sys
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime, timezone

# Set up minimal environment
app = FastAPI(title="Red Legion Backend - Minimal Mode")

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Red Legion Backend is running in minimal mode", "status": "ok"}

@app.get("/ping")
async def ping():
    """Simple ping endpoint."""
    return {
        "status": "ok",
        "message": "Backend responding",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "minimal"
    }

@app.get("/health")
async def health():
    """Basic health check."""
    return {
        "status": "healthy",
        "mode": "minimal",
        "python_version": sys.version,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/debug")
async def debug():
    """Debug endpoint to check environment."""
    return {
        "python_version": sys.version,
        "python_path": sys.path[:3],  # First 3 entries
        "environment_vars": {
            key: "***" if "SECRET" in key or "PASSWORD" in key else value
            for key, value in os.environ.items()
            if key.startswith(('DATABASE_', 'DISCORD_', 'FRONTEND_', 'BOT_'))
        },
        "working_directory": os.getcwd(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

if __name__ == "__main__":
    print("Starting Red Legion Backend in minimal mode...")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")

    # Start server
    uvicorn.run(app, host="0.0.0.0", port=8000)