"""
WSGI entry point for Passenger (cPanel) deployment.
This file is used by Passenger to run the FastAPI application.
"""

import sys
import os
from pathlib import Path

# Add the application directory to the Python path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))
sys.path.insert(0, str(app_dir / "src"))

# Set up virtual environment
venv_dir = app_dir / "venv"
if venv_dir.exists():
    # For Python 3.3+, we need to manually set up the virtualenv
    site_packages = venv_dir / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    if site_packages.exists():
        sys.path.insert(0, str(site_packages))

# Load environment variables from .env file
env_file = app_dir / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, _, value = line.partition('=')
                    os.environ.setdefault(key.strip(), value.strip())

# Set default environment variables
os.environ.setdefault('ABA_HOME', os.path.join(os.path.expanduser('~'), '.aba'))
os.environ.setdefault('PRODUCTION', 'true')

# Import the FastAPI application
from aba.web.server import app

# The WSGI application
application = app
