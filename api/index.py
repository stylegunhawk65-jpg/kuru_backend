"""Vercel Serverless Function entry point for FastAPI backend."""

import os
import sys

# Ensure project root is in sys.path for serverless runtime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

# Vercel looks for 'app' in api/index.py
