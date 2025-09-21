"""
Input validation utilities for Red Legion Web API.
Provides comprehensive validation for all user inputs to prevent security vulnerabilities.
"""

import re
from typing import Optional, List, Any, Union, Dict
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

# Validation patterns
DISCORD_ID_PATTERN = r'^\d{17,19}$'  # Discord snowflake IDs
EVENT_ID_PATTERN = r'^(sm|op|tr|web)-[a-zA-Z0-9]{6,20}$'  # Event ID format
USERNAME_PATTERN = r'^[a-zA-Z0-9_\-\.]{2,32}$'  # Discord usernames
ALPHA_NUMERIC_PATTERN = r'^[a-zA-Z0-9\s\-_\.]{1,100}$'  # General text
LOCATION_PATTERN = r'^[a-zA-Z0-9\s\-_\.\,\(\)]{1,200}$'  # Location text

def validate_discord_id(value: str, field_name: str = "Discord ID") -> str:
    """Validate Discord snowflake ID format."""
    if not value or not isinstance(value, str):
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}: must be a string")

    if not re.match(DISCORD_ID_PATTERN, value):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name}: must be 17-19 digits (Discord snowflake ID)"
        )
    return value

def validate_event_id(value: str) -> str:
    """Validate event ID format."""
    if not value or not isinstance(value, str):
        raise HTTPException(status_code=400, detail="Invalid event ID: must be a string")

    if not re.match(EVENT_ID_PATTERN, value):
        raise HTTPException(
            status_code=400,
            detail="Invalid event ID: must follow format 'sm-', 'op-', 'tr-', or 'web-' followed by alphanumeric characters"
        )
    return value

def validate_username(value: str) -> str:
    """Validate Discord username format."""
    if not value or not isinstance(value, str):
        raise HTTPException(status_code=400, detail="Invalid username: must be a string")

    if len(value) < 2 or len(value) > 32:
        raise HTTPException(status_code=400, detail="Invalid username: must be 2-32 characters")

    if not re.match(USERNAME_PATTERN, value):
        raise HTTPException(
            status_code=400,
            detail="Invalid username: can only contain letters, numbers, underscores, hyphens, and dots"
        )
    return value

def validate_text_input(value: str, field_name: str, min_length: int = 1, max_length: int = 100, allow_empty: bool = False) -> str:
    """Validate general text input."""
    if value is None or (not allow_empty and not value.strip()):
        if allow_empty:
            return ""
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}: cannot be empty")

    if not isinstance(value, str):
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}: must be a string")

    value = value.strip()

    if len(value) < min_length or len(value) > max_length:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name}: must be {min_length}-{max_length} characters"
        )

    # Basic XSS prevention - reject HTML-like content
    if '<' in value or '>' in value or 'script' in value.lower():
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}: HTML content not allowed")

    return value

def validate_positive_integer(value: Union[int, str], field_name: str, min_val: int = 0, max_val: int = None) -> int:
    """Validate positive integer."""
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}: must be a number")

    if int_value < min_val:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}: must be at least {min_val}")

    if max_val is not None and int_value > max_val:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}: must be at most {max_val}")

    return int_value

def validate_decimal_amount(value: Union[float, str], field_name: str, min_val: float = 0.0, max_val: float = None) -> float:
    """Validate decimal amounts (like SCU quantities)."""
    try:
        float_value = float(value)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}: must be a decimal number")

    if float_value < min_val:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}: must be at least {min_val}")

    if max_val is not None and float_value > max_val:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}: must be at most {max_val}")

    # Prevent extremely precise decimals that could cause issues
    if len(str(float_value).split('.')[-1]) > 6:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}: too many decimal places (max 6)")

    return float_value

# Pydantic models for complex validation

class EventCreateRequest(BaseModel):
    """Validation for event creation requests."""
    event_name: str = Field(..., min_length=3, max_length=100)
    event_type: str = Field(..., pattern=r'^(mining|salvage|combat|training)$')
    system_location: str = Field(..., min_length=2, max_length=50)
    planet_moon: Optional[str] = Field(None, max_length=50)
    location_notes: Optional[str] = Field(None, max_length=200)
    selected_channels: List[str] = Field(..., min_items=1, max_items=10)

    @field_validator('selected_channels')
    def validate_channel_ids(cls, v):
        for channel_id in v:
            validate_discord_id(channel_id, "Channel ID")
        return v

    @field_validator('event_name')
    def validate_event_name(cls, v):
        return validate_text_input(v, "Event name", min_length=3, max_length=100)

    @field_validator('system_location')
    def validate_system_location(cls, v):
        return validate_text_input(v, "System location", min_length=2, max_length=50)

