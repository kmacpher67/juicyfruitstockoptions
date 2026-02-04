
import pytest
from unittest.mock import MagicMock, patch
from app.services.llm_service import GeminiService

# Mock settings
@pytest.fixture
def mock_settings():
    with patch("app.services.llm_service.settings") as mock_settings:
        mock_settings.GOOGLE_API_KEY = "fake_key"
        mock_settings.GEMINI_MODEL = "gemini-pro"
        yield mock_settings

# Mock genai
@pytest.fixture
def mock_genai():
    with patch("app.services.llm_service.genai") as mock_genai:
        mock_model_instance = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model_instance
        yield mock_genai, mock_model_instance

def test_gemini_service_initialization_success(mock_settings, mock_genai):
    """Test successful initialization with API key."""
    service = GeminiService()
    
    assert service.model is not None
    mock_genai[0].configure.assert_called_with(api_key="fake_key")
    mock_genai[0].GenerativeModel.assert_called_with("gemini-pro")

def test_gemini_service_initialization_no_key():
    """Test initialization fails gracefully without API key."""
    with patch("app.services.llm_service.settings") as mock_settings:
        mock_settings.GOOGLE_API_KEY = ""
        service = GeminiService()
        assert service.model is None

def test_generate_reasoning_success(mock_settings, mock_genai):
    """Test generate_reasoning returns text on success."""
    _, mock_model = mock_genai
    mock_response = MagicMock()
    mock_response.text = "Analysis Complete"
    mock_model.generate_content.return_value = mock_response
    
    service = GeminiService()
    result = service.generate_reasoning("Test Context")
    
    assert result == "Analysis Complete"
    mock_model.generate_content.assert_called_once_with("Test Context")

def test_generate_reasoning_error(mock_settings, mock_genai):
    """Test generate_reasoning handles exceptions."""
    _, mock_model = mock_genai
    mock_model.generate_content.side_effect = Exception("API Error")
    
    service = GeminiService()
    result = service.generate_reasoning("Test Context")
    
    assert "Error generation reasoning" in result

def test_get_trade_analysis_construction(mock_settings, mock_genai):
    """Test that get_trade_analysis constructs the prompt correctly."""
    _, mock_model = mock_genai
    mock_response = MagicMock()
    mock_response.text = "Trade Plan"
    mock_model.generate_content.return_value = mock_response
    
    service = GeminiService()
    context = {
        "current_price": 100,
        "cost_basis": 90,
        "risk_profile": "Aggressive",
        "strategies": ["Covered Call", "Roll"]
    }
    
    service.get_trade_analysis("AAPL", context)
    
    # Verify the prompt contains key elements
    call_args = mock_model.generate_content.call_args[0][0]
    assert "Ticker: AAPL" in call_args
    assert "Current Price: 100" in call_args
    assert "Risk Profile: Aggressive" in call_args
    assert "Covered Call" in call_args
