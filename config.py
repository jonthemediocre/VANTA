# config.py - Centralized Configuration and Environment Variable Loading

import os
from pathlib import Path
from dotenv import load_dotenv
import logging

# --- Load .env file first ---
# This allows .env to override defaults set below if needed
ENV_PATH = Path('.') / '.env'
load_dotenv(dotenv_path=ENV_PATH)

# --- Base Directory --- 
BASE_DIR = Path(__file__).parent.resolve()

# --- Logging Configuration ---
# Get log directory from environment or use default
DEFAULT_LOG_DIR = BASE_DIR / "logs"
LOG_DIR_STR = os.getenv("VANTA_LOG_DIR", str(DEFAULT_LOG_DIR))
LOG_DIR = Path(LOG_DIR_STR).resolve()

# Ensure log directory exists
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except Exception as e:
    print(f"[WARN] Could not create log directory {LOG_DIR}: {e}")
    # Fallback? For now, just print warning.

# Set environment variable if not already set by .env (for other modules)
# Note: load_dotenv doesn't override existing env vars by default
if "VANTA_LOG_DIR" not in os.environ:
     os.environ["VANTA_LOG_DIR"] = str(LOG_DIR)

# Basic logging setup (can be customized further)
LOG_LEVEL = os.getenv("VANTA_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(levelname)s - %(name)s - [%(filename)s:%(lineno)d] - %(message)s', # Enhanced format
    handlers=[ # Explicitly define handlers
        logging.StreamHandler()
    ]
)

# --- Add File Handler ---
log_file_path = LOG_DIR / "vanta_core.log"
try:
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(LOG_LEVEL)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - [%(filename)s:%(lineno)d] - %(message)s')
    file_handler.setFormatter(file_formatter)
    logging.getLogger().addHandler(file_handler) # Add handler to the root logger
    print(f"Configured file logging to: {log_file_path}")
except Exception as e:
    print(f"[WARN] Could not configure file logging to {log_file_path}: {e}")
# ----------------------

# --- Path Definitions ---
BLUEPRINT_PATH = BASE_DIR / os.getenv("VANTA_BLUEPRINT_FILE", "blueprint.yaml")
AGENT_INDEX_PATH = BASE_DIR / os.getenv("VANTA_AGENT_INDEX_FILE", "agents.index.mpc.json")

# --- Other Configurations ---
# Example: Load API keys safely
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Add other environment variables or derived configurations here

# --- Allowed API Keys for VANTA API ---
# Load comma-separated keys from env var, default to empty list if not set
ALLOWED_API_KEYS_STR = os.getenv("VANTA_ALLOWED_API_KEYS", "")
ALLOWED_API_KEYS = set(key.strip() for key in ALLOWED_API_KEYS_STR.split(',') if key.strip())
if not ALLOWED_API_KEYS:
    print("[WARN] VANTA_ALLOWED_API_KEYS environment variable not set or empty. API will be accessible without authentication.")
else:
    print(f"Loaded {len(ALLOWED_API_KEYS)} allowed API keys.")
# ------------------------------------

# --- Print loaded config for verification --- 
print("--- Configuration Loaded ---")
print(f"BASE_DIR: {BASE_DIR}")
print(f"LOG_DIR: {LOG_DIR} (Level: {LOG_LEVEL})")
print(f"BLUEPRINT_PATH: {BLUEPRINT_PATH}")
print(f"AGENT_INDEX_PATH: {AGENT_INDEX_PATH}")
print(f"OpenAI Key Loaded: {'Yes' if OPENAI_API_KEY else 'No'}")
print("--------------------------")

# --- Functions to access config (optional) ---
def get_log_dir() -> Path:
    return LOG_DIR

def get_blueprint_path() -> Path:
    return BLUEPRINT_PATH

def get_agent_index_path() -> Path:
    return AGENT_INDEX_PATH 