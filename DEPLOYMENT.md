# Red Legion Website Deployment

This repository includes automated deployment using GitHub Actions and Ansible to deploy the Red Legion website to a GCP compute instance.

## Architecture

- **Frontend**: Vue.js SPA built and served as static files
- **Backend**: FastAPI Python application running on port 8000
- **Database**: PostgreSQL on GCP Cloud SQL
- **Bot Integration**: Internal API calls to Discord bot on port 8001
- **Reverse Proxy**: Nginx for static file serving and API proxying

## Prerequisites

Before deployment, ensure the following GitHub Secrets are configured:

### Required GitHub Secrets

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `WEB_SERVER_HOST` | External IP of the GCP web server instance | `34.123.456.789` |
| `WEB_SERVER_SSH_PRIVATE_KEY` | SSH private key for web server access | `-----BEGIN PRIVATE KEY-----...` |
| `BOT_API_INTERNAL_URL` | Internal URL to Discord bot API | `http://10.128.0.2:8001` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `DISCORD_CLIENT_ID` | Discord OAuth application client ID | `1234567890123456789` |
| `DISCORD_CLIENT_SECRET` | Discord OAuth application client secret | `ABC123...` |
| `DISCORD_REDIRECT_URI` | Discord OAuth redirect URI | `http://WEB_SERVER_HOST/api/auth/discord/callback` |

### Getting the Values

1. **Web Server Info**: Run `terraform output` in the infra repo to get:
   - `web_server_url` → Extract IP for `WEB_SERVER_HOST`
   - `bot_api_internal_url` → Use for `BOT_API_INTERNAL_URL`

2. **SSH Private Key**: Get from GCP Secret Manager:
   ```bash
   gcloud secrets versions access latest --secret="ssh-private-key"
   ```

3. **Database URL**: Get from GCP Secret Manager:
   ```bash
   gcloud secrets versions access latest --secret="database-connection-string"
   ```

4. **Discord OAuth**: From your Discord application in the Discord Developer Portal

## Deployment Process

### Automatic Deployment

Deployment is triggered automatically on:
- Push to `main` or `master` branch
- Manual workflow dispatch

### Manual Deployment

You can also trigger deployment manually:
1. Go to the GitHub repository
2. Navigate to **Actions** tab
3. Select **Deploy Red Legion Website** workflow
4. Click **Run workflow**

## Deployment Steps

The GitHub Action performs the following steps:

1. **Build Frontend**: Compiles Vue.js application
2. **Package Application**: Creates deployment package with backend and frontend
3. **Ansible Deployment**:
   - Updates system packages
   - Installs dependencies (Python, Nginx, PostgreSQL client)
   - Creates application user and directories
   - Deploys application files
   - Sets up Python virtual environment
   - Configures environment variables
   - Creates systemd service for backend
   - Configures Nginx reverse proxy
   - Starts services

## File Structure

```
red-legion-website/
├── .github/workflows/
│   └── deploy.yml           # GitHub Actions workflow
├── ansible/
│   ├── ansible.cfg          # Ansible configuration
│   ├── inventory/
│   │   └── production.yml   # Server inventory
│   └── playbooks/
│       ├── deploy.yml       # Main deployment playbook
│       └── templates/
│           ├── env.j2       # Environment variables template
│           ├── nginx.j2     # Nginx configuration template
│           └── systemd-service.j2  # Systemd service template
├── backend/                 # FastAPI backend code
├── frontend/                # Vue.js frontend code
└── static/                  # Static assets
```

## Server Configuration

### Services

- **Backend Service**: `red-legion-website-backend.service`
  - Runs on port 8000
  - Auto-restart on failure
  - Managed by systemd

- **Nginx**: Reverse proxy on port 80
  - Serves static files directly
  - Proxies API requests to backend
  - Handles Vue.js SPA routing

### File Locations

- **Application**: `/opt/red-legion-website/`
- **Logs**: `journalctl -u red-legion-website-backend`
- **Nginx Config**: `/etc/nginx/sites-available/red-legion-website`

## Monitoring and Maintenance

### Service Status
```bash
sudo systemctl status red-legion-website-backend
sudo systemctl status nginx
```

### View Logs
```bash
sudo journalctl -u red-legion-website-backend -f
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Manual Restart
```bash
sudo systemctl restart red-legion-website-backend
sudo systemctl reload nginx
```

## Troubleshooting

### Common Issues

1. **Service won't start**: Check environment variables in `.env` file
2. **Database connection failed**: Verify database URL and network connectivity
3. **Bot API not accessible**: Ensure bot server is running and firewall allows port 8001
4. **Frontend not loading**: Check Nginx configuration and static file permissions

### Access Application

Once deployed, the application will be available at:
- **Web Interface**: `http://WEB_SERVER_HOST` (port 80)
- **API Docs**: `http://WEB_SERVER_HOST/docs` (FastAPI docs)

## Security Considerations

- All sensitive credentials are stored in GitHub Secrets
- SSH access is key-based only
- Nginx includes security headers
- Rate limiting on authentication endpoints
- Application runs with restricted permissions via systemd