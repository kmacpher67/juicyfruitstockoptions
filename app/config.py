from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "JuicyFruit Stock Portal"
    # Scheduler
    RUN_TIME: str = "16:00"
    
    # Database
    MONGO_URI: str = "mongodb://mongo:27017" # Docker default
    MONGO_DB_NAME: str = "stock_data"
    
    # Logic
    MAX_AGE_HOURS: int = 4
    DATA_DIR: str = "/app/data/ibkr_data"
    
    # Security
    SECRET_KEY: str = "CHANGE_ME_IN_PROD_9834758934758934" 
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Admin User (Initial Bootstrap)
    ADMIN_USER: str = "admin"
    ADMIN_PASS: str = "admin123"

    # External APIs
    NEWS_API_KEY: str = ""
    FRED_API_KEY: str = ""
    X_API_KEY: str | None = None
    X_API_SECRET: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
