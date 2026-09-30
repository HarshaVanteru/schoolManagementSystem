from dotenv import load_dotenv
import os
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()

class Settings():
    DATABASE_URL = os.getenv("DATABASE_URL")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    LLM_MODEL = os.getenv("LLM_MODEL")

settings = Settings()
