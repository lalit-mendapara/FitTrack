
import os
from dotenv import load_dotenv

load_dotenv(override=True)

print(f"OLLAMA_URL: {os.getenv('OLLAMA_URL')}")
print(f"OLLAMA_MODEL: {os.getenv('OLLAMA_MODEL')}")
print(f"OPENROUTER_API_KEY: {os.getenv('OPENROUTER_API_KEY')}")
print(f"OLLAMA_API_KEY: {os.getenv('OLLAMA_API_KEY')}")
