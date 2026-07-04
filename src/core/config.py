import os
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

class Config(BaseModel):
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    DB_NAME: str = os.getenv("DB_NAME", "jobsentinel")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    NOTIFY_EMAIL: str = os.getenv("NOTIFY_EMAIL", "")
    
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json")
    
    SCRAPE_INTERVAL: int = int(os.getenv("SCRAPE_INTERVAL", "60"))
    JOB_KEYWORDS: str = os.getenv("JOB_KEYWORDS", "Software Engineer")
    JOB_LOCATIONS: str = os.getenv("JOB_LOCATIONS", "Remote")
    
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "output_resumes")
    SCRAPE_HEADLESS: bool = os.getenv("SCRAPE_HEADLESS", "True").lower() in ("true", "1", "t")

config = Config()

if not os.path.exists(config.OUTPUT_DIR):
    os.makedirs(config.OUTPUT_DIR)
