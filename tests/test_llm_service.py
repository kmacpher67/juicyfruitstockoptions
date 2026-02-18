
import pytest
from unittest.mock import MagicMock, patch



@pytest.fixture
def mock_settings():
    """Patch settings on the llm_service module so GeminiService sees fake values."""
    with patch("app.services.llm_service.settings") as _mock:
        _mock.GOOGLE_API_KEY = "fake_key"
        _mock.GEMINI_MODEL = "gemini-pro"
        yield _mock


@pytest.fixture
def mock_genai():
    """Patch google.generativeai AND the parent 'google' package in sys.modules.

    Python resolves ``import google.generativeai as genai`` by looking up
    ``sys.modules["google"].generativeai``, so the parent mock MUST have the
    ``generativeai`` attribute wired to our genai mock.
    """
    mock_genai_module = MagicMock()
    mock_model_instance = MagicMock()
    mock_genai_module.GenerativeModel.return_value = mock_model_instance

    mock_google_pkg = MagicMock()
    mock_google_pkg.generativeai = mock_genai_module  # critical link

    modules = {
        "google": mock_google_pkg,
        "google.generativeai": mock_genai_module,
    }

    with patch.dict("sys.modules", modules):
        yield mock_genai_module, mock_model_instance


def test_gemini_service_initialization_success(mock_settings, mock_genai):
    """Test successful initialization with API key."""
    from app.services.llm_service import GeminiService
    service = GeminiService()

    # Verify lazy init: model should be None initially
    assert service.model is None
    assert service._is_initialized is False

    # Trigger initialization (simulated)
    service._ensure_initialized()

    assert service.model is not None
    mock_genai_module, _ = mock_genai
    mock_genai_module.configure.assert_called_with(api_key="fake_key")
    mock_genai_module.GenerativeModel.assert_called_with("gemini-pro")


def test_gemini_service_initialization_no_key():
    """Test initialization fails gracefully without API key."""
    with patch("app.services.llm_service.settings") as _mock:
        _mock.GOOGLE_API_KEY = ""
        from app.services.llm_service import GeminiService
        service = GeminiService()
        assert service.model is None

        # Trigger init
        service._ensure_initialized()
        assert service.model is None


def test_generate_reasoning_success(mock_settings, mock_genai):
    """Test generate_reasoning returns text on success."""
    mock_genai_module, mock_model = mock_genai
    mock_response = MagicMock()
    mock_response.text = "Analysis Complete"
    mock_model.generate_content.return_value = mock_response

    from app.services.llm_service import GeminiService

    service = GeminiService()
    result = service.generate_reasoning("Test Context")

    assert result == "Analysis Complete"
    mock_genai_module.configure.assert_called_with(api_key="fake_key")
    mock_model.generate_content.assert_called_once_with("Test Context")


def test_generate_reasoning_error(mock_settings, mock_genai):
    """Test generate_reasoning handles exceptions."""
    _, mock_model = mock_genai
    mock_model.generate_content.side_effect = Exception("API Error")

    from app.services.llm_service import GeminiService
    mock_genai_module, _ = mock_genai

    service = GeminiService()
    result = service.generate_reasoning("Test Context")

    assert "Error generation reasoning" in result
    mock_genai_module.configure.assert_called_with(api_key="fake_key")


def test_get_trade_analysis_construction(mock_settings, mock_genai):
    """Test that get_trade_analysis constructs the prompt correctly."""
    mock_genai_module, mock_model = mock_genai

    mock_response = MagicMock()
    mock_response.text = "Trade Plan"
    mock_model.generate_content.return_value = mock_response

    from app.services.llm_service import GeminiService
    service = GeminiService()
    context = {
        "current_price": 100,
        "cost_basis": 90,
        "risk_profile": "Aggressive",
        "strategies": ["Covered Call", "Roll"]
    }

    service.get_trade_analysis("AAPL", context)

    # Verify init happened
    mock_genai_module.configure.assert_called_with(api_key="fake_key")

    # Verify the prompt contains key elements
    call_args = mock_model.generate_content.call_args[0][0]
    assert "Ticker: AAPL" in call_args
    assert "Current Price: 100" in call_args
    assert "Risk Profile: Aggressive" in call_args
    assert "Covered Call" in call_args

