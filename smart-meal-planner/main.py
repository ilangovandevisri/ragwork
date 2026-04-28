"""
Entry point — starts the FastAPI backend server.
Run: python main.py
"""

import os
import sys
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to path so all imports resolve correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("Starting Smart Meal Planner API... visit http://localhost:8000/docs")
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
