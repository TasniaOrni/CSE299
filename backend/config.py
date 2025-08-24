import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "CSE299 Project"
    DATABASE_URL: str = os.getenv("DATABASE_URL")  # Neon DB
    BREVO_API_KEY: str = os.getenv("BREVO_API_KEY")
    Google_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID")
    Google_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET")
    JWT_SECRET: str = os.getenv("JWT_SECRET_KEY", "supersecret")
    JWT_ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

settings = Settings()