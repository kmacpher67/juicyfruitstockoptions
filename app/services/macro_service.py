import requests
from datetime import datetime
from app.config import settings
from app.models_news import MacroIndicator
import logging

logger = logging.getLogger(__name__)

class MacroService:
    def __init__(self):
        self.api_key = settings.FRED_API_KEY
        self.base_url = "https://api.stlouisfed.org/fred/series/observations"

    def fetch_indicator(self, series_id: str, title: str) -> MacroIndicator:
        """Fetches the latest observation for a FRED series."""
        if not self.api_key:
            logger.warning("No FRED API key found")
            return None

        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 1
        }

        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            observations = data.get("observations", [])
            if not observations:
                return None
            
            obs = observations[0]
            
            return MacroIndicator(
                series_id=series_id,
                title=title,
                value=float(obs["value"]),
                date=datetime.strptime(obs["date"], "%Y-%m-%d"),
                unit="Points/Percent" # Simplification, ideally fetched from metadata
            )

        except Exception as e:
            logger.error(f"Error fetching FRED data for {series_id}: {e}")
            return None

    def get_market_condition(self) -> str:
        """
        Determines market regime based on simple heuristics.
        Note: Requires fetching multiple indicators first.
        """
        # Placeholder logic
        return "Neutral"
