# GoDaddy cPanel Application Manager Setup Guide

This guide explains how to deploy ABA using GoDaddy's **cPanel Application Manager** interface (instead of manual Passenger configuration).

## What is Application Manager?

GoDaddy's cPanel includes **Application Manager** (previously called "Setup Python App") which:
- ✅ Automatically configures Passenger
- ✅ Creates and manages virtual environments
- ✅ Handles Python version selection
- ✅ Generates the necessary `.htaccess` file
- ✅ Provides a GUI for managing the application

**No need to manually configure Passenger** - cPanel does it for you!

---

## Prerequisites

1. **GoDaddy Linux cPanel hosting account**
2. **SSH access enabled** (for initial file upload)
3. **Python 3.9+** available in cPanel
4. **OpenRouter API key** (from https://openrouter.ai/keys)

---

## Deployment Steps

### Step 1: Upload Application Files

#### Option A: Via Git (Recommended)

```bash
# SSH into your cPanel server
ssh username@singularsys.com

# Navigate to home directory
cd ~

# Clone the repository
git clone https://github.com/nathanfunk/aba.git aba-app
cd aba-app

# Create environment file
cp .env.example .env
nano .env  # Add your OPENROUTER_API_KEY
```

#### Option B: Via File Manager

1. Log into cPanel
2. Navigate to **Files → File Manager**
3. Upload the application files to `~/aba-app/`
4. Extract if uploaded as a ZIP file

---

### Step 2: Configure Python Application in cPanel

1. **Log into cPanel**
   - Go to https://singularsys.com:2083 (or your cPanel URL)

2. **Find Application Manager**
   - Search for "Python" in the search bar
   - Click **"Setup Python App"** or **"Application Manager"**

3. **Create New Application**
   Click the **"Create Application"** button

4. **Configure Application Settings:**

   | Field | Value |
   |-------|-------|
   | **Python Version** | 3.11 or latest available |
   | **Application Root** | `/home/username/aba-app` |
   | **Application URL** | `singularsys.com/aba` or leave blank for domain root |
   | **Application Startup File** | `passenger_wsgi.py` |
   | **Application Entry Point** | `application` |

5. **Click "Create"**

   cPanel will:
   - Create a virtual environment
   - Generate `.htaccess` file
   - Configure Passenger
   - Set up the application

---

### Step 3: Install Dependencies

After creating the application, you'll see a command to activate the virtual environment.

1. **In the Application Manager interface:**
   - Copy the command shown (looks like `source /home/username/virtualenv/aba-app/3.11/bin/activate`)

2. **SSH into your server:**

   ```bash
   ssh username@singularsys.com
   cd ~/aba-app

   # Activate the virtual environment (use the command from cPanel)
   source /home/username/virtualenv/aba-app/3.11/bin/activate

   # Install dependencies
   pip install --upgrade pip
   pip install -e .
   ```

3. **Verify installation:**

   ```bash
   pip list | grep fastapi
   pip list | grep asgiref
   ```

   You should see `fastapi` and `asgiref` in the list.

---

### Step 4: Build the Frontend

```bash
# Still in SSH, with virtualenv activated
cd ~/aba-app/web-ui

# Install Node.js dependencies (if Node.js is available)
npm install

# Build the frontend
npm run build
```

**Note:** If Node.js is not available on the server, build locally and upload:

```bash
# On your local machine
cd web-ui
npm install
npm run build

# Upload src/aba/web/static/ to server via SFTP or File Manager
```

---

### Step 5: Configure Environment Variables

You can set environment variables in Application Manager or via `.env` file.

#### Option A: Via cPanel Application Manager

1. In Application Manager, click on your application
2. Scroll to **"Environment Variables"** section
3. Add:
   - `OPENROUTER_API_KEY` = `your_api_key_here`
   - `PRODUCTION` = `true`
   - `ABA_HOME` = `/home/username/.aba`

#### Option B: Via .env File (Already done in Step 1)

The `passenger_wsgi.py` file automatically loads `.env`:

```bash
# SSH into server
cd ~/aba-app
nano .env
```

Add:
```
OPENROUTER_API_KEY=your_actual_api_key_here
PRODUCTION=true
ABA_HOME=/home/username/.aba
LOG_LEVEL=INFO
```

---

### Step 6: Restart the Application

In **cPanel Application Manager**:
1. Click on your application
2. Click the **"Restart"** button

Or via SSH:
```bash
cd ~/aba-app
mkdir -p tmp
touch tmp/restart.txt
```

---

### Step 7: Configure Application URL (Optional)

If you want the app accessible at `https://singularsys.com/aba`:

1. **In Application Manager:**
   - Set **Application URL** to `/aba`

2. **Or manually edit .htaccess:**

   ```bash
   cd ~/aba-app
   nano .htaccess
   ```

   Ensure it contains:
   ```apache
   PassengerBaseURI /aba
   PassengerAppRoot /home/username/aba-app
   ```

3. **Create symbolic link in public_html:**

   ```bash
   cd ~/public_html
   ln -s ~/aba-app aba
   ```

---

### Step 8: Test the Application

1. **Visit your website:**
   - `https://singularsys.com/aba` (if configured with URL)
   - Or `https://singularsys.com` (if domain root)

2. **Check it loads:**
   - React frontend should appear
   - Click on an agent
   - Test sending a chat message

3. **Verify WebSocket:**
   - Open browser console (F12)
   - Look for `[WebSocket] Connected` messages
   - Test streaming chat responses

---

## Troubleshooting

### Application Not Starting

**Symptom:** 500 Internal Server Error

**Check:**
1. **View error log in cPanel:**
   - Application Manager → Your App → View Logs

2. **Or via SSH:**
   ```bash
   cd ~/aba-app
   cat logs/error_log
   cat tmp/passenger.log
   ```

**Common issues:**
- Wrong Python version selected
- Missing dependencies (`pip install -e .`)
- Wrong application startup file path
- Missing `.env` file with API key

### Dependencies Not Installing

**Symptom:** `ModuleNotFoundError` when accessing site

**Solution:**
```bash
ssh username@singularsys.com
cd ~/aba-app

# Activate virtualenv (get command from cPanel Application Manager)
source /home/username/virtualenv/aba-app/3.11/bin/activate

# Reinstall
pip install --upgrade pip
pip install -e .

# Verify
python -c "import fastapi; print(fastapi.__version__)"
python -c "import asgiref; print(asgiref.__version__)"

# Restart
touch tmp/restart.txt
```

### Frontend Not Loading

**Symptom:** Blank page or 404 on assets

**Check:**
```bash
cd ~/aba-app/src/aba/web/static
ls -la
```

**Should see:**
- `index.html`
- `assets/` directory with JS/CSS files

**If missing:**
```bash
cd ~/aba-app/web-ui
npm run build
```

### WebSocket Not Working

**Symptom:** Chat doesn't stream, connection errors

**Solutions:**

1. **Check CloudFlare (if using):**
   - CloudFlare dashboard → Network
   - Enable WebSocket support

2. **Check .htaccess:**
   ```apache
   # Should NOT have these (they break WebSockets):
   # RequestHeader unset Upgrade
   # RequestHeader unset Connection
   ```

3. **Verify Passenger config:**
   - Application Manager should handle this automatically
   - Check that `PassengerAppType` is set correctly

### Permission Errors

**Symptom:** Can't write files, access denied

**Fix permissions:**
```bash
cd ~/aba-app
chmod -R 755 .
chmod 644 passenger_wsgi.py
chmod 644 .htaccess
```

---

## Understanding the Generated Configuration

When you create an app in Application Manager, cPanel generates:

### 1. Virtual Environment

Location: `/home/username/virtualenv/aba-app/3.11/`

This is isolated from system Python and other apps.

### 2. .htaccess File

cPanel creates this in your application root:

```apache
PassengerAppRoot /home/username/aba-app
PassengerBaseURI /aba
PassengerPython /home/username/virtualenv/aba-app/3.11/bin/python
PassengerAppType wsgi
PassengerStartupFile passenger_wsgi.py
```

**Our `passenger_wsgi.py` works with this** because:
- It exports `application` variable
- Uses `asgiref` to convert ASGI → WSGI
- Loads environment variables
- Sets up Python path

### 3. Passenger Configuration

Application Manager configures Passenger with sensible defaults:
- Auto-restart on code changes
- Process management
- Memory limits
- Request handling

---

## Updating the Application

### Method 1: Via Git (Recommended)

```bash
ssh username@singularsys.com
cd ~/aba-app
git pull origin main
source /home/username/virtualenv/aba-app/3.11/bin/activate
pip install -e .  # Update dependencies if needed
touch tmp/restart.txt
```

### Method 2: Via CI/CD (Automatic)

The GitHub Actions workflow will automatically:
1. Deploy on push to `main` branch
2. Install dependencies
3. Restart the application

Just ensure GitHub secrets are configured correctly.

### Method 3: Via File Manager

1. Upload changed files via cPanel File Manager
2. Click "Restart" in Application Manager

---

## Environment Variables

### Setting via Application Manager

1. Click on your application
2. Scroll to **Environment Variables**
3. Add/edit variables:
   - `OPENROUTER_API_KEY`
   - `PRODUCTION`
   - `LOG_LEVEL`
4. Click "Save"
5. Restart application

### Setting via .env File

```bash
ssh username@singularsys.com
cd ~/aba-app
nano .env
```

Edit:
```bash
OPENROUTER_API_KEY=sk-or-v1-...
PRODUCTION=true
ABA_HOME=/home/username/.aba
LOG_LEVEL=INFO
```

Save and restart:
```bash
touch tmp/restart.txt
```

---

## Performance Optimization

### In Application Manager

1. Click on your application
2. Configure:
   - **Processes:** 2-4 (depending on your plan)
   - **Threads:** 4-8
   - **Startup timeout:** 300 seconds
   - **Restart:** Enable automatic restart

### In .env File

```bash
# Reduce logging in production
LOG_LEVEL=WARNING

# Production mode
PRODUCTION=true
```

---

## Monitoring

### Via Application Manager

1. Click on your application
2. View:
   - **Status:** Running/Stopped
   - **CPU Usage:** Current usage
   - **Memory:** Current usage
   - **Logs:** Recent errors and access logs

### Via SSH

```bash
# Application logs
tail -f ~/aba-app/logs/app.log

# Error log
tail -f ~/aba-app/logs/error_log

# Restart log
cat ~/aba-app/tmp/passenger.log
```

---

## CI/CD Integration

The GitHub Actions workflow works seamlessly with Application Manager:

1. **Workflow deploys files** via rsync
2. **Updates dependencies** via pip
3. **Touches restart.txt** to trigger restart
4. **Application Manager detects change** and restarts

**No additional configuration needed** - Application Manager handles it automatically!

---

## Quick Reference

### Common Tasks

| Task | Command |
|------|---------|
| **Restart app** | `touch ~/aba-app/tmp/restart.txt` |
| **View logs** | `tail -f ~/aba-app/logs/app.log` |
| **Activate venv** | `source /home/username/virtualenv/aba-app/3.11/bin/activate` |
| **Install deps** | `cd ~/aba-app && pip install -e .` |
| **Update code** | `cd ~/aba-app && git pull` |
| **Build frontend** | `cd ~/aba-app/web-ui && npm run build` |

### Important Paths

- **App root:** `/home/username/aba-app/`
- **Virtual env:** `/home/username/virtualenv/aba-app/3.11/`
- **Agent data:** `/home/username/.aba/`
- **Logs:** `/home/username/aba-app/logs/`
- **Static files:** `/home/username/aba-app/src/aba/web/static/`

---

## Differences from Manual Passenger Setup

| Aspect | Manual Setup | Application Manager |
|--------|-------------|---------------------|
| **Configuration** | Manual .htaccess editing | GUI-based configuration |
| **Virtual env** | Create manually | Auto-created by cPanel |
| **Python version** | Set in .htaccess | Select in GUI |
| **Restart** | `touch tmp/restart.txt` | GUI button or `touch` |
| **Logs** | SSH only | GUI and SSH |
| **Updates** | Manual only | GUI, SSH, or CI/CD |

**Recommendation:** Use Application Manager for initial setup, then manage via Git/CI/CD.

---

## Security Best Practices

1. **Never commit .env file**
   - Already in `.gitignore`
   - Contains API keys

2. **Use environment variables in Application Manager**
   - More secure than `.env` file
   - Managed through cPanel

3. **Keep dependencies updated**
   ```bash
   pip install --upgrade -U pip
   pip install --upgrade -U -e .
   ```

4. **Monitor logs regularly**
   - Check for unusual activity
   - Watch for errors

5. **Use HTTPS only**
   - Ensure SSL certificate is installed
   - Force HTTPS in .htaccess if needed

---

## Next Steps

1. ✅ Create application in cPanel Application Manager
2. ✅ Install dependencies via SSH
3. ✅ Build frontend (or upload built files)
4. ✅ Configure environment variables
5. ✅ Test the application
6. ✅ Set up CI/CD GitHub secrets
7. ✅ Push to `main` branch to trigger auto-deployment

---

## Support Resources

- **cPanel Documentation:** https://docs.cpanel.net/
- **GoDaddy Support:** https://www.godaddy.com/help/
- **Application Manager Guide:** Check cPanel docs for your version
- **This project:** See `DEPLOYMENT.md` and `PASSENGER-SETUP.md`

---

## Summary

✅ **Application Manager simplifies deployment** - no manual Passenger config
✅ **GUI-based management** - easy to configure and monitor
✅ **Automatic virtual environment** - cPanel creates and manages it
✅ **Works with CI/CD** - GitHub Actions deploys automatically
✅ **Our passenger_wsgi.py is compatible** - uses ASGI→WSGI adapter

The application should run smoothly with Application Manager handling all the Passenger configuration automatically!
