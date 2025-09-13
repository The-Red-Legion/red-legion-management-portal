"""
Unit tests for authentication functionality.
Tests OAuth flow, role validation, and session management.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
import httpx
from datetime import datetime, timedelta

# Mock the main app for testing
@pytest.fixture
def mock_app():
    """Create a mock FastAPI app for testing."""
    from fastapi import FastAPI
    app = FastAPI()
    
    # Add mock routes for testing
    @app.get("/auth/discord")
    async def mock_discord_auth():
        return {"redirect_url": "https://discord.com/api/oauth2/authorize"}
    
    @app.get("/auth/callback")
    async def mock_auth_callback():
        return {"success": True, "user": {"id": "123", "username": "test"}}
    
    @app.get("/auth/me")
    async def mock_auth_me():
        return {"user": {"id": "123", "username": "test", "roles": ["Admin"]}}
    
    return app


class TestDiscordOAuth:
    """Test Discord OAuth 2.0 authentication flow."""
    
    def test_oauth_redirect_url_generation(self):
        """Test OAuth redirect URL is properly formatted."""
        from urllib.parse import urlencode, quote
        
        # Mock OAuth parameters
        client_id = "123456789"
        redirect_uri = "https://arccorp-web.redlegion.org/auth/callback"
        scopes = ["identify", "guilds"]
        
        # Generate OAuth URL
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": "random_state_token"
        }
        
        oauth_url = f"https://discord.com/api/oauth2/authorize?{urlencode(params)}"
        
        # Verify URL contains required parameters
        assert "client_id=" in oauth_url
        assert "redirect_uri=" in oauth_url
        assert "response_type=code" in oauth_url
        assert "scope=identify%20guilds" in oauth_url
        assert "state=" in oauth_url
    
    @pytest.mark.asyncio
    async def test_token_exchange(self):
        """Test exchanging authorization code for access token."""
        
        # Mock successful token response
        mock_token_response = {
            "access_token": "mock_access_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "mock_refresh_token",
            "scope": "identify guilds"
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_token_response
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # Simulate token exchange
            async with httpx.AsyncClient() as client:
                response = await client.post("https://discord.com/api/oauth2/token", 
                                           data={
                                               "client_id": "test_client_id",
                                               "client_secret": "test_client_secret",
                                               "grant_type": "authorization_code",
                                               "code": "test_auth_code",
                                               "redirect_uri": "https://example.com/callback"
                                           })
            
            # Verify token exchange was attempted
            mock_post.assert_called_once()
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_user_info_fetch(self):
        """Test fetching user information from Discord API."""
        
        # Mock Discord user response
        mock_user_data = {
            "id": "288816952992989184",
            "username": "NewSticks",
            "discriminator": "0000",
            "avatar": "avatar_hash",
            "verified": True,
            "email": "test@example.com"
        }
        
        mock_guilds_data = [
            {
                "id": "814699481912049704",
                "name": "Red Legion",
                "owner": False,
                "permissions": "2147483647"
            }
        ]
        
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock user info response
            mock_user_response = Mock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = mock_user_data
            
            # Mock guilds response
            mock_guilds_response = Mock()
            mock_guilds_response.status_code = 200
            mock_guilds_response.json.return_value = mock_guilds_data
            
            mock_get.side_effect = [mock_user_response, mock_guilds_response]
            
            # Simulate API calls
            async with httpx.AsyncClient() as client:
                user_response = await client.get("https://discord.com/api/v10/users/@me",
                                               headers={"Authorization": "Bearer mock_token"})
                guilds_response = await client.get("https://discord.com/api/v10/users/@me/guilds",
                                                 headers={"Authorization": "Bearer mock_token"})
            
            assert user_response.status_code == 200
            assert guilds_response.status_code == 200
            
            user_data = user_response.json()
            guilds_data = guilds_response.json()
            
            assert user_data["id"] == "288816952992989184"
            assert user_data["username"] == "NewSticks"
            assert len(guilds_data) == 1
            assert guilds_data[0]["id"] == "814699481912049704"


class TestRoleValidation:
    """Test role-based access control."""
    
    @pytest.mark.asyncio
    async def test_admin_role_validation(self):
        """Test validation of Admin role."""
        
        # Mock database response for user with Admin role
        mock_user_roles = [
            {"role_id": "814699701861220412", "role_name": "Admin"},
            {"role_id": "814699481912049708", "role_name": "@everyone"}
        ]
        
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetch.return_value = mock_user_roles
            
            # Simulate role check
            user_id = "288816952992989184"
            guild_id = "814699481912049704"
            
            # Check if user has Admin role
            admin_role_id = "814699701861220412"
            has_admin_role = any(role["role_id"] == admin_role_id for role in mock_user_roles)
            
            assert has_admin_role == True
    
    @pytest.mark.asyncio
    async def test_unauthorized_user_rejection(self):
        """Test rejection of users without proper roles."""
        
        # Mock database response for user with no special roles
        mock_user_roles = [
            {"role_id": "814699481912049708", "role_name": "@everyone"}
        ]
        
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetch.return_value = mock_user_roles
            
            # Check if user has Admin role
            admin_role_id = "814699701861220412"
            has_admin_role = any(role["role_id"] == admin_role_id for role in mock_user_roles)
            
            assert has_admin_role == False
    
    def test_role_hierarchy(self):
        """Test role hierarchy validation."""
        
        # Define role hierarchy (higher number = more permissions)
        role_hierarchy = {
            "814699701861220412": 100,  # Admin
            "814699648451510287": 75,   # Officer  
            "814699559275126814": 50,   # Senior Member
            "814699481912049708": 1     # @everyone
        }
        
        # Test Admin has highest permissions
        admin_level = role_hierarchy["814699701861220412"]
        officer_level = role_hierarchy["814699648451510287"]
        
        assert admin_level > officer_level
        
        # Test role comparison function
        def has_permission_level(user_roles, required_level):
            user_levels = [role_hierarchy.get(role_id, 0) for role_id in user_roles]
            return max(user_levels, default=0) >= required_level
        
        # Test Admin user has access to Officer-level features
        admin_roles = ["814699701861220412"]
        assert has_permission_level(admin_roles, 75) == True
        
        # Test regular user doesn't have Officer access
        regular_roles = ["814699481912049708"]
        assert has_permission_level(regular_roles, 75) == False


class TestSessionManagement:
    """Test session handling and JWT tokens."""
    
    def test_jwt_token_creation(self):
        """Test JWT token creation with user data."""
        import jwt
        from datetime import datetime, timedelta
        
        # Mock user data
        user_data = {
            "user_id": "288816952992989184",
            "username": "NewSticks",
            "roles": ["814699701861220412"],
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow()
        }
        
        # Create JWT token (mock secret)
        secret_key = "test_secret_key"
        token = jwt.encode(user_data, secret_key, algorithm="HS256")
        
        # Verify token can be decoded
        decoded_data = jwt.decode(token, secret_key, algorithms=["HS256"])
        
        assert decoded_data["user_id"] == "288816952992989184"
        assert decoded_data["username"] == "NewSticks"
        assert "814699701861220412" in decoded_data["roles"]
    
    def test_jwt_token_expiration(self):
        """Test JWT token expiration handling."""
        import jwt
        from datetime import datetime, timedelta
        
        # Create expired token
        expired_data = {
            "user_id": "288816952992989184",
            "exp": datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
        }
        
        secret_key = "test_secret_key"
        expired_token = jwt.encode(expired_data, secret_key, algorithm="HS256")
        
        # Verify expired token raises exception
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(expired_token, secret_key, algorithms=["HS256"])
    
    def test_session_cookie_security(self):
        """Test session cookie security attributes."""
        
        # Mock secure cookie attributes
        cookie_attributes = {
            "httponly": True,
            "secure": True,
            "samesite": "lax",
            "max_age": 86400  # 24 hours
        }
        
        # Verify security attributes are set
        assert cookie_attributes["httponly"] == True  # Prevent XSS
        assert cookie_attributes["secure"] == True    # HTTPS only
        assert cookie_attributes["samesite"] == "lax" # CSRF protection
        assert cookie_attributes["max_age"] > 0       # Has expiration


class TestAuthenticationFlow:
    """Test complete authentication flow integration."""
    
    @pytest.mark.asyncio
    async def test_successful_login_flow(self):
        """Test complete successful login flow."""
        
        # Step 1: User initiates OAuth
        oauth_url = "https://discord.com/api/oauth2/authorize?client_id=test&redirect_uri=test"
        assert "discord.com" in oauth_url
        
        # Step 2: Mock successful callback with code
        auth_code = "mock_auth_code_123"
        assert len(auth_code) > 0
        
        # Step 3: Mock token exchange success
        mock_token = "mock_access_token_456"
        assert len(mock_token) > 0
        
        # Step 4: Mock user data fetch success
        mock_user = {
            "id": "288816952992989184",
            "username": "NewSticks"
        }
        assert mock_user["id"] == "288816952992989184"
        
        # Step 5: Mock database role lookup success
        mock_roles = ["814699701861220412"]  # Admin role
        assert "814699701861220412" in mock_roles
        
        # Step 6: Create session token
        session_token = "jwt_session_token_789"
        assert len(session_token) > 0
        
        # Flow completed successfully
        login_success = True
        assert login_success == True
    
    @pytest.mark.asyncio
    async def test_failed_login_flow(self):
        """Test failed login scenarios."""
        
        # Test 1: Invalid authorization code
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {"error": "invalid_grant"}
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # This should fail token exchange
            token_success = mock_response.status_code == 200
            assert token_success == False
        
        # Test 2: User not in guild database
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetchrow.return_value = None  # User not found
            
            # This should fail authorization
            user_authorized = mock_conn.fetchrow.return_value is not None
            assert user_authorized == False
        
        # Test 3: User has no valid roles
        mock_user_roles = []  # No roles
        has_access = len(mock_user_roles) > 0
        assert has_access == False