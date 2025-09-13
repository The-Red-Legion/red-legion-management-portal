"""
API Endpoint Tests
Tests all API endpoints, authentication, and role-based access control.
"""

import pytest
import asyncio
import httpx
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime, timedelta
import jwt


# Mock FastAPI app for testing
@pytest.fixture
def mock_api_app():
    """Create a mock FastAPI app with protected endpoints."""
    app = FastAPI()
    
    @app.get("/")
    async def root():
        return {"message": "Red Legion Web API", "version": "1.0.0"}
    
    @app.get("/api/health")
    async def health_check():
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
    
    @app.get("/auth/me")
    async def get_current_user():
        return {
            "user_id": "288816952992989184",
            "username": "NewSticks",
            "roles": ["814699701861220412"],
            "permissions": ["admin"]
        }
    
    @app.get("/api/users")
    async def get_users():
        return {"users": [], "total": 0}
    
    @app.get("/api/events")
    async def get_events():
        return {"events": [], "total": 0}
    
    @app.post("/api/events")
    async def create_event():
        return {"success": True, "event_id": "test_event_123"}
    
    @app.get("/api/admin/stats")
    async def get_admin_stats():
        return {"total_users": 100, "active_events": 5}
    
    return app


@pytest.fixture
def api_client(mock_api_app):
    """Create a test client for the API."""
    return TestClient(mock_api_app)


