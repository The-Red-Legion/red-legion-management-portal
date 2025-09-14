#!/usr/bin/env python3
"""
Gradual import testing to identify problematic dependency.
This version systematically adds imports from main.py one by one.
"""

print("=== Gradual Import Testing ===")

# Basic imports first (these worked in ultra_simple_main.py)
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime, timezone
import os
import sys

print("✓ Basic imports successful")

# Test each import group systematically
import_groups = [
    # Group 1: Standard library and basic FastAPI
    ("Basic FastAPI", ["from fastapi.middleware.cors import CORSMiddleware",
                      "from fastapi import HTTPException, Depends, Request",
                      "from fastapi.responses import RedirectResponse, Response"]),

    # Group 2: Pydantic
    ("Pydantic", ["from pydantic import BaseModel, Field, field_validator"]),

    # Group 3: External libraries
    ("External libs", ["import asyncpg", "import httpx", "from dotenv import load_dotenv"]),

    # Group 4: Google Cloud
    ("Google Cloud", ["from google.cloud import secretmanager"]),

    # Group 5: Data processing
    ("Data processing", ["from typing import List, Dict, Optional, Any",
                        "import logging", "import random", "import string",
                        "import secrets", "import json", "import io"]),

    # Group 6: ReportLab
    ("ReportLab", ["from reportlab.lib.pagesizes import letter, A4",
                  "from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image",
                  "from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle",
                  "from reportlab.lib.units import inch",
                  "from reportlab.lib import colors"]),

    # Group 7: Local services
    ("Local services", ["from services.discord_integration import trigger_voice_tracking_on_event_start, trigger_voice_tracking_on_event_stop, get_discord_bot_status",
                       "from services.discord_api import sync_discord_channels_to_db"]),

    # Group 8: Local modules
    ("Local modules", ["from validation import validate_discord_id, validate_event_id, validate_text_input, validate_positive_integer, validate_decimal_amount, EventCreateRequest, PayrollCalculateRequest, ChannelAddRequest, validate_pagination_params, log_validation_attempt",
                      "from session_manager import SessionManager, SessionData, SecurityConfig, get_session_manager"])
]

successful_imports = []
failed_imports = []

for group_name, imports in import_groups:
    print(f"\n--- Testing {group_name} ---")
    for import_statement in imports:
        try:
            exec(import_statement)
            print(f"✓ {import_statement}")
            successful_imports.append(import_statement)
        except Exception as e:
            print(f"✗ {import_statement}")
            print(f"  Error: {e}")
            failed_imports.append((import_statement, str(e)))

# Load environment if dotenv worked
try:
    load_dotenv()
    print("✓ Environment loaded")
except:
    print("✗ Environment loading failed")

# Create FastAPI app
app = FastAPI(title="Gradual Import Test Backend")

@app.get("/")
async def root():
    return {"message": "Gradual import test backend", "status": "ok"}

@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "Backend responding"}

@app.get("/health")
async def health():
    return {"status": "healthy", "mode": "gradual_test"}

@app.get("/import-status")
async def import_status():
    return {
        "successful_imports": len(successful_imports),
        "failed_imports": len(failed_imports),
        "successful": successful_imports,
        "failed": failed_imports,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

if __name__ == "__main__":
    print(f"\n=== Import Summary ===")
    print(f"Successful: {len(successful_imports)}")
    print(f"Failed: {len(failed_imports)}")

    if failed_imports:
        print(f"\n--- FAILED IMPORTS ---")
        for stmt, error in failed_imports:
            print(f"✗ {stmt}")
            print(f"  {error}")

    print(f"\nStarting gradual test backend...")
    uvicorn.run(app, host="0.0.0.0", port=8000)