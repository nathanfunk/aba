# Passenger Setup Guide for FastAPI on cPanel

This guide explains how FastAPI (an ASGI framework) runs on GoDaddy cPanel using Passenger.

## Understanding the Architecture

### The Challenge

- **FastAPI** uses **ASGI** (Asynchronous Server Gateway Interface)
- **cPanel Passenger** traditionally supports **WSGI** (Web Server Gateway Interface)
- We need a bridge between the two

### The Solution

We support **two deployment modes**:

#### Mode 1: WSGI Mode (Default - Compatible with all Passenger versions)

```
Browser → Apache → Passenger → WSGI Adapter → FastAPI (ASGI)
```

Uses `asgiref.wsgi.WsgiToAsgi` to convert ASGI to WSGI.

**Pros:**
- ✅ Works on all Passenger versions
- ✅ Compatible with older cPanel installations
- ✅ Reliable and battle-tested

**Cons:**
- ⚠️ Slightly lower performance
- ⚠️ Some ASGI features may be limited (WebSockets work fine)

#### Mode 2: ASGI Mode (Passenger 6.0+ only)

```
Browser → Apache → Passenger 6.0+ → FastAPI (ASGI) [native]
```

Passenger directly runs the ASGI application.

**Pros:**
- ✅ Better performance
- ✅ Full ASGI feature support
- ✅ Native async/await handling

**Cons:**
- ⚠️ Requires Passenger 6.0+
- ⚠️ May not be available on all GoDaddy plans

---

## Current Setup

### Default Configuration (WSGI Mode)

**Files:**
- `passenger_wsgi.py` - Uses `asgiref.wsgi.WsgiToAsgi` adapter
- `.htaccess` - Configured for `PassengerAppType wsgi`
- `pyproject.toml` - Includes `asgiref>=3.7.0` dependency

**How it works:**

1. Passenger loads `passenger_wsgi.py`
2. The script imports the FastAPI app
3. `WsgiToAsgi` wraps the ASGI app for WSGI compatibility
4. Passenger serves the wrapped application

**Code in `passenger_wsgi.py`:**

```python
from aba.web.server import app
from asgiref.wsgi import WsgiToAsgi

# Convert ASGI to WSGI
application = WsgiToAsgi(app)
```

**`.htaccess` configuration:**

```apache
PassengerAppType wsgi
PassengerStartupFile passenger_wsgi.py
```

---

## Checking Your Passenger Version

SSH into your cPanel server and run:

```bash
passenger-config --version
```

**Example output:**
```
Phusion Passenger 6.0.19
```

- **Version < 6.0:** Use WSGI mode (default)
- **Version >= 6.0:** Can use ASGI mode (optional upgrade)

---

## Switching to ASGI Mode (Passenger 6.0+)

If you have Passenger 6.0+, you can enable native ASGI support:

### Step 1: Check Passenger Version

```bash
ssh username@singularsys.com
passenger-config --version
```

### Step 2: Update .htaccess

Replace `.htaccess` with `.htaccess.asgi`:

```bash
cd ~/public_html/aba
cp .htaccess .htaccess.wsgi.backup
cp .htaccess.asgi .htaccess
nano .htaccess  # Update USERNAME paths
```

**Key changes:**

```apache
PassengerAppType asgi  # Changed from wsgi
PassengerAppGroupName aba_app  # Optional: isolate app
PassengerMinInstances 2  # Optional: performance tuning
```

### Step 3: Update passenger_wsgi.py (Optional)

For pure ASGI mode, simplify `passenger_wsgi.py`:

```python
from aba.web.server import app

# Direct ASGI export (Passenger 6.0+ only)
application = app
```

### Step 4: Restart Application

```bash
mkdir -p tmp
touch tmp/restart.txt
```

### Step 5: Verify

Visit your application and check logs:

```bash
cat tmp/error_log
```

**Expected:** No errors about ASGI/WSGI incompatibility

---

## How the Backend Runs

### Request Flow

```
User Browser
     ↓
[HTTPS Request]
     ↓
Apache Web Server (Port 443)
     ↓
mod_passenger (Passenger Module)
     ↓
Python Application (passenger_wsgi.py)
     ↓
┌─────────────────────────────────┐
│  WSGI Mode        ASGI Mode     │
│     ↓                 ↓          │
│  WsgiToAsgi      Direct         │
│     ↓                 ↓          │
│  FastAPI App    FastAPI App     │
└─────────────────────────────────┘
     ↓
[Response]
     ↓
User Browser
```

### Application Lifecycle

1. **Startup:**
   - Passenger detects `.htaccess` configuration
   - Loads Python from virtual environment path
   - Executes `passenger_wsgi.py`
   - Imports FastAPI app and dependencies
   - Starts serving requests

2. **Request Handling:**
   - Apache receives HTTP request
   - Routes to Passenger based on `.htaccess`
   - Passenger forwards to Python application
   - FastAPI processes request (async/await)
   - Response sent back through Passenger → Apache

3. **Restart:**
   - Create/touch `tmp/restart.txt`
   - Passenger detects file change
   - Gracefully restarts application
   - New requests use updated code

### Process Management

**Passenger automatically handles:**
- Process spawning (multiple workers)
- Load balancing across workers
- Process recycling (after max requests)
- Memory management
- Crash recovery
- Idle process shutdown

