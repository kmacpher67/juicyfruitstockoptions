
import pytest

def test_app_llm_service_import():
    from app.services.llm_service import GeminiService
    print("Successfully imported app.services.llm_service")
    assert True
