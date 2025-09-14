"""
Secure Session Management System for Red Legion Web API.
Provides comprehensive session handling with security features and persistence options.
"""

import secrets
import hashlib
import time
import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field
from fastapi import Request, HTTPException
import logging

logger = logging.getLogger(__name__)

class SessionData(BaseModel):
    """Session data model with security features."""
    user_id: str
    username: str
    access_token: str
    roles: List[str]
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    ip_address: str
    user_agent: str
    is_active: bool = True
    refresh_count: int = 0
    max_refreshes: int = Field(default=5, description="Maximum session refreshes allowed")

class SecurityConfig(BaseModel):
    """Session security configuration."""
    session_timeout_hours: int = Field(default=24, description="Session timeout in hours")
    max_concurrent_sessions: int = Field(default=3, description="Max concurrent sessions per user")
    require_same_ip: bool = Field(default=False, description="Require same IP for session")
    require_same_user_agent: bool = Field(default=False, description="Require same user agent")
    cleanup_interval_minutes: int = Field(default=30, description="Cleanup interval in minutes")
    token_length: int = Field(default=64, description="Session token length")
    enable_session_fingerprinting: bool = Field(default=True, description="Enable fingerprinting")

class SessionManager:
    """Secure session manager with persistence and security features."""

    def __init__(self, config: SecurityConfig = None):
        self.config = config or SecurityConfig()
        self._sessions: Dict[str, SessionData] = {}
        self._user_sessions: Dict[str, List[str]] = {}  # user_id -> [session_tokens]
        self._cleanup_task = None
        self._start_cleanup_task()

    def _start_cleanup_task(self):
        """Start background task for session cleanup."""
        try:
            # Only start cleanup task if event loop is running
            try:
                loop = asyncio.get_running_loop()
                if self._cleanup_task is None:
                    self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            except RuntimeError:
                # No event loop running - will start during first session operation
                logger.info("No event loop running - cleanup task will start later")
        except Exception as e:
            logger.warning(f"Could not start cleanup task: {e}")
            # Don't fail initialization if cleanup task can't start

    async def _periodic_cleanup(self):
        """Periodically clean up expired sessions."""
        while True:
            try:
                await asyncio.sleep(self.config.cleanup_interval_minutes * 60)
                await self.cleanup_expired_sessions()
            except asyncio.CancelledError:
                logger.info("Session cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Session cleanup error: {e}")
                # Continue running even if cleanup fails

    def _generate_session_token(self) -> str:
        """Generate cryptographically secure session token."""
        return secrets.token_urlsafe(self.config.token_length)

    def _create_session_fingerprint(self, request: Request) -> str:
        """Create session fingerprint from request metadata."""
        if not self.config.enable_session_fingerprinting:
            return ""

        components = [
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "unknown"),
            request.headers.get("accept-language", ""),
            request.headers.get("accept-encoding", "")
        ]

        fingerprint_data = "|".join(components)
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]

    async def _ensure_cleanup_task_started(self):
        """Ensure cleanup task is running."""
        if self._cleanup_task is None:
            try:
                self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
                logger.info("Started session cleanup background task")
            except Exception as e:
                logger.warning(f"Could not start cleanup task: {e}")

    async def create_session(
        self,
        user_id: str,
        username: str,
        access_token: str,
        roles: List[str],
        request: Request
    ) -> Tuple[str, SessionData]:
        """Create a new secure session."""

        # Ensure cleanup task is running
        await self._ensure_cleanup_task_started()

        # Check concurrent session limit
        await self._enforce_session_limits(user_id)

        # Generate secure session token
        session_token = self._generate_session_token()

        # Get client info
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        # Create session data
        session_data = SessionData(
            user_id=user_id,
            username=username,
            access_token=access_token,
            roles=roles,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=self.config.session_timeout_hours),
            last_activity=datetime.now(timezone.utc),
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Store session
        self._sessions[session_token] = session_data

        # Track user sessions
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = []
        self._user_sessions[user_id].append(session_token)

        logger.info(
            f"Created session for user {username} (ID: {user_id}) "
            f"from {ip_address} with roles: {roles}"
        )

        return session_token, session_data

    async def _enforce_session_limits(self, user_id: str):
        """Enforce concurrent session limits for user."""
        if user_id in self._user_sessions:
            active_sessions = [
                token for token in self._user_sessions[user_id]
                if token in self._sessions and self._sessions[token].is_active
            ]

            # If at limit, remove oldest session
            if len(active_sessions) >= self.config.max_concurrent_sessions:
                oldest_token = min(
                    active_sessions,
                    key=lambda t: self._sessions[t].created_at
                )
                await self.invalidate_session(oldest_token)
                logger.info(f"Removed oldest session for user {user_id} due to limit")

    async def validate_session(self, session_token: str, request: Request) -> SessionData:
        """Validate and return session data with security checks."""

        if not session_token or session_token not in self._sessions:
            raise HTTPException(
                status_code=401,
                detail="Invalid session token",
                headers={"WWW-Authenticate": "Bearer"}
            )

        session_data = self._sessions[session_token]

        # Check if session is active
        if not session_data.is_active:
            raise HTTPException(
                status_code=401,
                detail="Session has been deactivated",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Check expiration
        if datetime.now(timezone.utc) > session_data.expires_at:
            await self.invalidate_session(session_token)
            raise HTTPException(
                status_code=401,
                detail="Session expired",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Security checks
        await self._perform_security_checks(session_data, request)

        # Update last activity
        session_data.last_activity = datetime.now(timezone.utc)

        return session_data

    async def _perform_security_checks(self, session_data: SessionData, request: Request):
        """Perform additional security validation."""

        current_ip = request.client.host if request.client else "unknown"
        current_ua = request.headers.get("user-agent", "unknown")

        # IP address check
        if self.config.require_same_ip and session_data.ip_address != current_ip:
            logger.warning(
                f"Session IP mismatch for user {session_data.user_id}: "
                f"{session_data.ip_address} vs {current_ip}"
            )
            raise HTTPException(
                status_code=401,
                detail="Session security validation failed",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # User agent check
        if self.config.require_same_user_agent and session_data.user_agent != current_ua:
            logger.warning(
                f"Session User-Agent mismatch for user {session_data.user_id}"
            )
            raise HTTPException(
                status_code=401,
                detail="Session security validation failed",
                headers={"WWW-Authenticate": "Bearer"}
            )

    async def refresh_session(self, session_token: str) -> SessionData:
        """Refresh session expiration time."""

        if session_token not in self._sessions:
            raise HTTPException(status_code=401, detail="Invalid session token")

        session_data = self._sessions[session_token]

        # Check refresh limit
        if session_data.refresh_count >= session_data.max_refreshes:
            await self.invalidate_session(session_token)
            raise HTTPException(
                status_code=401,
                detail="Session refresh limit exceeded"
            )

        # Refresh session
        session_data.expires_at = datetime.now(timezone.utc) + timedelta(
            hours=self.config.session_timeout_hours
        )
        session_data.refresh_count += 1
        session_data.last_activity = datetime.now(timezone.utc)

        logger.info(f"Refreshed session for user {session_data.user_id}")
        return session_data

    async def invalidate_session(self, session_token: str):
        """Invalidate a specific session."""

        if session_token in self._sessions:
            session_data = self._sessions[session_token]

            # Mark as inactive
            session_data.is_active = False

            # Remove from user sessions tracking
            user_id = session_data.user_id
            if user_id in self._user_sessions:
                self._user_sessions[user_id] = [
                    token for token in self._user_sessions[user_id]
                    if token != session_token
                ]

                # Clean up empty user session lists
                if not self._user_sessions[user_id]:
                    del self._user_sessions[user_id]

            # Remove session
            del self._sessions[session_token]

            logger.info(f"Invalidated session for user {session_data.user_id}")

    async def invalidate_all_user_sessions(self, user_id: str):
        """Invalidate all sessions for a specific user."""

        if user_id in self._user_sessions:
            session_tokens = self._user_sessions[user_id].copy()
            for session_token in session_tokens:
                await self.invalidate_session(session_token)

            logger.info(f"Invalidated all sessions for user {user_id}")

    async def cleanup_expired_sessions(self) -> int:
        """Clean up all expired sessions and return count."""

        now = datetime.now(timezone.utc)
        expired_tokens = []

        for session_token, session_data in self._sessions.items():
            if now > session_data.expires_at or not session_data.is_active:
                expired_tokens.append(session_token)

        # Clean up expired sessions
        for session_token in expired_tokens:
            await self.invalidate_session(session_token)

        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired sessions")

        return len(expired_tokens)

    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics for monitoring."""

        now = datetime.now(timezone.utc)
        active_sessions = 0
        expired_sessions = 0

        for session_data in self._sessions.values():
            if session_data.is_active and now <= session_data.expires_at:
                active_sessions += 1
            else:
                expired_sessions += 1

        return {
            "total_sessions": len(self._sessions),
            "active_sessions": active_sessions,
            "expired_sessions": expired_sessions,
            "unique_users": len(self._user_sessions),
            "config": self.config.dict()
        }

    async def shutdown(self):
        """Gracefully shutdown the session manager."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("Session manager shutdown complete")

# Global session manager instance
session_manager = SessionManager()

async def get_session_manager() -> SessionManager:
    """Dependency to get session manager instance."""
    return session_manager