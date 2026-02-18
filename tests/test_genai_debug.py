
import pytest

genai = pytest.importorskip("google.generativeai", reason="google-generativeai not installed")

def test_genai_import():
    print("Successfully imported google.generativeai")
    assert True
