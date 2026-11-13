"""
Configuration settings for the E-Commerce application.
All application-wide constants and configuration values are defined here.
"""

import os

# --------------------------------------------------------------------------
# Base directory — used to resolve relative paths (e.g. the SQLite file)
# --------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# --------------------------------------------------------------------------
# Serverless detection
# Vercel (like most serverless hosts) mounts the deployment read-only apart
# from /tmp, so anything the app writes to has to live there.
# --------------------------------------------------------------------------
IS_SERVERLESS = bool(os.environ.get('VERCEL'))

# --------------------------------------------------------------------------
# Secret key — used by Flask to sign session cookies and flash messages
# In production this MUST come from an environment variable.
# --------------------------------------------------------------------------
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------
DATABASE_PATH = os.environ.get('DATABASE_PATH') or (
    os.path.join('/tmp', 'ecommerce.db') if IS_SERVERLESS
    else os.path.join(BASE_DIR, 'ecommerce.db')
)

# --------------------------------------------------------------------------
# Upload settings for product images
# --------------------------------------------------------------------------
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or (
    os.path.join('/tmp', 'uploads') if IS_SERVERLESS
    else os.path.join(BASE_DIR, 'static', 'images')
)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2 MB max upload size

# --------------------------------------------------------------------------
# Application settings
# --------------------------------------------------------------------------
DEBUG = os.environ.get('DEBUG', '0' if IS_SERVERLESS else '1') == '1'
ITEMS_PER_PAGE = 12
