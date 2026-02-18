
import pytest


def test_requests_import():
    try:
        import requests
        # Guard against sys.modules mocking from other tests
        file_path = getattr(requests, "__file__", None)
        version = getattr(requests, "__version__", None)
        print(f"Requests file: {file_path}")
        print(f"Requests version: {version}")
        assert version is not None
    except (ImportError, AttributeError):
        pytest.skip("requests module not available or mocked by another test")
