
import pytest
import requests

def test_requests_import():
    print(f"Requests file: {requests.__file__}")
    print(f"Requests version: {requests.__version__}")
    assert requests.__version__ is not None
