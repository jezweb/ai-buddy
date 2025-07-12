# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.absolute()

# Load environment variables from .env file in the AI Buddy directory
load_dotenv(SCRIPT_DIR / '.env')

# IMPORTANT: Create a file named .env in the same directory
# and add your Gemini API key like this:
# GEMINI_API_KEY="YOUR_API_KEY_HERE"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY not found. Please set it in your .env file.\n"
        "1. Copy .env.example to .env\n"
        "2. Add your Gemini API key to the .env file\n"
        "3. Get your API key from: https://makersuite.google.com/app/apikey"
    )

# Optional: Configure model name (can be overridden at runtime)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Optional: Configure session directory (relative to AI Buddy directory)
SESSIONS_DIR = os.getenv("SESSIONS_DIR", str(SCRIPT_DIR / "sessions"))

# Optional: Configure polling interval for monitoring agent (in seconds)
POLLING_INTERVAL = float(os.getenv("POLLING_INTERVAL", "1.0"))

# Smart Context Management
SMART_CONTEXT_ENABLED = os.getenv("SMART_CONTEXT_ENABLED", "true").lower() == "true"
MAX_CONTEXT_SIZE = int(os.getenv("MAX_CONTEXT_SIZE", "100000"))