class PayrollCalculateRequest(BaseModel):
    """Validation for payroll calculation requests."""
    ore_quantities: dict = Field(..., description="Ore type to SCU quantity mapping")
    donation_percentage: Optional[float] = Field(0, ge=0, le=100)
    custom_prices: Optional[dict] = Field({})
    donating_users: Optional[List[str]] = Field([], description="List of user IDs who are donating their shares")

    @field_validator('ore_quantities')
    def validate_ore_quantities(cls, v):
        if not isinstance(v, dict):
            raise ValueError("Ore quantities must be a dictionary")

        for ore_type, quantity in v.items():
            validate_text_input(ore_type, "Ore type", min_length=2, max_length=50)
            validate_decimal_amount(quantity, f"Quantity for {ore_type}", min_val=0.0, max_val=10000.0)

        return v

class ChannelAddRequest(BaseModel):
    """Validation for adding restricted channels."""
    channel_id: str
    channel_name: str = Field(..., min_length=1, max_length=100)

    @field_validator('channel_id')
    def validate_channel_id(cls, v):
        return validate_discord_id(v, "Channel ID")

    @field_validator('channel_name')
    def validate_channel_name(cls, v):
        return validate_text_input(v, "Channel name", min_length=1, max_length=100)

class EventCreationRequest(BaseModel):
    """Request model for creating events."""
    event_name: str = Field(..., min_length=3, max_length=100, description="Event name")
    organizer_name: str = Field(..., min_length=2, max_length=50, description="Organizer name")
    organizer_id: Optional[str] = Field(None, description="Discord organizer ID")
    guild_id: Optional[str] = Field("814699481912049704", pattern=r'^\d{17,19}$', description="Discord guild ID")
    event_type: str = Field("mining", pattern=r'^(mining|salvage|combat|training|cargo)$', description="Event type")
    location_notes: Optional[str] = Field(None, max_length=500, description="Location notes")
    session_notes: Optional[str] = Field(None, max_length=1000, description="Session notes")
    scheduled_start_time: Optional[datetime] = Field(None, description="Scheduled start time")
    auto_start_enabled: bool = Field(False, description="Auto-start enabled")
    tracked_channels: Optional[List[Dict[str, Any]]] = Field(None, description="Tracked Discord channels")
    primary_channel_id: Optional[int] = Field(None, ge=1, description="Primary Discord channel ID")

    @field_validator('tracked_channels')
    def validate_tracked_channels(cls, v):
        if v is not None:
            if len(v) > 20:
                raise ValueError("Too many tracked channels (max 20)")
            for channel in v:
                if not isinstance(channel, dict):
                    raise ValueError("Each tracked channel must be a dictionary")
                if 'id' not in channel or 'name' not in channel:
                    raise ValueError("Each tracked channel must have 'id' and 'name' fields")
        return v

# Security validation helpers

def sanitize_sql_identifier(identifier: str) -> str:
    """Sanitize SQL identifiers to prevent injection."""
    # Only allow alphanumeric characters and underscores
    if not re.match(r'^[a-zA-Z0-9_]+$', identifier):
        raise HTTPException(status_code=400, detail="Invalid identifier: only letters, numbers, and underscores allowed")

    # Prevent reserved SQL keywords
    sql_keywords = {'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'UNION', 'WHERE'}
    if identifier.upper() in sql_keywords:
        raise HTTPException(status_code=400, detail="Invalid identifier: SQL keywords not allowed")

    return identifier

def validate_pagination_params(page: int = 1, per_page: int = 20) -> tuple[int, int]:
    """Validate pagination parameters."""
    page = validate_positive_integer(page, "Page number", min_val=1, max_val=1000)
    per_page = validate_positive_integer(per_page, "Items per page", min_val=1, max_val=100)

    return page, per_page

def log_validation_attempt(endpoint: str, user_id: str, params: dict):
    """Log validation attempts for security monitoring."""
    logger.info(f"Validation attempt - Endpoint: {endpoint}, User: {user_id}, Params: {list(params.keys())}")

# Rate limiting helpers (to be expanded)
def check_rate_limit(user_id: str, endpoint: str) -> bool:
    """Basic rate limiting check."""
    # TODO: Implement proper rate limiting with Redis or similar
    return True