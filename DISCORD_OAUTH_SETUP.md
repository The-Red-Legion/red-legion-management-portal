# Discord Developer Portal Setup for OAuth

## 🚨 IMMEDIATE ACTION REQUIRED

Your Discord Application needs to be updated with the correct redirect URIs for `dev.redlegion.gg`.

## Step-by-Step Instructions

### 1. Go to Discord Developer Portal
- Visit: https://discord.com/developers/applications
- Log in with your Discord account
- Find your application (should be named something like "Red Legion" or similar)

### 2. Update OAuth2 Settings

**In your Discord Application:**

1. Click on "OAuth2" in the left sidebar
2. In the **"Redirects"** section, add these URLs:

```
https://dev.redlegion.gg/auth/discord/callback
http://dev.redlegion.gg/auth/discord/callback
http://localhost:8000/auth/discord/callback
https://localhost:8000/auth/discord/callback
```

3. **Remove any URLs with IP addresses** like:
   - `http://34.28.1.154/auth/discord/callback`
   - Any other IP-based URLs

4. Make sure these **OAuth2 Scopes** are selected:
   - ✅ `identify`
   - ✅ `guilds`

### 3. Verify Your Current Settings

Your Discord application should show:
- **Client ID:** `1411784517655461978` (matches your .env)
- **Client Secret:** `SGzor2kgR_XrdkOIg1-P3YehiwNr8mrm` (matches your .env)
- **Redirect URIs:** The URLs listed above

### 4. Test the OAuth Flow

After updating Discord:

1. **Deploy your changes:** Push your code and let GitHub Actions deploy
2. **Test OAuth:** Go to `https://dev.redlegion.gg/auth/login`
3. **Verify redirect:** After Discord login, you should be redirected to `https://dev.redlegion.gg/events`

## 🔍 Troubleshooting

### If you get "redirect_uri_mismatch":
- Double-check that the Discord app has exactly: `https://dev.redlegion.gg/auth/discord/callback`
- Make sure there are no extra spaces or characters

### If you get "invalid_client":
- Verify your CLIENT_ID and CLIENT_SECRET match exactly
- Make sure the Discord app is not deleted or suspended

### If OAuth works but redirects to wrong page:
- The code now redirects to `/events` instead of `/` after successful login

## 🔐 Security Note

The current .env file has hardcoded secrets. In production, these should come from:
- Environment variables
- Google Cloud Secret Manager
- GitHub Secrets

The secrets are only for development - production will use proper secret management.

## Expected Behavior After Fix

1. User visits `https://dev.redlegion.gg`
2. Clicks login → redirects to Discord
3. User authorizes → Discord redirects to `https://dev.redlegion.gg/auth/discord/callback`
4. Backend processes OAuth → redirects to `https://dev.redlegion.gg/events`
5. User sees events page while logged in