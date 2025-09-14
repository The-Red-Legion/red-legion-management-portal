#!/usr/bin/env python3
"""
Startup validation script for Red Legion backend.
Checks all dependencies and configurations before starting the main application.
"""

import sys
import os
import importlib
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_python_version():
    """Check Python version compatibility."""
    required_version = (3, 8)
    current_version = sys.version_info[:2]

    if current_version < required_version:
        logger.error(f"Python {required_version[0]}.{required_version[1]}+ required, got {current_version[0]}.{current_version[1]}")
        return False

    logger.info(f"Python version: {sys.version}")
    return True

def check_required_packages():
    """Check if all required packages are available."""
    required_packages = [
        'fastapi',
        'pydantic',
        'asyncpg',
        'httpx',
        'google.cloud.secretmanager',
        'reportlab',
        'dotenv'
    ]

    missing_packages = []

    for package in required_packages:
        try:
            importlib.import_module(package)
            logger.info(f"✓ {package}")
        except ImportError as e:
            logger.error(f"✗ {package}: {e}")
            missing_packages.append(package)

    if missing_packages:
        logger.error(f"Missing packages: {', '.join(missing_packages)}")
        return False

    logger.info("All required packages available")
    return True

def check_environment_variables():
    """Check critical environment variables."""
    critical_vars = [
        'DATABASE_URL',
        'DISCORD_CLIENT_ID',
        'DISCORD_CLIENT_SECRET',
        'DISCORD_REDIRECT_URI',
        'FRONTEND_URL'
    ]

    missing_vars = []

    for var in critical_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
            logger.warning(f"✗ {var}: Not set")
        else:
            logger.info(f"✓ {var}: {'*' * min(len(value), 8)}")  # Mask values

    if missing_vars:
        logger.warning(f"Missing environment variables: {', '.join(missing_vars)}")
        logger.info("Application will attempt to use Secret Manager or defaults")

    return True  # Don't fail on missing env vars since we have fallbacks

async def test_basic_imports():
    """Test importing main application modules."""
    try:
        # Test validation module
        from validation import validate_discord_id
        logger.info("✓ validation module")

        # Test session manager
        from session_manager import SessionManager, SecurityConfig
        logger.info("✓ session_manager module")

        # Test basic FastAPI import
        from fastapi import FastAPI
        logger.info("✓ FastAPI import")

        return True

    except Exception as e:
        logger.error(f"Import test failed: {e}")
        return False

async def test_async_compatibility():
    """Test async/await functionality."""
    try:
        await asyncio.sleep(0.001)  # Minimal async test
        logger.info("✓ Async functionality working")
        return True
    except Exception as e:
        logger.error(f"Async test failed: {e}")
        return False

async def main():
    """Run all startup checks."""
    logger.info("Starting Red Legion backend validation...")

    checks = [
        ("Python Version", check_python_version()),
        ("Required Packages", check_required_packages()),
        ("Environment Variables", check_environment_variables()),
        ("Module Imports", await test_basic_imports()),
        ("Async Compatibility", await test_async_compatibility())
    ]

    passed = 0
    failed = 0

    for check_name, result in checks:
        if result:
            logger.info(f"✓ {check_name}: PASS")
            passed += 1
        else:
            logger.error(f"✗ {check_name}: FAIL")
            failed += 1

    logger.info(f"Validation complete: {passed} passed, {failed} failed")

    if failed > 0:
        logger.error("Startup validation failed - application may not work correctly")
        return False
    else:
        logger.info("All checks passed - ready to start application")
        return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)