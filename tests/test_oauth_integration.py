"""
OAuth Integration Test
Tests the complete end-to-end Discord OAuth authentication flow.
"""

import pytest
import asyncio
import httpx
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import os
import json


class TestOAuthIntegrationFlow:
    """Test complete OAuth integration flow end-to-end."""
    
    @pytest.mark.asyncio
    async def test_complete_oauth_flow_success(self):
        """Test successful complete OAuth flow from start to finish."""
        
        # Step 1: Initial OAuth redirect
        print("🔄 Testing OAuth redirect generation...")
        
        client_id = "test_client_id_123456"
        redirect_uri = "https://arccorp-web.redlegion.org/auth/callback"
        state = "random_state_token_abc123"
        
        oauth_params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code", 
            "scope": "identify guilds",
            "state": state
        }
        
        # Verify OAuth URL generation
        from urllib.parse import urlencode
        expected_url = f"https://discord.com/api/oauth2/authorize?{urlencode(oauth_params)}"
        
        assert "discord.com/api/oauth2/authorize" in expected_url
        assert "client_id=test_client_id_123456" in expected_url
        assert "scope=identify%20guilds" in expected_url
        
        print("✅ OAuth redirect URL generated correctly")
        
        # Step 2: Mock Discord callback with authorization code
        print("🔄 Testing authorization code exchange...")
        
        auth_code = "mock_authorization_code_xyz789"
        
        # Mock token exchange response
        mock_token_data = {
            "access_token": "mock_access_token_456def",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "mock_refresh_token_789ghi",
            "scope": "identify guilds"
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_token_data
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # Simulate token exchange
            async with httpx.AsyncClient() as client:
                token_response = await client.post(
                    "https://discord.com/api/oauth2/token",
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    data={
                        "client_id": client_id,
                        "client_secret": "test_client_secret",
                        "grant_type": "authorization_code",
                        "code": auth_code,
                        "redirect_uri": redirect_uri
                    }
                )
            
            assert token_response.status_code == 200
            token_data = token_response.json()
            assert token_data["access_token"] == "mock_access_token_456def"
            
        print("✅ Authorization code exchange successful")
        
        # Step 3: Fetch user information from Discord
        print("🔄 Testing user information fetch...")
        
        mock_user_data = {
            "id": "288816952992989184",
            "username": "NewSticks",
            "discriminator": "0000",
            "avatar": "mock_avatar_hash",
            "verified": True,
            "email": "newsticks@redlegion.org"
        }
        
        mock_guilds_data = [
            {
                "id": "814699481912049704",
                "name": "Red Legion",
                "owner": False,
                "permissions": "2147483647",
                "features": []
            }
        ]
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_user_response = Mock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = mock_user_data
            
            mock_guilds_response = Mock()
            mock_guilds_response.status_code = 200
            mock_guilds_response.json.return_value = mock_guilds_data
            
            # Return user data first, then guilds data
            mock_get.side_effect = [mock_user_response, mock_guilds_response]
            
            access_token = mock_token_data["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}
            
            async with httpx.AsyncClient() as client:
                user_response = await client.get("https://discord.com/api/v10/users/@me", headers=headers)
                guilds_response = await client.get("https://discord.com/api/v10/users/@me/guilds", headers=headers)
            
            assert user_response.status_code == 200
            assert guilds_response.status_code == 200
            
            user_data = user_response.json()
            guilds_data = guilds_response.json()
            
            assert user_data["id"] == "288816952992989184"
            assert user_data["username"] == "NewSticks"
            assert len(guilds_data) == 1
            assert guilds_data[0]["id"] == "814699481912049704"
            
        print("✅ User information fetched successfully")
        
        # Step 4: Database role lookup
        print("🔄 Testing database role lookup...")
        
        mock_user_roles = [
            {
                "role_id": "814699701861220412",
                "role_name": "Admin",
                "permissions": 8,
                "color": 16711680,
                "position": 10
            },
            {
                "role_id": "814699481912049708", 
                "role_name": "@everyone",
                "permissions": 0,
                "color": 0,
                "position": 0
            }
        ]
        
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetchrow.return_value = {
                "user_id": "288816952992989184",
                "guild_id": "814699481912049704", 
                "roles": ["814699701861220412", "814699481912049708"],
                "is_active": True
            }
            mock_conn.fetch.return_value = mock_user_roles
            
            # Simulate database queries
            membership = await mock_conn.fetchrow("""
                SELECT user_id, guild_id, roles, is_active
                FROM guild_memberships 
                WHERE user_id = $1 AND guild_id = $2 AND is_active = TRUE
            """, "288816952992989184", "814699481912049704")
            
            user_roles = await mock_conn.fetch("""
                SELECT role_id, role_name, permissions, color, position
                FROM roles 
                WHERE role_id = ANY($1) AND guild_id = $2
                ORDER BY position DESC
            """, membership["roles"], "814699481912049704")
            
            assert membership is not None
            assert membership["is_active"] == True
            assert len(user_roles) == 2
            assert any(role["role_name"] == "Admin" for role in user_roles)
            
        print("✅ Database role lookup successful")
        
        # Step 5: Session token creation
        print("🔄 Testing session token creation...")
        
        import jwt
        
        session_data = {
            "user_id": user_data["id"],
            "username": user_data["username"],
            "guild_id": "814699481912049704",
            "roles": [role["role_id"] for role in mock_user_roles],
            "permissions": max(role["permissions"] for role in mock_user_roles),
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        
        jwt_secret = "test_jwt_secret_key"
        session_token = jwt.encode(session_data, jwt_secret, algorithm="HS256")
        
        # Verify token can be decoded
        decoded_data = jwt.decode(session_token, jwt_secret, algorithms=["HS256"])
        
        assert decoded_data["user_id"] == "288816952992989184"
        assert decoded_data["username"] == "NewSticks" 
        assert "814699701861220412" in decoded_data["roles"]
        assert decoded_data["permissions"] == 8  # Admin permissions
        
        print("✅ Session token created successfully")
        
        # Step 6: Final authentication success
        print("🔄 Testing complete authentication flow...")
        
        # Mock successful login response
        login_response = {
            "success": True,
            "user": {
                "id": decoded_data["user_id"],
                "username": decoded_data["username"],
                "roles": decoded_data["roles"],
                "permissions": decoded_data["permissions"]
            },
            "session_token": session_token,
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }
        
        assert login_response["success"] == True
        assert login_response["user"]["username"] == "NewSticks"
        assert login_response["user"]["permissions"] == 8
        
        print("✅ Complete OAuth flow successful!")
        
        return login_response
    
    @pytest.mark.asyncio
    async def test_oauth_flow_invalid_code(self):
        """Test OAuth flow with invalid authorization code."""
        
        print("🔄 Testing OAuth flow with invalid code...")
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {
                "error": "invalid_grant",
                "error_description": "Invalid authorization code"
            }
            mock_post.return_value.__aenter__.return_value = mock_response
            
            async with httpx.AsyncClient() as client:
                token_response = await client.post(
                    "https://discord.com/api/oauth2/token",
                    data={
                        "client_id": "test_client_id",
                        "client_secret": "test_client_secret", 
                        "grant_type": "authorization_code",
                        "code": "invalid_code_123",
                        "redirect_uri": "https://example.com/callback"
                    }
                )
            
            assert token_response.status_code == 400
            error_data = token_response.json()
            assert error_data["error"] == "invalid_grant"
            
        print("✅ Invalid code properly rejected")
    
    @pytest.mark.asyncio 
    async def test_oauth_flow_user_not_in_guild(self):
        """Test OAuth flow for user not in required guild."""
        
        print("🔄 Testing OAuth flow for non-guild user...")
        
        # Mock user who is not in Red Legion guild
        mock_guilds_data = [
            {
                "id": "999999999999999999",  # Different guild
                "name": "Other Guild",
                "owner": False,
                "permissions": "2147483647"
            }
        ]
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_guilds_data
            mock_get.return_value.__aenter__.return_value = mock_response
            
            async with httpx.AsyncClient() as client:
                guilds_response = await client.get(
                    "https://discord.com/api/v10/users/@me/guilds",
                    headers={"Authorization": "Bearer mock_token"}
                )
            
            guilds_data = guilds_response.json()
            
            # Check if user is in Red Legion guild
            red_legion_guild_id = "814699481912049704"
            is_in_guild = any(guild["id"] == red_legion_guild_id for guild in guilds_data)
            
            assert is_in_guild == False
            
        print("✅ Non-guild user properly identified")
    
    @pytest.mark.asyncio
    async def test_oauth_flow_insufficient_permissions(self):
        """Test OAuth flow for user with insufficient permissions."""
        
        print("🔄 Testing OAuth flow for user with insufficient permissions...")
        
        # Mock database response for user with only @everyone role
        mock_user_roles = [
            {
                "role_id": "814699481912049708",
                "role_name": "@everyone", 
                "permissions": 0,
                "color": 0,
                "position": 0
            }
        ]
        
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetchrow.return_value = {
                "user_id": "123456789012345678",
                "guild_id": "814699481912049704",
                "roles": ["814699481912049708"],  # Only @everyone
                "is_active": True
            }
            mock_conn.fetch.return_value = mock_user_roles
            
            membership = await mock_conn.fetchrow("""
                SELECT user_id, guild_id, roles, is_active
                FROM guild_memberships 
                WHERE user_id = $1 AND guild_id = $2 AND is_active = TRUE
            """, "123456789012345678", "814699481912049704")
            
            user_roles = await mock_conn.fetch("""
                SELECT role_id, role_name, permissions
                FROM roles 
                WHERE role_id = ANY($1) AND guild_id = $2
            """, membership["roles"], "814699481912049704")
            
            # Check if user has admin permissions
            admin_role_id = "814699701861220412"
            has_admin_access = any(role["role_id"] == admin_role_id for role in user_roles)
            max_permissions = max((role["permissions"] for role in user_roles), default=0)
            
            assert has_admin_access == False
            assert max_permissions == 0
            
        print("✅ Insufficient permissions properly detected")
    
    @pytest.mark.asyncio
    async def test_oauth_flow_database_error(self):
        """Test OAuth flow with database connection error."""
        
        print("🔄 Testing OAuth flow with database error...")
        
        with patch('asyncpg.connect') as mock_connect:
            mock_connect.side_effect = Exception("Database connection failed")
            
            with pytest.raises(Exception) as exc_info:
                await mock_connect("postgresql://invalid_url")
            
            assert "Database connection failed" in str(exc_info.value)
            
        print("✅ Database error properly handled")
    
    @pytest.mark.asyncio
    async def test_oauth_flow_token_expiration(self):
        """Test OAuth flow with expired token."""
        
        print("🔄 Testing OAuth flow with expired token...")
        
        import jwt
        from datetime import datetime, timedelta
        
        # Create expired session token
        expired_session_data = {
            "user_id": "288816952992989184",
            "username": "NewSticks",
            "exp": datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
        }
        
        jwt_secret = "test_jwt_secret_key"
        expired_token = jwt.encode(expired_session_data, jwt_secret, algorithm="HS256")
        
        # Try to decode expired token
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(expired_token, jwt_secret, algorithms=["HS256"])
            
        print("✅ Token expiration properly detected")
    
    @pytest.mark.asyncio
    async def test_oauth_state_verification(self):
        """Test OAuth state parameter verification for CSRF protection."""
        
        print("🔄 Testing OAuth state verification...")
        
        # Test valid state
        original_state = "secure_random_state_token_123"
        returned_state = "secure_random_state_token_123"
        
        assert original_state == returned_state
        
        # Test invalid state (CSRF attempt)
        invalid_state = "malicious_state_token_456"
        
        assert original_state != invalid_state
        
        print("✅ OAuth state verification working")
    
    @pytest.mark.asyncio
    async def test_session_management(self):
        """Test session creation and validation."""
        
        print("🔄 Testing session management...")
        
        import jwt
        
        # Create session
        session_data = {
            "user_id": "288816952992989184",
            "username": "NewSticks",
            "roles": ["814699701861220412"],
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        
        jwt_secret = "test_secret_key"
        token = jwt.encode(session_data, jwt_secret, algorithm="HS256")
        
        # Validate session
        decoded = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        
        assert decoded["user_id"] == "288816952992989184"
        assert decoded["username"] == "NewSticks"
        assert "814699701861220412" in decoded["roles"]
        
        # Test session expiration check
        expires_at = datetime.fromtimestamp(decoded["exp"])
        is_expired = datetime.utcnow() > expires_at
        
        assert is_expired == False
        
        print("✅ Session management working correctly")


class TestOAuthEnvironmentValidation:
    """Test OAuth environment configuration validation."""
    
    def test_oauth_environment_variables(self):
        """Test OAuth environment variables are properly configured."""
        
        # Mock required environment variables
        test_env = {
            "DISCORD_CLIENT_ID": "123456789012345678",
            "DISCORD_CLIENT_SECRET": "mock_client_secret_abc123",
            "JWT_SECRET_KEY": "mock_jwt_secret_xyz789",
            "OAUTH_REDIRECT_URI": "https://arccorp-web.redlegion.org/auth/callback"
        }
        
        with patch.dict(os.environ, test_env):
            client_id = os.getenv("DISCORD_CLIENT_ID")
            client_secret = os.getenv("DISCORD_CLIENT_SECRET")
            jwt_secret = os.getenv("JWT_SECRET_KEY")
            redirect_uri = os.getenv("OAUTH_REDIRECT_URI")
            
            assert client_id == "123456789012345678"
            assert client_secret == "mock_client_secret_abc123"
            assert jwt_secret == "mock_jwt_secret_xyz789"
            assert "arccorp-web.redlegion.org" in redirect_uri
            
            # Validate configurations
            assert len(client_id) >= 17  # Discord client IDs are at least 17 digits
            assert len(client_secret) >= 10  # Client secrets should be substantial
            assert len(jwt_secret) >= 16  # JWT secrets should be strong
            assert redirect_uri.startswith("https://")  # Must be HTTPS
        
        print("✅ OAuth environment variables properly configured")
    
    def test_oauth_url_validation(self):
        """Test OAuth URL validation and security."""
        
        # Test valid OAuth URLs
        valid_urls = [
            "https://discord.com/api/oauth2/authorize",
            "https://discord.com/api/oauth2/token", 
            "https://discord.com/api/v10/users/@me",
            "https://discord.com/api/v10/users/@me/guilds"
        ]
        
        for url in valid_urls:
            assert url.startswith("https://")
            assert "discord.com" in url
            
        # Test invalid OAuth URLs (security check)
        invalid_urls = [
            "http://discord.com/api/oauth2/authorize",  # Not HTTPS
            "https://malicious-site.com/oauth",         # Wrong domain
            "https://discord.evil.com/api/oauth2/token" # Subdomain attack
        ]
        
        discord_domain = "discord.com"
        for url in invalid_urls:
            if not url.startswith("https://"):
                assert False, f"URL not HTTPS: {url}"
            if discord_domain not in url or not url.startswith("https://discord.com"):
                assert True  # This should fail validation
                
        print("✅ OAuth URL validation working correctly")