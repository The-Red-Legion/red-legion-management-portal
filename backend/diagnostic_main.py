#!/usr/bin/env python3
"""
Diagnostic version of main.py for troubleshooting deployment issues.
This version provides extensive logging and graceful fallbacks.
"""

import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime, timezone
import traceback

print("=== Red Legion Backend Diagnostic Mode ===")
print(f"Python version: {sys.version}")
print(f"Working directory: {os.getcwd()}")
print(f"Python path: {sys.path[:3]}")

# Test imports step by step
import_results = {}
modules_to_test = [
    "fastapi", "uvicorn", "asyncpg", "httpx", "dotenv",
    "google.cloud.secretmanager", "pydantic", "reportlab",
    "validation", "session_manager", "services.discord_integration"
]

for module in modules_to_test:
    try:
        __import__(module)
        import_results[module] = "✓"
        print(f"✓ {module}")
    except Exception as e:
        import_results[module] = f"✗ {e}"
        print(f"✗ {module}: {e}")

# Test environment variables
env_vars = ["DATABASE_URL", "DISCORD_CLIENT_ID", "DISCORD_CLIENT_SECRET", "FRONTEND_URL"]
env_results = {}
for var in env_vars:
    value = os.getenv(var)
    if value:
        env_results[var] = "✓ SET" if "SECRET" not in var else "✓ SET (hidden)"
    else:
        env_results[var] = "✗ NOT SET"
    print(f"{env_results[var]} {var}")

# Create FastAPI app with minimal configuration
app = FastAPI(title="Red Legion Backend - Diagnostic Mode")

@app.get("/")
async def root():
    """Root endpoint with diagnostic info."""
    return {"message": "Red Legion Backend is running in diagnostic mode", "status": "ok"}

@app.get("/ping")
async def ping():
    """Simple ping endpoint."""
    return {
        "status": "ok",
        "message": "Backend responding in diagnostic mode",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/health")
async def health():
    """Health check with basic system info."""
    return {
        "status": "healthy",
        "mode": "diagnostic",
        "python_version": sys.version,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/debug")
async def debug():
    """Comprehensive debug information."""
    return {
        "import_results": import_results,
        "environment_variables": env_results,
        "python_info": {
            "version": sys.version,
            "executable": sys.executable,
            "path": sys.path[:5]
        },
        "system_info": {
            "working_directory": os.getcwd(),
            "environment_count": len(os.environ),
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

if __name__ == "__main__":
    try:
        print("Starting Red Legion Backend in diagnostic mode...")
        print("All imports successful - starting server")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to start server: {e}")
        traceback.print_exc()
        sys.exit(1)