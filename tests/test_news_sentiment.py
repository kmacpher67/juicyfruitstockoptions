import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from app.models_news import NewsArticle


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
    """Test that short-term keywords produce Short-term impact window."""
    from app.services.sentiment_service import SentimentService
    service = SentimentService()
    
    # Test "Short-term" keywords (earnings, beat, guidance)
    res = service.analyze_impact("Sea Limited Earnings Beat Guidance")
    assert res["impact_window"] == "Short-term"


def test_sentiment_heuristics_logic_generation():
    """Test that profit-related text generates Profitability logic."""
    from app.services.sentiment_service import SentimentService
    service = SentimentService()
    
    # Patch VADER to return a controlled positive score
    # so the test is deterministic regardless of lexicon version
    with patch.object(service.sia, "polarity_scores", return_value={"compound": 0.6}):
        res = service.analyze_impact("Sea Limited posts record Profit")
        assert res["sentiment_score"] > 0
        assert "Profitability" in res["logic"]


def test_source_weight_calculation():
    from app.services.news_service import NewsService
    news_service = NewsService()
    assert news_service.calculate_source_weight("Bloomberg") == 1.0
    assert news_service.calculate_source_weight("Twitter") == 0.5
    assert news_service.calculate_source_weight("Some Blog") == 0.5
