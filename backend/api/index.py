"""
Serverless entry point for Vercel/cloud deployments.
Exports the main FastAPI app from backend.app.main.
"""
import os
import sys

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.main import app