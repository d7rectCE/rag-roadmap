import pytest
from pydantic import ValidationError
from src.fetcher.models import FetchResult

def test_valid_ok():
    res = FetchResult(url="http://test", status="ok", status_code=200, attempts=1, duration=0.5)
    assert res.status == "ok"

def test_valid_error():
    res = FetchResult(url="http://test", status="error", error_message="fail", error_type="timeout", attempts=1, duration=0.5)
    assert res.status == "error"

def test_reject_ok_without_status_code():
    with pytest.raises(ValidationError, match="status='ok' требует указания status_code"):
        FetchResult(url="http://test", status="ok", attempts=1, duration=0.5)

def test_reject_error_without_message():
    with pytest.raises(ValidationError, match="status='error' требует указания error_message"):
        FetchResult(url="http://test", status="error", error_type="timeout", attempts=1, duration=0.5)

def test_reject_ok_with_error_message():
    with pytest.raises(ValidationError, match="status='ok' запрещает наличие error_message"):
        FetchResult(url="http://test", status="ok", status_code=200, error_message="oops", attempts=1, duration=0.5)

def test_reject_missing_required_field():
    with pytest.raises(ValidationError, match="attempts"):
        FetchResult(url="http://test", status="ok", status_code=200, duration=0.5)