"""
Module: config.py
Purpose: Configuration Layer
Responsibilities: Centralizing environment variables, providing safe fallbacks, 
and ensuring paths are dynamically resolved to prevent hardcoded failures.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

class Config:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    APP_ENV = os.getenv("APP_ENV", "development")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
    
    # Path Resolution (Safe defaults dynamically anchored to BASE_DIR)
    CHROMA_DB_PATH = os.path.join(BASE_DIR, os.getenv("CHROMA_DB_PATH", "chroma"))
    VISTASTREAM_DB_PATH = os.path.join(BASE_DIR, os.getenv("VISTASTREAM_DB_PATH", "databases/vistastream.db"))
    NEONPLAY_DB_PATH = os.path.join(BASE_DIR, os.getenv("NEONPLAY_DB_PATH", "databases/neonplay.db"))

def validate_environment():
    """Validates critical environment configurations at startup."""
    if not Config.GEMINI_API_KEY:
        print("WARNING: GEMINI_API_KEY is missing. Downstream LLM generation logic may fail.")
        
    os.makedirs(os.path.dirname(Config.VISTASTREAM_DB_PATH), exist_ok=True)
    os.makedirs(Config.CHROMA_DB_PATH, exist_ok=True)

validate_environment()
