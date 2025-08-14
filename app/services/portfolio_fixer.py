import logging
import os
import importlib.util
from pathlib import Path

# Dynamically load existing script with hyphen in name
_module_path = Path(__file__).resolve().parents[2] / "portfolio-fixer.py"
spec = importlib.util.spec_from_file_location("portfolio_fixer_module", str(_module_path))
portfolio_fixer_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(portfolio_fixer_module)


def run_portfolio_fixer(portfolio_dir: str | None = None) -> dict:
    """Run the portfolio fixer safely and return status information."""
    try:
        portfolio_dir = portfolio_dir or os.getcwd()
        latest_file = portfolio_fixer_module.get_latest_portfolio_file(portfolio_dir)
        portfolio_fixer_module.evaluate_portfolio(latest_file)
        return {"status": "success", "file": latest_file}
    except Exception as exc:
        logging.exception("Portfolio fixer failed")
        return {"status": "error", "error": str(exc)}