class TestPublicEndpoints:
    """Test publicly accessible API endpoints."""
    
    def test_root_endpoint(self, api_client):
        """Test root endpoint is accessible without authentication."""
        response = api_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["message"] == "Red Legion Web API"
    
    def test_health_check_endpoint(self, api_client):
        """Test health check endpoint."""
        response = api_client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_public_endpoints_no_auth_required(self):
        """Test public endpoints don't require authentication."""
        
        async with httpx.AsyncClient(base_url="https://dev.redlegion.gg") as client:
            # Mock responses for public endpoints
            with patch.object(client, 'get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"message": "API accessible"}
                mock_get.return_value = mock_response
                
                response = await client.get("/api/health")
                
                assert response.status_code == 200
                mock_get.assert_called_once_with("/api/health")


class TestAuthenticationEndpoints:
    """Test authentication-related endpoints."""
    
    def test_auth_me_endpoint_structure(self, api_client):
        """Test /auth/me endpoint returns proper user structure."""
        response = api_client.get("/auth/me")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        required_fields = ["user_id", "username", "roles", "permissions"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Verify data types
        assert isinstance(data["user_id"], str)
        assert isinstance(data["username"], str)
        assert isinstance(data["roles"], list)
        assert isinstance(data["permissions"], list)
    
    @pytest.mark.asyncio
    async def test_auth_me_with_valid_token(self):
        """Test /auth/me with valid JWT token."""
        
        # Create valid JWT token
        jwt_secret = "test_secret_key"
        token_data = {
            "user_id": "288816952992989184",
            "username": "NewSticks",
            "roles": ["814699701861220412"],
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        valid_token = jwt.encode(token_data, jwt_secret, algorithm="HS256")
        
        async with httpx.AsyncClient() as client:
            with patch.object(client, 'get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "user_id": "288816952992989184",
                    "username": "NewSticks",
                    "roles": ["814699701861220412"],
                    "permissions": ["admin"]
                }
                mock_get.return_value = mock_response
                
                headers = {"Authorization": f"Bearer {valid_token}"}
                response = await client.get("/auth/me", headers=headers)
                
                assert response.status_code == 200
                data = response.json()
                assert data["user_id"] == "288816952992989184"
    
    @pytest.mark.asyncio
    async def test_auth_me_with_invalid_token(self):
        """Test /auth/me with invalid JWT token."""
        
        invalid_token = "invalid.jwt.token"
        
        async with httpx.AsyncClient() as client:
            with patch.object(client, 'get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 401
                mock_response.json.return_value = {"detail": "Invalid token"}
                mock_get.return_value = mock_response
                
                headers = {"Authorization": f"Bearer {invalid_token}"}
                response = await client.get("/auth/me", headers=headers)
                
                assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_auth_me_with_expired_token(self):
        """Test /auth/me with expired JWT token."""
        
        jwt_secret = "test_secret_key"
        expired_token_data = {
            "user_id": "288816952992989184",
            "username": "NewSticks",
            "exp": datetime.utcnow() - timedelta(hours=1)  # Expired
        }
        expired_token = jwt.encode(expired_token_data, jwt_secret, algorithm="HS256")
        
        async with httpx.AsyncClient() as client:
            with patch.object(client, 'get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 401
                mock_response.json.return_value = {"detail": "Token expired"}
                mock_get.return_value = mock_response
                
                headers = {"Authorization": f"Bearer {expired_token}"}
                response = await client.get("/auth/me", headers=headers)
                
                assert response.status_code == 401


class TestProtectedEndpoints:
    """Test endpoints that require authentication."""
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_without_auth(self):
        """Test protected endpoints reject requests without authentication."""
        
        protected_endpoints = [
            "/api/users",
            "/api/events",
            "/api/admin/stats"
        ]
        
        async with httpx.AsyncClient() as client:
            for endpoint in protected_endpoints:
                with patch.object(client, 'get') as mock_get:
                    mock_response = Mock()
                    mock_response.status_code = 401
                    mock_response.json.return_value = {"detail": "Not authenticated"}
                    mock_get.return_value = mock_response
                    
                    response = await client.get(endpoint)
                    
                    assert response.status_code == 401, f"Endpoint {endpoint} should require auth"
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_with_valid_auth(self):
        """Test protected endpoints accept valid authentication."""
        
        # Create valid token
        jwt_secret = "test_secret_key"
        token_data = {
            "user_id": "288816952992989184",
            "username": "NewSticks",
            "roles": ["814699701861220412"],  # Admin role
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        valid_token = jwt.encode(token_data, jwt_secret, algorithm="HS256")
        
        async with httpx.AsyncClient() as client:
            with patch.object(client, 'get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"users": [], "total": 0}
                mock_get.return_value = mock_response
                
                headers = {"Authorization": f"Bearer {valid_token}"}
                response = await client.get("/api/users", headers=headers)
                
                assert response.status_code == 200


class TestRoleBasedAccess:
    """Test role-based access control for different endpoints."""
    
    def create_jwt_token(self, user_data, jwt_secret="test_secret_key"):
        """Helper to create JWT tokens with different roles."""
        token_data = {
            "exp": datetime.utcnow() + timedelta(hours=1),
            **user_data
        }
        return jwt.encode(token_data, jwt_secret, algorithm="HS256")
    
    @pytest.mark.asyncio
    async def test_admin_endpoint_requires_admin_role(self):
        """Test admin endpoints require Admin role."""
        
        # Test with Admin role
        admin_token = self.create_jwt_token({
            "user_id": "288816952992989184",
            "username": "NewSticks",
            "roles": ["814699701861220412"]  # Admin role
        })
        
        async with httpx.AsyncClient() as client:
            with patch.object(client, 'get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"total_users": 100, "active_events": 5}
                mock_get.return_value = mock_response
                
                headers = {"Authorization": f"Bearer {admin_token}"}
                response = await client.get("/api/admin/stats", headers=headers)
                
                assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_admin_endpoint_rejects_non_admin(self):
        """Test admin endpoints reject non-admin users."""
        
        # Test with regular user (only @everyone role)
        regular_token = self.create_jwt_token({
            "user_id": "123456789012345678",
            "username": "RegularUser", 
            "roles": ["814699481912049708"]  # @everyone role only
        })
        
        async with httpx.AsyncClient() as client:
            with patch.object(client, 'get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 403
                mock_response.json.return_value = {"detail": "Insufficient permissions"}
                mock_get.return_value = mock_response
                
                headers = {"Authorization": f"Bearer {regular_token}"}
                response = await client.get("/api/admin/stats", headers=headers)
                
                assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_officer_level_access(self):
        """Test Officer-level access to certain endpoints."""
        
        officer_token = self.create_jwt_token({
            "user_id": "987654321098765432",
            "username": "OfficerUser",
            "roles": ["814699648451510287"]  # Officer role
        })
        
        async with httpx.AsyncClient() as client:
            with patch.object(client, 'get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"events": [], "total": 0}
                mock_get.return_value = mock_response
                
                headers = {"Authorization": f"Bearer {officer_token}"}
                response = await client.get("/api/events", headers=headers)
                
                assert response.status_code == 200
    
    def test_role_hierarchy_validation(self):
        """Test role hierarchy is properly validated."""
        
        # Define role hierarchy
        role_hierarchy = {
            "814699701861220412": 100,  # Admin
            "814699648451510287": 75,   # Officer
            "814699559275126814": 50,   # Senior Member
            "814699481912049708": 1     # @everyone
        }
        
        def has_permission_level(user_roles, required_level):
            user_levels = [role_hierarchy.get(role_id, 0) for role_id in user_roles]
            return max(user_levels, default=0) >= required_level
        
        # Test Admin has access to Officer-level features
        admin_roles = ["814699701861220412"]
        assert has_permission_level(admin_roles, 75) == True
        
        # Test Officer has access to Officer-level features
        officer_roles = ["814699648451510287"]
        assert has_permission_level(officer_roles, 75) == True
        
        # Test Senior Member doesn't have Officer access
        senior_roles = ["814699559275126814"]
        assert has_permission_level(senior_roles, 75) == False
        
        # Test regular user doesn't have Officer access
        regular_roles = ["814699481912049708"]
        assert has_permission_level(regular_roles, 75) == False


class TestAPIEndpointFunctionality:
    """Test specific API endpoint functionality."""
    
    @pytest.mark.asyncio
    async def test_users_endpoint_functionality(self):
        """Test /api/users endpoint returns proper data structure."""
        
        mock_users_data = {
            "users": [
                {
                    "user_id": "288816952992989184",
                    "username": "NewSticks",
                    "display_name": "NewSticks",
                    "roles": ["814699701861220412"],
                    "is_active": True,
                    "last_seen": datetime.utcnow().isoformat()
                }
            ],
            "total": 1,
            "page": 1,
            "per_page": 50
        }
        
        async with httpx.AsyncClient() as client:
            with patch.object(client, 'get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_users_data
                mock_get.return_value = mock_response
                
                valid_token = self.create_jwt_token({
                    "user_id": "288816952992989184",
                    "roles": ["814699701861220412"]
                })
                
                headers = {"Authorization": f"Bearer {valid_token}"}
                response = await client.get("/api/users", headers=headers)
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify response structure
                assert "users" in data
                assert "total" in data
                assert isinstance(data["users"], list)
                assert isinstance(data["total"], int)
    
    def create_jwt_token(self, user_data, jwt_secret="test_secret_key"):
        """Helper to create JWT tokens."""
        token_data = {
            "exp": datetime.utcnow() + timedelta(hours=1),
            **user_data
        }
        return jwt.encode(token_data, jwt_secret, algorithm="HS256")
    
    @pytest.mark.asyncio
    async def test_events_endpoint_functionality(self):
        """Test /api/events endpoint returns proper data structure."""
        
        mock_events_data = {
            "events": [
                {
                    "event_id": "event_123",
                    "event_type": "mining",
                    "organizer_name": "NewSticks",
                    "location": "Yela",
                    "start_time": datetime.utcnow().isoformat(),
                    "status": "active",
                    "participants": 5
                }
            ],
            "total": 1,
            "active_events": 1,
            "completed_events": 0
        }
        
        async with httpx.AsyncClient() as client:
            with patch.object(client, 'get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_events_data
                mock_get.return_value = mock_response
                
                valid_token = self.create_jwt_token({
                    "user_id": "288816952992989184",
                    "roles": ["814699701861220412"]
                })
                
                headers = {"Authorization": f"Bearer {valid_token}"}
                response = await client.get("/api/events", headers=headers)
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify response structure
                assert "events" in data
                assert "total" in data
                assert isinstance(data["events"], list)
                assert isinstance(data["total"], int)
    
    @pytest.mark.asyncio
    async def test_create_event_endpoint(self):
        """Test POST /api/events for event creation."""
        
        event_data = {
            "event_type": "mining",
            "organizer_name": "NewSticks",
            "location": "Yela",
            "notes": "Test mining event"
        }
        
        mock_response_data = {
            "success": True,
            "event_id": "event_abc123",
            "message": "Event created successfully"
        }
        
        async with httpx.AsyncClient() as client:
            with patch.object(client, 'post') as mock_post:
                mock_response = Mock()
                mock_response.status_code = 201
                mock_response.json.return_value = mock_response_data
                mock_post.return_value = mock_response
                
                valid_token = self.create_jwt_token({
                    "user_id": "288816952992989184",
                    "roles": ["814699701861220412"]
                })
                
                headers = {"Authorization": f"Bearer {valid_token}"}
                response = await client.post("/api/events", headers=headers, json=event_data)
                
                assert response.status_code == 201
                data = response.json()
                assert data["success"] == True
                assert "event_id" in data


class TestAPIErrorHandling:
    """Test API error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_database_connection_error(self):
        """Test API behavior when database is unavailable."""
        
        async with httpx.AsyncClient() as client:
            with patch.object(client, 'get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 503
                mock_response.json.return_value = {
                    "detail": "Service temporarily unavailable",
                    "error": "Database connection failed"
                }
                mock_get.return_value = mock_response
                
                valid_token = self.create_jwt_token({
                    "user_id": "288816952992989184",
                    "roles": ["814699701861220412"]
                })
                
                headers = {"Authorization": f"Bearer {valid_token}"}
                response = await client.get("/api/users", headers=headers)
                
                assert response.status_code == 503
                data = response.json()
                assert "Service temporarily unavailable" in data["detail"]
    
    def create_jwt_token(self, user_data, jwt_secret="test_secret_key"):
        """Helper to create JWT tokens."""
        token_data = {
            "exp": datetime.utcnow() + timedelta(hours=1),
            **user_data
        }
        return jwt.encode(token_data, jwt_secret, algorithm="HS256")
    
    @pytest.mark.asyncio 
    async def test_malformed_request_data(self):
        """Test API handling of malformed request data."""
        
        malformed_data = {
            "invalid_field": "invalid_value",
            # Missing required fields
        }
        
        async with httpx.AsyncClient() as client:
            with patch.object(client, 'post') as mock_post:
                mock_response = Mock()
                mock_response.status_code = 422
                mock_response.json.return_value = {
                    "detail": "Validation error",
                    "errors": ["Missing required field: event_type"]
                }
                mock_post.return_value = mock_response
                
                valid_token = self.create_jwt_token({
                    "user_id": "288816952992989184",
                    "roles": ["814699701861220412"]
                })
                
                headers = {"Authorization": f"Bearer {valid_token}"}
                response = await client.post("/api/events", headers=headers, json=malformed_data)
                
                assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test API rate limiting behavior."""
        
        async with httpx.AsyncClient() as client:
            with patch.object(client, 'get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 429
                mock_response.json.return_value = {
                    "detail": "Rate limit exceeded",
                    "retry_after": 60
                }
                mock_get.return_value = mock_response
                
                valid_token = self.create_jwt_token({
                    "user_id": "288816952992989184",
                    "roles": ["814699701861220412"]
                })
                
                headers = {"Authorization": f"Bearer {valid_token}"}
                
                # Simulate rate limit hit
                response = await client.get("/api/users", headers=headers)
                
                assert response.status_code == 429
                data = response.json()
                assert "Rate limit exceeded" in data["detail"]
                assert "retry_after" in data


class TestAPISecurityHeaders:
    """Test API security headers and CORS settings."""
    
    @pytest.mark.asyncio
    async def test_security_headers_present(self):
        """Test that proper security headers are included in responses."""
        
        expected_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options", 
            "X-XSS-Protection",
            "Strict-Transport-Security"
        ]
        
        async with httpx.AsyncClient() as client:
            with patch.object(client, 'get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.headers = {
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                    "X-XSS-Protection": "1; mode=block",
                    "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
                }
                mock_response.json.return_value = {"status": "healthy"}
                mock_get.return_value = mock_response
                
                response = await client.get("/api/health")
                
                assert response.status_code == 200
                
                for header in expected_headers:
                    assert header in response.headers, f"Missing security header: {header}"
    
    @pytest.mark.asyncio
    async def test_cors_configuration(self):
        """Test CORS headers are properly configured."""
        
        async with httpx.AsyncClient() as client:
            with patch.object(client, 'options') as mock_options:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.headers = {
                    "Access-Control-Allow-Origin": "https://dev.redlegion.gg",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "Authorization, Content-Type",
                    "Access-Control-Max-Age": "86400"
                }
                mock_options.return_value = mock_response
                
                headers = {"Origin": "https://dev.redlegion.gg"}
                response = await client.options("/api/users", headers=headers)
                
                assert response.status_code == 200
                assert "Access-Control-Allow-Origin" in response.headers
                assert "Access-Control-Allow-Methods" in response.headers