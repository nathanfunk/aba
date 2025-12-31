# Quick Start: CI/CD Setup for GoDaddy cPanel

This guide provides a streamlined setup process for deploying ABA to GoDaddy cPanel using GitHub Actions.

## Overview

The CI/CD pipeline automatically:
- ✅ Runs tests on every commit
- 🏗️ Builds the React frontend
- 🚀 Deploys to production on push to `main` branch

---

## Setup Checklist

### Step 1: Prepare Your cPanel Server

1. **Enable SSH Access**
   - Log into GoDaddy cPanel
   - Go to **Security → SSH Access**
   - Generate or import SSH key
   - Authorize the key

2. **Configure Python**
   - Go to **Software → Select Python Version**
   - Select **Python 3.11+**
   - Note the Python binary path

3. **Create Application Directory**
   ```bash
   ssh username@singularsys.com
   mkdir -p ~/public_html/aba
   ```

### Step 2: Generate Deployment SSH Key

On your local machine:

```bash
# Generate deployment key
ssh-keygen -t ed25519 -C "github-deploy" -f ~/.ssh/cpanel_deploy

# Display public key
cat ~/.ssh/cpanel_deploy.pub
```

**Action:** Copy the public key and add it to cPanel SSH authorized keys.

### Step 3: Configure GitHub Secrets

Add these secrets in **GitHub → Settings → Secrets and variables → Actions**:

1. **CPANEL_SSH_KEY**
   ```bash
   cat ~/.ssh/cpanel_deploy  # Copy the entire private key
   ```

2. **CPANEL_HOST**
   ```
   singularsys.com
   ```

3. **CPANEL_USER**
   ```
   your_cpanel_username
   ```

4. **CPANEL_PATH**
   ```
   /home/your_cpanel_username/public_html/aba
   ```

### Step 4: Initial Manual Deployment

SSH into your server and run:

```bash
ssh username@singularsys.com
cd ~/public_html/aba

# Clone repository
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git .

# Configure environment
cp .env.example .env
nano .env  # Add OPENROUTER_API_KEY

# Run deployment script
chmod +x deploy.sh
./deploy.sh

# Update .htaccess with your username
nano .htaccess
# Replace USERNAME with your actual cPanel username in these lines:
# PassengerPython /home/USERNAME/virtualenv/aba/venv/bin/python3
# PassengerAppRoot /home/USERNAME/aba
```

### Step 5: Test Deployment

1. Visit `https://singularsys.com/aba`
2. Check that the frontend loads
3. Test the WebSocket chat functionality
4. Verify API docs at `https://singularsys.com/aba/docs`

### Step 6: Enable Automatic Deployments

Push to `main` branch:

```bash
git add .
git commit -m "Enable CI/CD"
git push origin main
```

Monitor deployment:
- Go to **GitHub → Actions** tab
- Watch the workflow progress
- Check for any errors

---

## Workflow Overview

```
┌─────────────────┐
│  Push to main   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Run Tests     │  ← pytest runs all tests
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Build Frontend  │  ← npm run build
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Deploy to cPanel│  ← rsync + install deps
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Restart App     │  ← touch tmp/restart.txt
└─────────────────┘
```

---

## File Structure

```
aba/
├── .github/
│   └── workflows/
│       └── deploy.yml          # CI/CD workflow
├── src/aba/
│   └── web/
│       └── static/             # Built frontend (deployed)
├── web-ui/                     # React source (not deployed)
├── passenger_wsgi.py           # WSGI entry point
├── .htaccess                   # Passenger configuration
├── deploy.sh                   # Deployment script
├── .env.example                # Environment template
└── .env                        # Environment variables (not in git)
```

---

## Configuration Files

### `.github/workflows/deploy.yml`

GitHub Actions workflow that:
- Runs on push to any branch (tests + build)
- Deploys only on push to `main`
- Uses secrets for SSH authentication
- Excludes unnecessary files from deployment

### `passenger_wsgi.py`

WSGI entry point that:
- Sets up Python path
- Activates virtual environment
- Loads environment variables
- Exports FastAPI app as `application`

### `.htaccess`

Apache/Passenger configuration that:
- Enables Passenger for Python WSGI
- Sets Python interpreter path
- Configures startup timeout
- Enables compression and caching

### `deploy.sh`

Deployment script that:
- Creates virtual environment
- Installs dependencies
- Sets up .env file
- Creates necessary directories
- Restarts application

---

## Common Issues & Solutions

### ❌ SSH Connection Failed

**Error:** `Permission denied (publickey)`

**Solution:**
1. Verify `CPANEL_SSH_KEY` contains the complete private key
2. Ensure public key is in cPanel authorized keys
3. Test SSH connection manually: `ssh -i ~/.ssh/cpanel_deploy username@singularsys.com`

### ❌ Deployment Path Not Found

**Error:** `rsync: failed to stat destination`

**Solution:**
1. Create the directory: `ssh username@singularsys.com 'mkdir -p ~/public_html/aba'`
2. Verify `CPANEL_PATH` secret is correct

### ❌ Frontend Not Loading

**Error:** 404 on assets or blank page

**Solution:**
1. Check that build artifact was uploaded/downloaded in workflow
2. Verify `src/aba/web/static/` contains built files
3. Rebuild frontend manually if needed

### ❌ Application Not Restarting

**Error:** Changes not reflected after deployment

**Solution:**
```bash
ssh username@singularsys.com
cd ~/public_html/aba
mkdir -p tmp
touch tmp/restart.txt
```

---

## Testing the Pipeline

### Test 1: Feature Branch

```bash
git checkout -b test-feature
echo "# Test" >> README.md
git commit -am "Test CI"
git push origin test-feature
```

**Expected:** Tests run, frontend builds, but NO deployment

### Test 2: Main Branch

```bash
git checkout main
git merge test-feature
git push origin main
```

**Expected:** Tests run, frontend builds, AND deployment to cPanel

---

## Monitoring

### GitHub Actions Logs

```
GitHub → Your Repo → Actions → CI/CD Pipeline
```

View logs for:
- Test results
- Build output
- Deployment progress
- Any errors

### Server Logs

```bash
ssh username@singularsys.com
cd ~/public_html/aba

# Application errors
cat logs/app.log

# Passenger errors
cat tmp/error_log

# Follow logs in real-time
tail -f logs/app.log
```

---

## Security Notes

1. **Private Key Security**
   - NEVER commit private keys to Git
   - Store only in GitHub Secrets
   - Rotate keys if compromised

2. **Environment Variables**
   - `.env` is in `.gitignore`
   - Update secrets in cPanel `.env` file
   - Never expose API keys in logs

3. **SSH Access**
   - Use key-based authentication only
   - Disable password authentication
   - Limit authorized keys to deployment only

---

## Next Steps

- ✅ Set up branch protection rules on `main`
- ✅ Configure status checks (require tests to pass)
- ✅ Add deployment notifications (Slack, email)
- ✅ Set up staging environment
- ✅ Monitor application performance

---

## Resources

- **Full Deployment Guide:** [DEPLOYMENT.md](DEPLOYMENT.md)
- **GitHub Actions Docs:** https://docs.github.com/en/actions
- **Passenger Docs:** https://www.phusionpassenger.com/docs
- **GoDaddy cPanel:** https://www.godaddy.com/help/cpanel

---

## Getting Help

If you encounter issues:

1. Check the [Troubleshooting section in DEPLOYMENT.md](DEPLOYMENT.md#troubleshooting)
2. Review GitHub Actions logs
3. Check server logs via SSH
4. Verify all secrets are correctly set
5. Test SSH connection manually

---

**Happy Deploying! 🚀**
