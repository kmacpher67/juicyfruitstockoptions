from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "JuicyFruit Stock Portal"
    ENVIRONMENT: str = "development"
    # Scheduler
    RUN_TIME: str = "16:00"
    
    # Database
    MONGO_URI: str = "mongodb://mongo:27017" # Docker default
    MONGO_DB_NAME: str = "stock_data"
    
    # Logic
    MAX_AGE_HOURS: int = 4
    DATA_DIR: str = "/app/data/ibkr_data"

    # IBKR Client Portal fallback
    IBKR_PORTAL_ENABLED: bool = False
    IBKR_PORTAL_BASE_URL: str = "https://ibkr-portal:5000/v1/api"
    IBKR_PORTAL_ACCOUNT_ID: str | None = None
    IBKR_PORTAL_VERIFY_SSL: bool = False
    IBKR_PORTAL_TIMEOUT_SECONDS: int = 10

    # IBKR TWS / Gateway socket connection
    IBKR_TWS_ENABLED: bool = False
    IBKR_TWS_HOST: str = "127.0.0.1"
    IBKR_TWS_PORT: int = 4002
    IBKR_TWS_CLIENT_ID: int = 1
    
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
    
    # LLM / Agent
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-pro"
    
    # Calendar
    CALENDAR_LOOKAHEAD_DAYS: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
