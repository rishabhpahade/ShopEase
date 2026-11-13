"""
Vercel entry point.

The Python runtime loads this module and looks for a WSGI callable named
`app`. The Flask application lives one directory up, so the project root is
added to sys.path before importing it.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app  # noqa: E402,F401  (exported for @vercel/python)
