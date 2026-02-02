import requests
from datetime import datetime
from app.config import settings
from app.models_news import NewsArticle
from app.services.sentiment_service import SentimentService
import logging

logger = logging.getLogger(__name__)

class NewsService:
    def __init__(self):
        self.api_key = settings.NEWS_API_KEY
        self.base_url = "https://newsapi.org/v2/everything"
        self.sentiment_service = SentimentService()

    def fetch_news_for_ticker(self, ticker: str) -> list[NewsArticle]:
        """Fetches news for a given ticker and enriches it with sentiment analysis."""
        if not self.api_key:
            logger.warning("No NewsAPI key found, returning empty list")
            return []

        params = {
            "q": ticker,
            "apiKey": self.api_key,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 5  # Limit to 5 most recent for now
        }

        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for item in data.get("articles", []):
                # Analyze sentiment/logic
                analysis = self.sentiment_service.analyze_impact(item["title"])
                
                article = NewsArticle(
                    ticker=ticker,
                    title=item["title"],
                    url=item["url"],
                    published_at=datetime.fromisoformat(item["publishedAt"].replace("Z", "+00:00")),
                    source=item["source"]["name"],
                    source_weight=self.calculate_source_weight(item["source"]["name"]),
                    
                    # AI Fields
                    sentiment_score=analysis["sentiment_score"],
                    logic=analysis["logic"],
                    impact_window=analysis["impact_window"],
                    reasoning=analysis["reasoning"],
                    opportunity_score=analysis["opportunity_score"]
                )
                articles.append(article)
            
            return articles

        except Exception as e:
            logger.error(f"Error fetching news for {ticker}: {e}")
            return []

    def calculate_source_weight(self, source_name: str) -> float:
        """Assigns weight based on source credibility."""
        high_trust = ["Bloomberg", "Reuters", "WSJ", "CNBC", "Financial Times"]
        medium_trust = ["Yahoo Finance", "MarketWatch", "Benzinga"]
        
        if any(s.lower() in source_name.lower() for s in high_trust):
            return 1.0
        if any(s.lower() in source_name.lower() for s in medium_trust):
            return 0.8
        return 0.5
