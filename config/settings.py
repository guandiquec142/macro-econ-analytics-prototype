import os
from dotenv import load_dotenv

load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
BLS_API_KEY = os.getenv("BLS_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

if not FRED_API_KEY:
    raise ValueError("FRED_API_KEY missing from .env")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY missing from .env")
if not BLS_API_KEY:
    raise ValueError("BLS_API_KEY missing from .env")