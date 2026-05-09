import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

class Config:
    # Anchor all paths to the project root
    BASE_DIR = Path(__file__).resolve().parent.parent

    # Environment
    APP_ENV = os.getenv("APP_ENV", "development")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
    
    # Required API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    # Models
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    
    # Path Resolution (Safe defaults dynamically anchored to BASE_DIR)
    CHROMA_DB_PATH = str(BASE_DIR / os.getenv("CHROMA_DB_PATH", "chroma"))
    VISTASTREAM_DB_PATH = str(BASE_DIR / os.getenv("VISTASTREAM_DB_PATH", "databases/vistastream.db"))
    NEONPLAY_DB_PATH = str(BASE_DIR / os.getenv("NEONPLAY_DB_PATH", "databases/neonplay.db"))
    SESSIONS_DB_PATH = str(BASE_DIR / os.getenv("SESSIONS_DB_PATH", "databases/sessions.db"))
    
    # Ensure logs path
    LOG_DIR_PATH = str(BASE_DIR / "logs")

def validate_environment():
    """Validates critical environment configurations at startup."""
    errors = []
    
    # Validate critical variables
    if not Config.GEMINI_API_KEY and Config.APP_ENV == "production":
        errors.append("GEMINI_API_KEY is missing but required for generation.")
        
    # Ensure paths exist
    for path in [
        Path(Config.VISTASTREAM_DB_PATH).parent,
        Path(Config.NEONPLAY_DB_PATH).parent,
        Path(Config.SESSIONS_DB_PATH).parent,
        Path(Config.CHROMA_DB_PATH),
        Path(Config.LOG_DIR_PATH),
    ]:
        path.mkdir(parents=True, exist_ok=True)
        
    if errors:
        print("[CRITICAL] Path validation failed:")
        for err in errors:
            print(f" - {err}")
        sys.exit(1)
        
    if not Config.GEMINI_API_KEY:
        print("[WARNING] GEMINI_API_KEY is missing. LLM-based features will be disabled.")

# Validate on import
validate_environment()
