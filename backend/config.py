from dotenv import load_dotenv
import os

# Load .env file from backend directory
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)

# Also try loading from root directory (for backward compatibility)
root_env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(root_env_path):
    load_dotenv(dotenv_path=root_env_path)

# API Keys - MUST be set in .env file (no hardcoded fallbacks for security)
GITHUB_TOKEN = os.getenv("GITHUB_API_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Validate required API keys
if not GROQ_API_KEY:
    import warnings
    warnings.warn(
        "GROQ_API_KEY is not set in environment variables. "
        "AI features (summaries, role prediction, recommendation ranking) will be unavailable. "
        "Please set GROQ_API_KEY in backend/.env file."
    )
