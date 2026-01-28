from datetime import timedelta
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pymongo import MongoClient

from app.auth.dependencies import get_current_active_user
from app.auth.utils import create_access_token, verify_password, get_password_hash
from app.config import settings
from app.models import Token, User, StockRecord

from app.services.portfolio_fixer import run_portfolio_fixer
from app.services.stock_live_comparison import run_stock_live_comparison

router = APIRouter()

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    # Verify User (Bootstrap Logic)
    if form_data.username != settings.ADMIN_USER or not verify_password(form_data.password, get_password_hash(settings.ADMIN_PASS)):
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=User)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    return current_user

# --- Secured Endpoints ---

@router.get("/stocks", response_model=List[StockRecord])
async def get_stocks(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Fetch all stock records from MongoDB.
    """
    try:
        # Connect to Mongo (Connection pooling is handled by driver, simple connect here is fine for now)
        client = MongoClient(settings.MONGO_URI)
        db = client["stock_analysis"]
        collection = db["stock_data"]
        
        # Fetch all records, exclude internal Mongo ID
        cursor = collection.find({}, {"_id": 0})
        results = list(cursor)
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/run/portfolio-fixer")
def run_portfolio_fixer_endpoint(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    return run_portfolio_fixer()

from fastapi import BackgroundTasks
from app.jobs import create_job, get_job, update_job_status, JobStatus, Job

def background_job_wrapper(job_id: str, func):
    """Wrapper to run a function and update job status."""
    try:
        update_job_status(job_id, JobStatus.RUNNING)
        result = func()
        update_job_status(job_id, JobStatus.COMPLETED, result=result)
    except Exception as e:
        update_job_status(job_id, JobStatus.FAILED, error=str(e))

@router.get("/jobs/{job_id}", response_model=Job)
def get_job_status(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    job = get_job(job_id)
    if not job:
          raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/run/stock-live-comparison")
def run_stock_live_comparison_endpoint(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    # Create Job
    job = create_job()
    
    # Add to Background Tasks
    background_tasks.add_task(background_job_wrapper, job.id, run_stock_live_comparison)
    
    return {"job_id": job.id, "status": "queued"}

@router.get("/reports", response_model=List[str])
async def list_reports(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """List all available Excel reports."""
    import os
    report_dir = "report-results"
    if not os.path.exists(report_dir):
        return []
    files = [f for f in os.listdir(report_dir) if f.endswith('.xlsx') and not f.startswith('~$')]
    # Sort by modification time (newest first)
    files.sort(key=lambda x: os.path.getmtime(os.path.join(report_dir, x)), reverse=True)
    return files

@router.get("/reports/{filename}/data")
async def get_report_data(
    filename: str,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Read a specific Excel file and return as JSON for the grid."""
    import os
    import pandas as pd
    
    report_path = os.path.join("report-results", filename)
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not found")
    
    try:
        # Read Excel using pandas
        # Ensure we read the correct engine
        df = pd.read_excel(report_path, engine='openpyxl')
        
        # Handle NaN/Inf for JSON compliance
        df = df.replace({float('nan'): None, float('inf'): None, float('-inf'): None})
        
        # Convert to list of dicts
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read report: {str(e)}")

@router.get("/reports/{filename}/download")
async def download_report(
    filename: str,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Download a specific Excel report."""
    import os
    from fastapi.responses import FileResponse
    
    report_path = os.path.join("report-results", filename)
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not found")
        
    return FileResponse(report_path, filename=filename)
