from fastapi import APIRouter

from services.portfolio_fixer import run_portfolio_fixer
from services.stock_live_comparison import run_stock_live_comparison

router = APIRouter()


@router.get("/run/portfolio-fixer")
def run_portfolio_fixer_endpoint():
    return run_portfolio_fixer()


@router.get("/run/portfolio-fixer")
def run_portfolio_fixer_endpoint():
    return run_portfolio_fixer()

@router.get("/run/stock-live-comparison")
def run_stock_live_comparison_endpoint():
    return run_stock_live_comparison()
