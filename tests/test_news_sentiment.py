import pytest
from datetime import datetime
from app.models_news import NewsArticle
from app.services.sentiment_service import SentimentService
from app.services.news_service import NewsService

def test_news_article_model_compliance():
    """Verify strict JSON structure matches user requirements."""
    article = NewsArticle(
        ticker="SE",
        title="Test Title",
        url="http://test.com",
        published_at=datetime.now(),
        source="Yahoo Scout",
        source_weight=0.8,
        sentiment_score=-0.4,
        logic="Conflict between high growth...",
        impact_window="Medium-term",
        reasoning="Investors are punishing...",
        opportunity_score=7.5
    )
    
    data = article.dict()
    assert "logic" in data
    assert "reasoning" in data
    assert "impact_window" in data
    assert "opportunity_score" in data
    assert data["ticker"] == "SE"

def test_sentiment_heuristics_short_term():
    service = SentimentService()
    
    # Test "Short-term" keywords
    res = service.analyze_impact("Sea Limited Earnings Beat Guidance")
    assert res["impact_window"] == "Short-term"
    
def test_sentiment_heuristics_logic_generation():
    service = SentimentService()
    
    # Mock VADER to return positive
    # We can't easily mock the internal library without patching, 
    # but we can rely on real VADER for "Great Profit" = Positive
    
    res = service.analyze_impact("Sea Limited posts record Profit")
    assert res["sentiment_score"] > 0
    assert "Profitability" in res["logic"]
    
    # Negative growth conflict test (Harder to stick with pure VADER, might need mock)
    # Let's rely on the simple keyword text in analyze_impact
    
def test_source_weight_calculation():
    news_service = NewsService()
    assert news_service.calculate_source_weight("Bloomberg") == 1.0
    assert news_service.calculate_source_weight("Twitter") == 0.5
    assert news_service.calculate_source_weight("Some Blog") == 0.5
