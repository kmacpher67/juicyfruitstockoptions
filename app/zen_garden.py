import uvicorn
from fastapi import FastAPI

from api.routes import router
from scheduler.jobs import schedule_jobs
from auth.users import fastapi_users, auth_backend

app = FastAPI(title="Stock Automation API")
app.include_router(router)
app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(), prefix="/auth", tags=["auth"]
)


@app.on_event("startup")
def startup_event() -> None:
    schedule_jobs()


if __name__ == "__main__":
    uvicorn.run("zen_garden:app", host="0.0.0.0", port=8000)
