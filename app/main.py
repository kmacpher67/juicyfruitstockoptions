from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import routes, trades
from app.scheduler.jobs import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    import logging
    # Configure logging to file (visible on host via volume mount)
    # Ensure directory exists in case it wasn't mapped
    import os
    os.makedirs("logs", exist_ok=True)
    
    logging.basicConfig(
        filename="logs/stock_portal_debug.log",
        level=logging.DEBUG,
        # Format: {datetime stamp} - {filename-class-method/function_name} - {LEVEL} - {message text}
        format='%(asctime)s - %(filename)s-%(name)s-%(funcName)s - %(levelname)s - %(message)s',
        force=True # Force reconfiguration to override Uvicorn defaults for file output
    )
    # Add console handler back so docker logs still work
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger().addHandler(console)
    
    # Silence noisy libraries
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()

app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan
)

# Global Exception Handler to catch 500s that happen outside route handlers (e.g. serialization)
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    import logging
    import traceback
    from fastapi.responses import JSONResponse
    
    logger = logging.getLogger("app.main")
    error_msg = f"Global 500 Error: {str(exc)}"
    logger.error(f"{error_msg}\n{traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error. Check logs for details."},
    )

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for development convenience as requested ("Remote access via browser")
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router, prefix="/api")
app.include_router(trades.router, prefix="/api/trades", tags=["trades"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
