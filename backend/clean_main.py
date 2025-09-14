#!/usr/bin/env python3
"""
Clean, minimal Discord OAuth backend.
No unnecessary complexity - just basic OAuth flow.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
import httpx
import os
import uvicorn
from datetime import datetime, timezone
import secrets
import json

# Load environment
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://dev.redlegion.gg/auth/discord/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://dev.redlegion.gg")

print(f"Discord Client ID: {'✓' if DISCORD_CLIENT_ID else '✗'}")
print(f"Discord Client Secret: {'✓' if DISCORD_CLIENT_SECRET else '✗'}")
print(f"Redirect URI: {DISCORD_REDIRECT_URI}")
print(f"Frontend URL: {FRONTEND_URL}")

# Create FastAPI app
app = FastAPI(title="Red Legion - Clean OAuth Backend")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# In-memory session store (simple for now)
user_sessions = {}

@app.get("/")
async def root():
    return {"message": "Red Legion Clean OAuth Backend", "status": "ok"}

@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "Clean backend responding"}

@app.get("/health")
async def health():
    return {"status": "healthy", "mode": "clean"}

@app.get("/auth/discord")
async def discord_login():
    """Start Discord OAuth flow."""
    if not DISCORD_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Discord client ID not configured")

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)

    # Store state temporarily (in production, use Redis or database)
    # For now, we'll just pass it along

    discord_auth_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={DISCORD_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify"
        f"&state={state}"
    )

    return RedirectResponse(discord_auth_url)

@app.get("/auth/discord/callback")
async def discord_callback(code: str = None, state: str = None, error: str = None):
    """Handle Discord OAuth callback."""

    global callback_attempts
    callback_attempts += 1

    print(f"=== OAuth Callback Debug (Attempt #{callback_attempts}) ===")
    print(f"Code: {'✓' if code else '✗'}")
    print(f"State: {state}")
    print(f"Error: {error}")

    if error:
        print(f"OAuth error: {error}")
        return RedirectResponse(f"{FRONTEND_URL}?error={error}")

    if not code:
        print("No authorization code received")
        return RedirectResponse(f"{FRONTEND_URL}?error=no_code")

    # Exchange code for access token
    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://discord.com/api/oauth2/token",
                data={
                    "client_id": DISCORD_CLIENT_ID,
                    "client_secret": DISCORD_CLIENT_SECRET,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": DISCORD_REDIRECT_URI,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if token_response.status_code != 200:
                print(f"Token exchange failed: {token_response.status_code} - {token_response.text}")
                return RedirectResponse(f"{FRONTEND_URL}?error=token_exchange_failed")

            token_data = token_response.json()
            access_token = token_data.get("access_token")

            if not access_token:
                return RedirectResponse(f"{FRONTEND_URL}?error=no_access_token")

            # Get user info from Discord
            user_response = await client.get(
                "https://discord.com/api/users/@me",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if user_response.status_code != 200:
                print(f"User info failed: {user_response.status_code} - {user_response.text}")
                return RedirectResponse(f"{FRONTEND_URL}?error=user_info_failed")

            user_data = user_response.json()
            user_id = user_data.get("id")
            username = user_data.get("username")

            if not user_id:
                return RedirectResponse(f"{FRONTEND_URL}?error=no_user_id")

            # Create simple session
            session_token = secrets.token_urlsafe(32)
            user_sessions[session_token] = {
                "user_id": user_id,
                "username": username,
                "access_token": access_token,
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            print(f"✓ Session created for user {username} ({user_id})")
            print(f"✓ Session token: {session_token[:8]}...")
            print(f"✓ Total sessions: {len(user_sessions)}")

            # Redirect to frontend with session token
            response = RedirectResponse(f"{FRONTEND_URL}?token={session_token}")
            response.set_cookie("session_token", session_token, httponly=True, max_age=86400)  # 24 hours
            print(f"✓ Redirecting to: {FRONTEND_URL}?token={session_token[:8]}...")
            return response

    except Exception as e:
        print(f"OAuth callback error: {e}")
        return RedirectResponse(f"{FRONTEND_URL}?error=callback_failed")

@app.get("/auth/user")
async def get_user(request: Request):
    """Get current user info."""
    # Get session token from cookie or query param
    session_token = request.cookies.get("session_token") or request.query_params.get("token")

    print(f"=== Auth Check Debug ===")
    print(f"Cookie token: {'✓' if request.cookies.get('session_token') else '✗'}")
    print(f"Query token: {'✓' if request.query_params.get('token') else '✗'}")
    print(f"Session token: {session_token[:8] + '...' if session_token else 'None'}")
    print(f"Active sessions: {len(user_sessions)}")

    if not session_token or session_token not in user_sessions:
        print(f"❌ Authentication failed - token not found or invalid")
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = user_sessions[session_token]
    print(f"✓ User authenticated: {session['username']}")
    return {
        "user_id": session["user_id"],
        "username": session["username"],
        "authenticated": True
    }

@app.post("/auth/logout")
async def logout(request: Request):
    """Logout user."""
    session_token = request.cookies.get("session_token")

    if session_token and session_token in user_sessions:
        del user_sessions[session_token]

    response = JSONResponse({"message": "Logged out"})
    response.delete_cookie("session_token")
    return response

@app.get("/debug/sessions")
async def debug_sessions():
    """Debug endpoint to see active sessions."""
    return {
        "active_sessions": len(user_sessions),
        "sessions": [
            {
                "token": token[:8] + "...",
                "user_id": data["user_id"],
                "username": data["username"],
                "created_at": data["created_at"]
            }
            for token, data in user_sessions.items()
        ]
    }

# Debug counter to see if callback is being hit
callback_attempts = 0

@app.get("/debug/callback-test")
async def callback_test():
    """Test if callback URL is reachable."""
    global callback_attempts
    callback_attempts += 1
    return {
        "message": "Callback test endpoint reached",
        "attempts": callback_attempts,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

if __name__ == "__main__":
    print("Starting Clean Discord OAuth Backend...")
    uvicorn.run(app, host="0.0.0.0", port=8000)