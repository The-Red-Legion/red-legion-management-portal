#!/usr/bin/env python3
"""
Infrastructure Health Check
Tests all critical service connections to catch issues early.
"""

import asyncio
import asyncpg
import httpx
import os
import sys
from datetime import datetime
import pytest
from urllib.parse import unquote, urlparse, urlunparse, quote


class HealthCheckError(Exception):
    """Custom exception for health check failures."""
    pass


async def test_database_connection():
    """Test Cloud SQL database connectivity."""
    print("🗄️  Testing database connection...")
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise HealthCheckError("DATABASE_URL environment variable not set")
    
    # Handle URL-encoded passwords by properly decoding only the password part
    if '%' in database_url:
        # Parse URL components
        parsed = urlparse(database_url)
        if parsed.password and '%' in parsed.password:
            # Decode password and re-encode only necessary characters (not #)
            decoded_password = unquote(parsed.password)
            # Re-encode only @ and : which can interfere with URL parsing, but not #
            safe_password = quote(decoded_password, safe='#*;<>?!{}[]()=+&')
            netloc = f"{parsed.username}:{safe_password}@{parsed.hostname}:{parsed.port}"
            database_url = urlunparse((
                parsed.scheme, netloc, parsed.path, 
                parsed.params, parsed.query, parsed.fragment
            ))
    
    try:
        # Test connection to Cloud SQL
        conn = await asyncpg.connect(database_url)
        
        # Test basic query
        result = await conn.fetchval("SELECT 1")
        assert result == 1
        
        # Test critical tables exist
        tables_query = """
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('users', 'guild_memberships', 'mining_events', 'roles')
        """
        tables = await conn.fetch(tables_query)
        table_names = {row['table_name'] for row in tables}
        
        required_tables = {'users', 'guild_memberships', 'mining_events', 'roles'}
        missing_tables = required_tables - table_names
        
        if missing_tables:
            raise HealthCheckError(f"Missing required tables: {missing_tables}")
        
        # Test we can query guild_memberships (OAuth dependency)
        member_count = await conn.fetchval("SELECT COUNT(*) FROM guild_memberships WHERE is_active = TRUE")
        print(f"   ✅ Database connected - {member_count} active members")
        
        await conn.close()
        return True
        
    except Exception as e:
        raise HealthCheckError(f"Database connection failed: {e}")


async def test_discord_oauth():
    """Test Discord OAuth API connectivity."""
    print("🔐 Testing Discord OAuth API...")
    
    client_id = os.getenv('DISCORD_CLIENT_ID')
    client_secret = os.getenv('DISCORD_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        raise HealthCheckError("Discord OAuth credentials not configured")
    
    try:
        async with httpx.AsyncClient() as client:
            # Test Discord API accessibility
            response = await client.get("https://discord.com/api/v10/oauth2/applications/@me", 
                                      auth=(client_id, client_secret))
            
            if response.status_code != 200:
                raise HealthCheckError(f"Discord OAuth API returned {response.status_code}")
            
            app_data = response.json()
            print(f"   ✅ Discord OAuth API connected - App: {app_data.get('name', 'Unknown')}")
            return True
            
    except httpx.RequestError as e:
        raise HealthCheckError(f"Discord API connection failed: {e}")


async def test_bot_api():
    """Test Discord Bot API connectivity."""
    print("🤖 Testing Discord Bot API...")
    
    bot_api_url = os.getenv('BOT_API_URL', 'http://10.128.0.2:8001')
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test bot API is running
            response = await client.get(f"{bot_api_url}/")
            
            if response.status_code != 200:
                raise HealthCheckError(f"Bot API returned {response.status_code}")
            
            bot_data = response.json()
            
            # Test bot status
            status_response = await client.get(f"{bot_api_url}/bot/status")
            if status_response.status_code != 200:
                raise HealthCheckError(f"Bot status endpoint returned {status_response.status_code}")
            
            status_data = status_response.json()
            
            if not status_data.get('connected'):
                raise HealthCheckError("Discord bot is not connected")
            
            print(f"   ✅ Bot API connected - {status_data.get('guilds', 0)} guilds, {status_data.get('voice_connections', 0)} voice connections")
            return True
            
    except httpx.RequestError as e:
        raise HealthCheckError(f"Bot API connection failed: {e}")


async def test_uex_api():
    """Test UEX API connectivity for commodity prices."""
    print("💰 Testing UEX API...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test UEX API accessibility
            response = await client.get("https://uexcorp.space/api/2.0/commodities")
            
            if response.status_code != 200:
                raise HealthCheckError(f"UEX API returned {response.status_code}")
            
            commodities = response.json()
            
            if not isinstance(commodities, list) or len(commodities) == 0:
                raise HealthCheckError("UEX API returned invalid commodity data")
            
            print(f"   ✅ UEX API connected - {len(commodities)} commodities available")
            return True
            
    except httpx.RequestError as e:
        raise HealthCheckError(f"UEX API connection failed: {e}")


def test_environment_variables():
    """Test required environment variables are set."""
    print("🔧 Testing environment variables...")
    
    required_vars = [
        'DATABASE_URL',
        'DISCORD_CLIENT_ID', 
        'DISCORD_CLIENT_SECRET'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise HealthCheckError(f"Missing required environment variables: {missing_vars}")
    
    # Validate DATABASE_URL format
    database_url = os.getenv('DATABASE_URL')
    if not database_url.startswith('postgresql://'):
        raise HealthCheckError("DATABASE_URL must be a PostgreSQL connection string")
    
    # Check if using private or public IP for GCP connection
    database_url_decoded = unquote(database_url) if '%' in database_url else database_url
    if '10.92.0.3' not in database_url_decoded and '34.56.38.104' not in database_url_decoded:
        print("   ⚠️  WARNING: DATABASE_URL not using known GCP database IP")
    
    print("   ✅ Environment variables configured")
    return True


async def main():
    """Run all infrastructure health checks."""
    print("🚀 Starting Infrastructure Health Check")
    print("=" * 60)
    
    start_time = datetime.now()
    
    # Define all tests
    tests = [
        ("Environment Variables", test_environment_variables),
        ("Database Connection", test_database_connection),
        ("Discord OAuth API", test_discord_oauth),
        ("Discord Bot API", test_bot_api),
        ("UEX API", test_uex_api)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                await test_func()
            else:
                test_func()
            results.append((test_name, True, None))
        except HealthCheckError as e:
            print(f"   ❌ {test_name} failed: {e}")
            results.append((test_name, False, str(e)))
        except Exception as e:
            print(f"   ❌ {test_name} error: {e}")
            results.append((test_name, False, f"Unexpected error: {e}"))
        
        print()  # Add spacing between tests
    
    # Print summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("=" * 60)
    print("📊 Health Check Summary")
    print(f"⏱️  Duration: {duration:.2f}s")
    print()
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, error in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if error:
            print(f"         {error}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All infrastructure health checks passed!")
        sys.exit(0)
    else:
        print("💥 Some infrastructure health checks failed!")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Health check interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Health check failed with unexpected error: {e}")
        sys.exit(1)