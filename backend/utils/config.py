import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "")
    TEMPERATURE: float = float(os.getenv("GROQ_TEMPERATURE", "0.7"))
    RECURSION_LIMIT: dict = {"recursion_limit":100}

settings = Settings()

max_history = 10

if not settings.GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY must be set in environment")