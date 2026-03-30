from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import routes, trades
from app.scheduler.jobs import start_scheduler, stop_scheduler
from app.services.ibkr_tws_service import get_ibkr_tws_service, set_ibkr_tws_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from app.utils.logging_config import setup_logging
    setup_logging()

    tws_service = get_ibkr_tws_service()
    app.state.ibkr_tws_service = tws_service
    if settings.IBKR_TWS_ENABLED:
        tws_service.connect()

    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()
    tws_service.disconnect()
    set_ibkr_tws_service(None)

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
