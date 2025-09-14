#!/usr/bin/env python3
"""
Testing main.py initialization code step by step.
Since imports work, the issue must be in the configuration/initialization.
"""

print("=== Initialization Testing ===")

# All imports (we know these work from gradual_main.py)
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response, JSONResponse
from pydantic import BaseModel, Field, field_validator
import os
import sys
import asyncpg
import httpx
from dotenv import load_dotenv
from google.cloud import secretmanager
from typing import List, Dict, Optional, Any
import logging
import random
import string
import secrets
from datetime import datetime, timedelta, timezone
import io
import json
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from services.discord_integration import (
    trigger_voice_tracking_on_event_start,
    trigger_voice_tracking_on_event_stop,
    get_discord_bot_status
)
from services.discord_api import sync_discord_channels_to_db
from validation import (
    validate_discord_id, validate_event_id, validate_text_input,
    validate_positive_integer, validate_decimal_amount,
    EventCreateRequest, PayrollCalculateRequest, ChannelAddRequest,
    validate_pagination_params, log_validation_attempt
)
from session_manager import SessionManager, SessionData, SecurityConfig, get_session_manager
import uvicorn

print("✓ All imports successful")

initialization_results = []

# Step 1: Load environment
try:
    load_dotenv()
    print("✓ Environment variables loaded")
    initialization_results.append("✓ load_dotenv()")
except Exception as e:
    print(f"✗ Environment loading failed: {e}")
    initialization_results.append(f"✗ load_dotenv(): {e}")

# Step 2: Configure logging
try:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    print("✓ Logging configured")
    initialization_results.append("✓ logging configuration")
except Exception as e:
    print(f"✗ Logging configuration failed: {e}")
    initialization_results.append(f"✗ logging configuration: {e}")
    logger = None

# Step 3: Secret manager configuration helper
try:
    def get_config_value(env_var: str, secret_id: str = None) -> Optional[str]:
        """Get configuration value from environment or GCP Secret Manager."""
        value = os.getenv(env_var)
        if value:
            return value

        if secret_id:
            try:
                client = secretmanager.SecretManagerServiceClient()
                project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "rl-prod-471116")
                secret_name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
                response = client.access_secret_version(request={"name": secret_name})
                return response.payload.data.decode("UTF-8")
            except Exception as e:
                if logger:
                    logger.warning(f"Secret Manager access failed for {secret_id}: {e}")

        return None

    print("✓ Secret manager helper function created")
    initialization_results.append("✓ get_config_value function")
except Exception as e:
    print(f"✗ Secret manager helper failed: {e}")
    initialization_results.append(f"✗ get_config_value function: {e}")

# Step 4: Load configuration values
config_results = {}
try:
    DATABASE_URL = get_config_value("DATABASE_URL_LOCAL") or get_config_value("DATABASE_URL", "database-connection-string")
    config_results["DATABASE_URL"] = "✓" if DATABASE_URL else "✗"

    DISCORD_CLIENT_ID = get_config_value("DISCORD_CLIENT_ID", "discord-client-id")
    config_results["DISCORD_CLIENT_ID"] = "✓" if DISCORD_CLIENT_ID else "✗"

    DISCORD_CLIENT_SECRET = get_config_value("DISCORD_CLIENT_SECRET", "discord-client-secret")
    config_results["DISCORD_CLIENT_SECRET"] = "✓" if DISCORD_CLIENT_SECRET else "✗"

    DISCORD_REDIRECT_URI = get_config_value("DISCORD_REDIRECT_URI")
    config_results["DISCORD_REDIRECT_URI"] = "✓" if DISCORD_REDIRECT_URI else "✗"

    FRONTEND_URL = get_config_value("FRONTEND_URL") or "http://localhost:5173"
    config_results["FRONTEND_URL"] = FRONTEND_URL

    print("✓ Configuration values loaded")
    initialization_results.append("✓ Configuration loading")
except Exception as e:
    print(f"✗ Configuration loading failed: {e}")
    initialization_results.append(f"✗ Configuration loading: {e}")

# Step 5: Session manager initialization
try:
    session_manager_instance = get_session_manager()
    print("✓ Session manager initialized")
    initialization_results.append("✓ Session manager")
except Exception as e:
    print(f"✗ Session manager initialization failed: {e}")
    initialization_results.append(f"✗ Session manager: {e}")

# Step 6: Create FastAPI app
try:
    app = FastAPI(
        title="Red Legion Web Payroll",
        description="Simple web interface for Discord bot payroll system",
        version="2.0.0"
    )
    print("✓ FastAPI app created")
    initialization_results.append("✓ FastAPI app")
except Exception as e:
    print(f"✗ FastAPI app creation failed: {e}")
    initialization_results.append(f"✗ FastAPI app: {e}")

# Step 7: CORS middleware
try:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[FRONTEND_URL, "http://localhost:5173"] if 'FRONTEND_URL' in locals() else ["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    print("✓ CORS middleware added")
    initialization_results.append("✓ CORS middleware")
except Exception as e:
    print(f"✗ CORS middleware failed: {e}")
    initialization_results.append(f"✗ CORS middleware: {e}")

# Basic endpoints
@app.get("/")
async def root():
    return {"message": "Red Legion Backend - Initialization Test", "status": "ok"}

@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "Backend responding"}

@app.get("/health")
async def health():
    return {"status": "healthy", "mode": "init_test"}

@app.get("/init-status")
async def init_status():
    return {
        "initialization_results": initialization_results,
        "config_results": config_results if 'config_results' in locals() else {},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

if __name__ == "__main__":
    print(f"\n=== Initialization Summary ===")
    for result in initialization_results:
        print(result)

    print(f"\nStarting initialization test backend...")
    uvicorn.run(app, host="0.0.0.0", port=8000)