**Configuration in `.htaccess`:**

```apache
PassengerMinInstances 2      # Keep 2 processes always running
PassengerMaxPoolSize 6       # Max 6 processes
PassengerMaxRequests 1000    # Recycle after 1000 requests
```

---

## WebSocket Support

### How WebSockets Work with Passenger

Both WSGI and ASGI modes support WebSockets:

**WSGI Mode:**
- `asgiref.wsgi.WsgiToAsgi` passes through WebSocket connections
- Passenger proxies WebSocket upgrade requests
- Works reliably for chat application

**ASGI Mode:**
- Native WebSocket support
- Better performance for long-lived connections

### Verifying WebSocket Support

1. **Check application logs:**
   ```bash
   tail -f ~/public_html/aba/logs/app.log
   ```

2. **Test WebSocket connection:**
   - Open browser console on `https://singularsys.com/aba`
   - Look for `[WebSocket] Connected to ws://...` messages
   - Send a chat message
   - Verify streaming responses

3. **Common issues:**
   - **CloudFlare:** If using CloudFlare, ensure WebSocket support is enabled
   - **Firewall:** Check that WebSocket ports aren't blocked
   - **Timeout:** Increase `PassengerStartTimeout` if needed

---

## Performance Tuning

### WSGI Mode Optimizations

```apache
# Increase worker processes
PassengerMaxPoolSize 6
PassengerMinInstances 2

# Reduce memory usage
PassengerMaxRequests 1000
PassengerMemoryLimit 512

# Faster startup
PassengerStartTimeout 600
PassengerPreStart https://singularsys.com/aba
```

### ASGI Mode Optimizations

```apache
# All WSGI optimizations plus:
PassengerAppGroupName aba_app
PassengerThreadCount 4
```

### Python Application Tuning

In `.env`:
```bash
# Reduce logging in production
LOG_LEVEL=WARNING

# Enable production mode
PRODUCTION=true

# Limit history size
MAX_HISTORY_MESSAGES=20
```

---

## Troubleshooting

### Application Won't Start

**Symptom:** 500 Internal Server Error

**Check:**

```bash
# View Passenger error log
cat ~/public_html/aba/tmp/error_log

# Check Apache error log (if accessible)
tail -f ~/logs/error_log
```

**Common causes:**
- Missing `asgiref` dependency (WSGI mode)
- Wrong Python path in `.htaccess`
- Missing virtual environment
- Import errors in `passenger_wsgi.py`

### ASGI/WSGI Mismatch

**Symptom:** `AttributeError: 'FastAPI' object has no attribute '__call__'`

**Solution:**

Ensure `.htaccess` matches `passenger_wsgi.py`:

- **WSGI mode:** `PassengerAppType wsgi` + `WsgiToAsgi(app)`
- **ASGI mode:** `PassengerAppType asgi` + `application = app`

### Performance Issues

**Symptom:** Slow responses or timeouts

**Solutions:**

1. **Increase worker processes:**
   ```apache
   PassengerMaxPoolSize 6
   ```

2. **Enable process preloading:**
   ```apache
   PassengerPreStart https://singularsys.com/aba
   ```

3. **Check resource limits:**
   ```bash
   # View current limits
   passenger-status
   passenger-memory-stats
   ```

### WebSocket Disconnects

**Symptom:** Chat works briefly then disconnects

**Solutions:**

1. **Increase timeout:**
   ```apache
   PassengerStartTimeout 600
   ```

2. **Keep connections alive:**
   ```apache
   PassengerMaxPreloaderIdleTime 0
   ```

3. **Check for proxy timeout** (CloudFlare, etc.)

---

## Monitoring

### Check Application Status

```bash
# SSH into server
ssh username@singularsys.com

# View Passenger status
passenger-status

# View memory usage
passenger-memory-stats

# View application logs
tail -f ~/public_html/aba/logs/app.log
```

### View Active Processes

```bash
# List Python processes
ps aux | grep python

# View passenger processes
passenger-status --verbose
```

### Monitor Resource Usage

```bash
# CPU and memory
top

# Disk space
df -h

# Application directory size
du -sh ~/public_html/aba
```

---

## Summary

### Quick Reference

| Aspect | WSGI Mode (Default) | ASGI Mode (6.0+) |
|--------|-------------------|------------------|
| **Passenger Version** | Any version | 6.0+ required |
| **Performance** | Good | Better |
| **WebSockets** | ✅ Supported | ✅ Native |
| **Configuration** | `.htaccess` (wsgi) | `.htaccess.asgi` |
| **Dependency** | `asgiref` required | No adapter needed |
| **Reliability** | Battle-tested | Modern standard |

### Recommended Setup

For most GoDaddy cPanel installations:
- ✅ **Use WSGI mode** (default configuration)
- ✅ Works reliably on all servers
- ✅ Supports all FastAPI features including WebSockets
- ✅ Easy to troubleshoot

---

## Resources

- **Passenger Documentation:** https://www.phusionpassenger.com/docs
- **ASGI Specification:** https://asgi.readthedocs.io/
- **FastAPI Deployment:** https://fastapi.tiangolo.com/deployment/
- **asgiref Library:** https://github.com/django/asgiref

---

For additional help, see [DEPLOYMENT.md](DEPLOYMENT.md) and [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
