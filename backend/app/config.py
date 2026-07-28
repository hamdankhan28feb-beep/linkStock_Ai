from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/linkstock_db"

    # JWT
    SECRET_KEY: str = "linkstock-ai-secret-key-2024-hackathon-secure-32chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Supabase
    SUPABASE_URL: str = "https://wdifcoslcosbuambsrsm.supabase.co"
    SUPABASE_ANON_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndkaWZjb3NsY29zYnVhbWJzcnNtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODUxMjY4MzcsImV4cCI6MjEwMDcwMjgzN30.KWpv_YNSL9uN-0CjWw0ppT5emjnXVuH0_isZm4IIGOU"
    SUPABASE_SERVICE_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndkaWZjb3NsY29zYnVhbWJzcnNtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODUxMjY4MzcsImV4cCI6MjEwMDcwMjgzN30.KWpv_YNSL9uN-0CjWw0ppT5emjnXVuH0_isZm4IIGOU"
    SUPABASE_PUBLISHABLE_KEY: str = "sb_publishable_AMFQMu37aDQxOWJ1UG5noQ_HSIR7L6k"

    # App
    APP_NAME: str = "LinkStock AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
