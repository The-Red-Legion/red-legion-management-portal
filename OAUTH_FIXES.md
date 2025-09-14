# Discord OAuth Fixes Required

## 1. Discord Developer Portal Configuration

**In your Discord Application settings:**

- **Redirect URIs:** Add ALL of these:
  ```
  http://localhost:8000/auth/discord/callback
  http://your-production-domain.com/auth/discord/callback
  https://your-production-domain.com/auth/discord/callback
  ```

- **OAuth2 Scopes:** Ensure these are enabled:
  - `identify` (basic user info)
  - `guilds` (user's guild list)

## 2. Environment Variables Fix

**Update your .env files:**
```bash
# Correct the redirect URI
DISCORD_REDIRECT_URI=http://localhost:8000/auth/discord/callback

# For production:
DISCORD_REDIRECT_URI=https://your-domain.com/auth/discord/callback
```

## 3. Add CSRF Protection (Security Fix)

**In backend/main.py**, update the OAuth flow:

```python
import secrets

@app.get("/auth/login")
async def discord_login():
    """Redirect to Discord OAuth."""
    if not DISCORD_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Discord OAuth not configured: Missing DISCORD_CLIENT_ID")
    if not DISCORD_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Discord OAuth not configured: Missing DISCORD_REDIRECT_URI")

    # Generate CSRF state token
    state = secrets.token_urlsafe(32)
    # Store state temporarily (implement session storage)

    discord_auth_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={DISCORD_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify%20guilds"
        f"&state={state}"  # Add CSRF protection
    )

    logger.info(f"Discord OAuth redirect URL: {discord_auth_url}")
    return RedirectResponse(discord_auth_url)

@app.get("/auth/discord/callback")
async def discord_callback(code: str, state: str):
    """Handle Discord OAuth callback."""
    # Validate state parameter against stored value
    # ... rest of your callback logic
```

## 4. Fix Environment Loading

**In backend/main.py**, simplify environment loading:

```python
# Load environment once at startup
load_dotenv()

# Get all config in one place
DATABASE_URL = os.getenv("DATABASE_URL")
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Validate critical config at startup
if not DISCORD_CLIENT_ID:
    raise ValueError("DISCORD_CLIENT_ID environment variable required")
if not DISCORD_CLIENT_SECRET:
    raise ValueError("DISCORD_CLIENT_SECRET environment variable required")
if not DISCORD_REDIRECT_URI:
    raise ValueError("DISCORD_REDIRECT_URI environment variable required")
```

## 5. CORS Configuration

**Add proper CORS setup:**

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vue.js dev server
        "http://localhost:3000",
        "https://your-production-domain.com"
    ],
    allow_credentials=True,  # Required for cookies
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

## 6. Debug OAuth Flow

**Add detailed logging:**

```python
@app.get("/auth/discord/callback")
async def discord_callback(code: str, state: str = None):
    """Handle Discord OAuth callback."""
    try:
        logger.info(f"OAuth callback - Code: {code[:10]}..., State: {state}")
        logger.info(f"Using CLIENT_ID: {DISCORD_CLIENT_ID}")
        logger.info(f"Using REDIRECT_URI: {DISCORD_REDIRECT_URI}")

        # Your token exchange logic...

    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")
```

## Testing Steps

1. **Update Discord App settings** with correct redirect URIs
2. **Set environment variables** correctly
3. **Test locally:** `http://localhost:8000/auth/login`
4. **Check logs** for detailed error messages
5. **Verify redirect URI** matches exactly what Discord expects

## Common Error Messages

- `"invalid_client"` = Wrong CLIENT_ID or CLIENT_SECRET
- `"redirect_uri_mismatch"` = Redirect URI doesn't match Discord app settings
- `"invalid_grant"` = Authorization code expired or already used
- `"access_denied"` = User denied authorization

Try these fixes first, then we can address the broader architecture issues.