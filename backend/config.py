import os
from dotenv import load_dotenv

# Force reload of .env file
load_dotenv(override=False)

SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")  # Use a strong random string
ALGORITHM = os.getenv("ALGORITHM")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")

# LLM Selection Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower() # Options: ollama, router, openai
LLM_API_KEY = os.getenv("LLM_API_KEY") or OPENROUTER_API_KEY # Fallback for backward compatibility
LLM_MODEL = os.getenv("LLM_MODEL") # Optional override


QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
USDA_API_KEY = os.getenv("USDA_API_KEY")

print("--- CONFIG DEBUG ---")
print(f"QDRANT_URL: '{QDRANT_URL}'")
print(f"REDIS_URL: '{REDIS_URL}'")
print("--------------------")