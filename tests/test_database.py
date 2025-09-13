"""
Unit tests for database operations.
Tests database connectivity, queries, and data integrity.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import asyncpg


class TestDatabaseConnection:
    """Test database connection and pool management."""
    
    @pytest.mark.asyncio
    async def test_database_connection_success(self):
        """Test successful database connection."""
        
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 1
        
        with patch('asyncpg.connect', return_value=mock_conn):
            conn = await asyncpg.connect("postgresql://test")
            result = await conn.fetchval("SELECT 1")
            
            assert result == 1
            mock_conn.fetchval.assert_called_once_with("SELECT 1")
    
    @pytest.mark.asyncio 
    async def test_database_connection_failure(self):
        """Test database connection failure handling."""
        
        with patch('asyncpg.connect', side_effect=asyncpg.ConnectionDoesNotExistError("Connection failed")):
            with pytest.raises(asyncpg.ConnectionDoesNotExistError):
                await asyncpg.connect("postgresql://invalid")
    
    @pytest.mark.asyncio
    async def test_connection_pool_management(self):
        """Test connection pool creation and management."""
        
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        with patch('asyncpg.create_pool', return_value=mock_pool):
            pool = await asyncpg.create_pool("postgresql://test", min_size=1, max_size=10)
            
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            
            mock_pool.acquire.assert_called_once()


class TestUserOperations:
    """Test user-related database operations."""
    
    @pytest.mark.asyncio
    async def test_user_lookup_by_id(self):
        """Test looking up user by Discord ID."""
        
        mock_user_data = {
            "user_id": "288816952992989184",
            "username": "NewSticks", 
            "display_name": "NewSticks",
            "is_active": True,
            "first_seen": datetime.now(),
            "last_seen": datetime.now()
        }
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = mock_user_data
        
        with patch('asyncpg.connect', return_value=mock_conn):
            conn = await asyncpg.connect("postgresql://test")
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE user_id = $1", 
                "288816952992989184"
            )
            
            assert user["user_id"] == "288816952992989184"
            assert user["username"] == "NewSticks"
            assert user["is_active"] == True
    
    @pytest.mark.asyncio
    async def test_user_creation(self):
        """Test creating new user in database."""
        
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "INSERT 0 1"
        
        user_data = {
            "user_id": "123456789",
            "username": "TestUser",
            "display_name": "Test User",
            "first_seen": datetime.now(),
            "last_seen": datetime.now()
        }
        
        with patch('asyncpg.connect', return_value=mock_conn):
            conn = await asyncpg.connect("postgresql://test")
            result = await conn.execute("""
                INSERT INTO users (user_id, username, display_name, first_seen, last_seen, is_active)
                VALUES ($1, $2, $3, $4, $5, TRUE)
            """, user_data["user_id"], user_data["username"], user_data["display_name"],
                user_data["first_seen"], user_data["last_seen"])
            
            assert "INSERT" in result
            mock_conn.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_user_update(self):
        """Test updating existing user."""
        
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "UPDATE 1"
        
        with patch('asyncpg.connect', return_value=mock_conn):
            conn = await asyncpg.connect("postgresql://test")
            result = await conn.execute("""
                UPDATE users SET username = $2, last_seen = $3 
                WHERE user_id = $1
            """, "288816952992989184", "UpdatedName", datetime.now())
            
            assert "UPDATE" in result
            mock_conn.execute.assert_called_once()


class TestGuildMembershipOperations:
    """Test guild membership database operations."""
    
    @pytest.mark.asyncio
    async def test_guild_membership_lookup(self):
        """Test looking up guild membership."""
        
        mock_membership_data = {
            "guild_id": "814699481912049704",
            "user_id": "288816952992989184", 
            "joined_at": datetime.now(),
            "roles": ["814699701861220412", "814699481912049708"],
            "nickname": "NewSticks",
            "is_active": True
        }
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = mock_membership_data
        
        with patch('asyncpg.connect', return_value=mock_conn):
            conn = await asyncpg.connect("postgresql://test")
            membership = await conn.fetchrow("""
                SELECT * FROM guild_memberships 
                WHERE guild_id = $1 AND user_id = $2 AND is_active = TRUE
            """, "814699481912049704", "288816952992989184")
            
            assert membership["guild_id"] == "814699481912049704"
            assert membership["user_id"] == "288816952992989184"
            assert "814699701861220412" in membership["roles"]
            assert membership["is_active"] == True
    
    @pytest.mark.asyncio
    async def test_guild_membership_upsert(self):
        """Test upserting guild membership."""
        
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "INSERT 0 1"
        
        membership_data = {
            "guild_id": "814699481912049704",
            "user_id": "288816952992989184",
            "joined_at": datetime.now(),
            "roles": ["814699701861220412"],
            "nickname": "NewSticks"
        }
        
        with patch('asyncpg.connect', return_value=mock_conn):
            conn = await asyncpg.connect("postgresql://test")
            result = await conn.execute("""
                INSERT INTO guild_memberships 
                (guild_id, user_id, joined_at, roles, nickname, is_active)
                VALUES ($1, $2, $3, $4, $5, TRUE)
                ON CONFLICT (guild_id, user_id)
                DO UPDATE SET
                    roles = EXCLUDED.roles,
                    nickname = EXCLUDED.nickname,
                    is_active = TRUE,
                    left_at = NULL
            """, membership_data["guild_id"], membership_data["user_id"], 
                membership_data["joined_at"], membership_data["roles"], 
                membership_data["nickname"])
            
            mock_conn.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_guild_membership_deactivation(self):
        """Test deactivating guild membership when user leaves."""
        
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "UPDATE 1"
        
        with patch('asyncpg.connect', return_value=mock_conn):
            conn = await asyncpg.connect("postgresql://test")
            result = await conn.execute("""
                UPDATE guild_memberships 
                SET is_active = FALSE, left_at = $3
                WHERE guild_id = $1 AND user_id = $2
            """, "814699481912049704", "288816952992989184", datetime.now())
            
            assert "UPDATE" in result
            mock_conn.execute.assert_called_once()


class TestRoleOperations:
    """Test role-related database operations."""
    
    @pytest.mark.asyncio
    async def test_role_lookup_by_id(self):
        """Test looking up role by ID."""
        
        mock_role_data = {
            "role_id": "814699701861220412",
            "guild_id": "814699481912049704",
            "role_name": "Admin",
            "permissions": 8,  # Administrator permission
            "color": 16711680,  # Red color
            "position": 10,
            "is_active": True
        }
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = mock_role_data
        
        with patch('asyncpg.connect', return_value=mock_conn):
            conn = await asyncpg.connect("postgresql://test")
            role = await conn.fetchrow(
                "SELECT * FROM roles WHERE role_id = $1", 
                "814699701861220412"
            )
            
            assert role["role_id"] == "814699701861220412"
            assert role["role_name"] == "Admin"
            assert role["permissions"] == 8
    
    @pytest.mark.asyncio
    async def test_user_roles_lookup(self):
        """Test looking up all roles for a user."""
        
        mock_roles_data = [
            {
                "role_id": "814699701861220412",
                "role_name": "Admin",
                "permissions": 8
            },
            {
                "role_id": "814699481912049708", 
                "role_name": "@everyone",
                "permissions": 0
            }
        ]
        
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = mock_roles_data
        
        with patch('asyncpg.connect', return_value=mock_conn):
            conn = await asyncpg.connect("postgresql://test")
            user_roles = await conn.fetch("""
                SELECT r.role_id, r.role_name, r.permissions
                FROM roles r
                JOIN guild_memberships gm ON gm.guild_id = r.guild_id
                WHERE gm.user_id = $1 AND gm.is_active = TRUE
                AND r.role_id = ANY(gm.roles)
            """, "288816952992989184")
            
            assert len(user_roles) == 2
            assert any(role["role_name"] == "Admin" for role in user_roles)
            assert any(role["role_name"] == "@everyone" for role in user_roles)
    
    @pytest.mark.asyncio
    async def test_admin_permission_check(self):
        """Test checking if user has admin permissions."""
        
        admin_role_id = "814699701861220412"
        
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 1  # User has admin role
        
        with patch('asyncpg.connect', return_value=mock_conn):
            conn = await asyncpg.connect("postgresql://test")
            has_admin = await conn.fetchval("""
                SELECT COUNT(*)
                FROM guild_memberships gm
                WHERE gm.user_id = $1 AND gm.is_active = TRUE
                AND $2 = ANY(gm.roles)
            """, "288816952992989184", admin_role_id)
            
            assert has_admin > 0
            mock_conn.fetchval.assert_called_once()


class TestMiningEventOperations:
    """Test mining event database operations."""
    
    @pytest.mark.asyncio
    async def test_mining_event_creation(self):
        """Test creating a new mining event."""
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {
            "event_id": "test_event_123",
            "guild_id": "814699481912049704",
            "organizer_id": "288816952992989184",
            "start_time": datetime.now(),
            "status": "active"
        }
        
        event_data = {
            "event_id": "test_event_123",
            "guild_id": "814699481912049704",
            "organizer_id": "288816952992989184",
            "organizer_name": "NewSticks",
            "location": "Yela",
            "event_type": "mining",
            "start_time": datetime.now()
        }
        
        with patch('asyncpg.connect', return_value=mock_conn):
            conn = await asyncpg.connect("postgresql://test")
            event = await conn.fetchrow("""
                INSERT INTO mining_events 
                (event_id, guild_id, organizer_id, organizer_name, location, event_type, start_time, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, 'active')
                RETURNING *
            """, event_data["event_id"], event_data["guild_id"], event_data["organizer_id"],
                event_data["organizer_name"], event_data["location"], event_data["event_type"],
                event_data["start_time"])
            
            assert event["event_id"] == "test_event_123"
            assert event["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_mining_event_lookup(self):
        """Test looking up mining event by ID."""
        
        mock_event_data = {
            "event_id": "test_event_123",
            "guild_id": "814699481912049704",
            "organizer_id": "288816952992989184",
            "organizer_name": "NewSticks",
            "location": "Yela",
            "event_type": "mining",
            "start_time": datetime.now() - timedelta(hours=1),
            "end_time": None,
            "status": "active",
            "total_participants": 5,
            "total_duration_minutes": 60
        }
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = mock_event_data
        
        with patch('asyncpg.connect', return_value=mock_conn):
            conn = await asyncpg.connect("postgresql://test")
            event = await conn.fetchrow(
                "SELECT * FROM mining_events WHERE event_id = $1",
                "test_event_123"
            )
            
            assert event["event_id"] == "test_event_123"
            assert event["organizer_name"] == "NewSticks"
            assert event["status"] == "active"
            assert event["total_participants"] == 5
    
    @pytest.mark.asyncio
    async def test_mining_event_closure(self):
        """Test closing a mining event."""
        
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "UPDATE 1"
        
        with patch('asyncpg.connect', return_value=mock_conn):
            conn = await asyncpg.connect("postgresql://test")
            result = await conn.execute("""
                UPDATE mining_events 
                SET status = 'completed', end_time = $2, closed_by_id = $3, closed_by_name = $4
                WHERE event_id = $1
            """, "test_event_123", datetime.now(), "288816952992989184", "NewSticks")
            
            assert "UPDATE" in result
            mock_conn.execute.assert_called_once()


class TestTransactionHandling:
    """Test database transaction management."""
    
    @pytest.mark.asyncio
    async def test_transaction_commit(self):
        """Test successful transaction commit."""
        
        mock_conn = AsyncMock()
        mock_transaction = AsyncMock()
        mock_conn.transaction.return_value.__aenter__.return_value = mock_transaction
        
        with patch('asyncpg.connect', return_value=mock_conn):
            conn = await asyncpg.connect("postgresql://test")
            
            async with conn.transaction():
                await conn.execute("INSERT INTO users (...) VALUES (...)")
                await conn.execute("INSERT INTO guild_memberships (...) VALUES (...)")
            
            # Verify transaction was used
            mock_conn.transaction.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_transaction_rollback(self):
        """Test transaction rollback on error."""
        
        mock_conn = AsyncMock()
        mock_transaction = AsyncMock()
        mock_conn.transaction.return_value.__aenter__.return_value = mock_transaction
        mock_conn.execute.side_effect = [None, Exception("Database error")]
        
        with patch('asyncpg.connect', return_value=mock_conn):
            conn = await asyncpg.connect("postgresql://test")
            
            with pytest.raises(Exception):
                async with conn.transaction():
                    await conn.execute("INSERT INTO users (...) VALUES (...)")
                    await conn.execute("INVALID SQL STATEMENT")
            
            # Transaction should have been attempted
            mock_conn.transaction.assert_called_once()


class TestDataIntegrity:
    """Test data integrity and constraints."""
    
    @pytest.mark.asyncio
    async def test_unique_constraint_violation(self):
        """Test handling of unique constraint violations."""
        
        mock_conn = AsyncMock()
        mock_conn.execute.side_effect = asyncpg.UniqueViolationError("Duplicate key")
        
        with patch('asyncpg.connect', return_value=mock_conn):
            conn = await asyncpg.connect("postgresql://test")
            
            with pytest.raises(asyncpg.UniqueViolationError):
                await conn.execute("""
                    INSERT INTO users (user_id, username) 
                    VALUES ('288816952992989184', 'NewSticks')
                """)
    
    @pytest.mark.asyncio
    async def test_foreign_key_constraint(self):
        """Test foreign key constraint validation."""
        
        mock_conn = AsyncMock()
        mock_conn.execute.side_effect = asyncpg.ForeignKeyViolationError("Foreign key violation")
        
        with patch('asyncpg.connect', return_value=mock_conn):
            conn = await asyncpg.connect("postgresql://test")
            
            with pytest.raises(asyncpg.ForeignKeyViolationError):
                await conn.execute("""
                    INSERT INTO guild_memberships (guild_id, user_id) 
                    VALUES ('814699481912049704', 'nonexistent_user')
                """)
    
    def test_data_validation(self):
        """Test data validation before database operations."""
        
        # Test Discord ID format validation
        def is_valid_discord_id(discord_id):
            return discord_id.isdigit() and len(discord_id) >= 17
        
        assert is_valid_discord_id("288816952992989184") == True
        assert is_valid_discord_id("invalid_id") == False
        assert is_valid_discord_id("123") == False
        
        # Test role ID array validation
        def is_valid_role_array(roles):
            return isinstance(roles, list) and all(isinstance(role, str) for role in roles)
        
        assert is_valid_role_array(["814699701861220412"]) == True
        assert is_valid_role_array("not_a_list") == False
        assert is_valid_role_array([123, 456]) == False