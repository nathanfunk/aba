# Deployment Guide: GoDaddy cPanel Hosting

This guide explains how to deploy the ABA (Agent Builder) project to GoDaddy Linux cPanel web hosting with CI/CD using GitHub Actions.

> **💡 Quick Start:** For most users, we recommend using **cPanel's Application Manager** interface for easier deployment. See [CPANEL-APPLICATION-MANAGER.md](CPANEL-APPLICATION-MANAGER.md) for GUI-based setup instructions. This guide covers the manual/advanced approach.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [GitHub Secrets Configuration](#github-secrets-configuration)
4. [Manual Deployment](#manual-deployment)
5. [CI/CD Deployment](#cicd-deployment)
6. [Troubleshooting](#troubleshooting)
7. [Maintenance](#maintenance)

---

## Prerequisites

### On Your Local Machine
- Git installed
- GitHub account with repository access
- SSH client

### On GoDaddy cPanel
- Linux hosting plan with SSH access
- Python 3.11+ support (check cPanel Python Selector)
- Passenger (mod_passenger) enabled
- Node.js 20+ (for building frontend)

### API Keys
- OpenRouter API key (get from https://openrouter.ai/keys)

---

## Initial Setup

### 1. Enable SSH Access in cPanel

1. Log into your GoDaddy cPanel
2. Navigate to **Security → SSH Access**
3. Click **Manage SSH Keys**
4. Generate a new SSH key pair or import your existing public key
5. Authorize the key for SSH access

### 2. Generate SSH Key for GitHub Actions

On your local machine:

```bash
# Generate a new SSH key pair for deployment
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/cpanel_deploy

# Display the public key
cat ~/.ssh/cpanel_deploy.pub
```

**Important:** Copy the public key and add it to your cPanel SSH authorized keys.

### 3. Configure Python Version in cPanel

1. In cPanel, navigate to **Software → Select Python Version**
2. Select **Python 3.11** (or latest available)
3. Note the path to the Python binary (you'll need this for `.htaccess`)

---

## GitHub Secrets Configuration

Add the following secrets to your GitHub repository:

**Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `CPANEL_SSH_KEY` | Private SSH key for deployment | Contents of `~/.ssh/cpanel_deploy` |
| `CPANEL_HOST` | cPanel server hostname | `singularsys.com` or IP address |
| `CPANEL_USER` | cPanel username | `username` |
| `CPANEL_PATH` | Path to application directory | `/home/username/public_html/aba` |

### Setting the Secrets

```bash
# Example: Setting CPANEL_SSH_KEY
# Copy the ENTIRE private key including BEGIN and END lines
cat ~/.ssh/cpanel_deploy
```

Then paste into GitHub:
1. Go to: https://github.com/YOUR_USERNAME/YOUR_REPO/settings/secrets/actions
2. Click "New repository secret"
3. Name: `CPANEL_SSH_KEY`
4. Value: Paste the entire private key
5. Click "Add secret"

Repeat for `CPANEL_HOST`, `CPANEL_USER`, and `CPANEL_PATH`.

---

## Manual Deployment

### First-Time Setup on Server

SSH into your cPanel server:

```bash
ssh username@singularsys.com
```

Create and navigate to application directory:

```bash
cd ~/public_html
mkdir -p aba
cd aba
```

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git .
```

Copy and configure environment file:

```bash
cp .env.example .env
nano .env  # Edit and add your OPENROUTER_API_KEY
```

Run the deployment script:

```bash
chmod +x deploy.sh
./deploy.sh
```

### Configure .htaccess

Edit the `.htaccess` file to match your cPanel configuration:

```bash
nano .htaccess
```

Update these lines with your actual paths:

```apache
# Replace USERNAME with your cPanel username
PassengerPython /home/USERNAME/virtualenv/aba/venv/bin/python3
PassengerAppRoot /home/USERNAME/aba
```

### Test the Application

Visit your website:
- Main site: `https://singularsys.com/aba`
- API docs: `https://singularsys.com/aba/docs`

---

## CI/CD Deployment

### How It Works

The GitHub Actions workflow (`.github/workflows/deploy.yml`) automatically:

1. **On every push to any branch:**
   - Runs Python tests
   - Builds React frontend

2. **On push to `main` branch only:**
   - Deploys code to cPanel via rsync
   - Installs Python dependencies
   - Restarts the application

### Triggering a Deployment

Simply push to the main branch:

```bash
git add .
git commit -m "Update application"
git push origin main
```

Or merge a pull request into `main`.

### Monitoring Deployments

1. Go to your GitHub repository
2. Click **Actions** tab
3. View the latest workflow run
4. Check logs for any errors

### Manual Workflow Trigger

You can also manually trigger a deployment:

1. Go to **Actions** tab in GitHub
2. Select **CI/CD Pipeline** workflow
3. Click **Run workflow**
4. Select `main` branch
5. Click **Run workflow**

---

## Troubleshooting

### Application Not Starting

**Check Passenger logs:**
```bash
ssh username@singularsys.com
cd ~/public_html/aba
cat tmp/error_log
```

**Check application logs:**
```bash
cd ~/public_html/aba
cat logs/app.log
```

**Restart the application:**
```bash
cd ~/public_html/aba
mkdir -p tmp
touch tmp/restart.txt
```

### Python Import Errors

Ensure virtual environment is set up correctly:

```bash
ssh username@singularsys.com
cd ~/public_html/aba
source venv/bin/activate
pip install -e .
```

### Frontend Not Loading

Build the frontend manually:

```bash
ssh username@singularsys.com
cd ~/public_html/aba/web-ui
npm install
npm run build
```

### WebSocket Connection Issues

1. Check that WebSocket is enabled in cPanel
2. Verify your GoDaddy plan supports WebSockets
3. Check browser console for connection errors
4. Ensure CORS is properly configured in `src/aba/web/server.py`

### Permission Errors

Fix file permissions:

```bash
ssh username@singularsys.com
cd ~/public_html/aba
chmod -R 755 .
chmod 644 .htaccess
chmod 644 passenger_wsgi.py
```

### CI/CD Deployment Fails

**SSH connection issues:**
- Verify `CPANEL_SSH_KEY` secret contains the complete private key
- Ensure the corresponding public key is in cPanel authorized keys
- Check `CPANEL_HOST` and `CPANEL_USER` are correct

**Permission denied during rsync:**
- Ensure `CPANEL_PATH` directory exists and is writable
- Check SSH key has proper permissions on the server

**Python installation fails:**
- Verify Python 3.11+ is available in cPanel Python Selector
- Check that virtual environment was created successfully

---

## Maintenance

### Updating Environment Variables

```bash
ssh username@singularsys.com
cd ~/public_html/aba
nano .env
# Make changes
touch tmp/restart.txt  # Restart application
```

### Viewing Application Logs

```bash
ssh username@singularsys.com
cd ~/public_html/aba
tail -f logs/app.log
```

### Checking Application Status

```bash
ssh username@singularsys.com
cd ~/public_html/aba
passenger-status
```

### Database/Storage Management

The application stores agent data in `~/.aba/`:

```bash
# Backup agent data
cd ~
tar -czf aba-backup-$(date +%Y%m%d).tar.gz .aba/

# Restore agent data
tar -xzf aba-backup-YYYYMMDD.tar.gz
```

### Updating Dependencies

```bash
ssh username@singularsys.com
cd ~/public_html/aba
source venv/bin/activate
pip install --upgrade -r requirements.txt
touch tmp/restart.txt
```

---

## Security Best Practices

1. **Never commit `.env` file** - It's in `.gitignore` for a reason
2. **Rotate API keys regularly** - Update in `.env` and restart
3. **Keep dependencies updated** - Regularly update Python packages
4. **Monitor access logs** - Check for unusual activity
5. **Use HTTPS only** - Ensure SSL certificate is installed
6. **Limit SSH access** - Use key-based authentication only

---

## Performance Optimization

### Enable Production Mode

In `.env`:
```
PRODUCTION=true
LOG_LEVEL=WARNING
```

### Configure Passenger

Create `.passenger` file:

```ruby
PassengerMaxPoolSize 6
PassengerMinInstances 2
PassengerMaxPreloaderIdleTime 0
```

### Enable Caching

The `.htaccess` file already includes:
- Gzip compression for text files
- Browser caching for static assets
- Security headers

---

## Support and Resources

- **ABA Documentation:** See `README.md` and `CLAUDE.md`
- **GoDaddy cPanel Docs:** https://www.godaddy.com/help/cpanel
- **Passenger Documentation:** https://www.phusionpassenger.com/docs
- **FastAPI Documentation:** https://fastapi.tiangolo.com/
- **GitHub Actions:** https://docs.github.com/en/actions

---

## Quick Reference

### Common Commands

```bash
# Restart application
touch tmp/restart.txt

# View logs
tail -f logs/app.log

# Activate virtual environment
source venv/bin/activate

# Run deployment script
./deploy.sh

# Build frontend
cd web-ui && npm run build

# Check Python version
python3 --version

# Check Git status
git status

# Pull latest changes
git pull origin main
```

### Important Paths

- Application root: `/home/username/public_html/aba`
- Virtual environment: `/home/username/public_html/aba/venv`
- Agent data: `~/.aba/`
- Logs: `/home/username/public_html/aba/logs/`
- Frontend source: `/home/username/public_html/aba/web-ui`
- Built frontend: `/home/username/public_html/aba/src/aba/web/static/`

---

## License

See `LICENSE` file in the repository root.
