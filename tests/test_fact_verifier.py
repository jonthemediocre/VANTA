import os
import pytest
from vanta_nextgen import FactVerifier, VerificationResult

class DummyResponse:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data
    def json(self):
        return self._data

# Test cases for WolframAlpha-backed verification

def test_verify_wolfram_success(monkeypatch):
    # Stub environment variable and requests.get
    monkeypatch.setenv('WOLFRAM_APP_ID', 'dummy')
    pods_data = {"queryresult": {"pods": [{"title": "Result: 4"}]}}
    def fake_get(url, params, timeout):
        return DummyResponse(200, pods_data)
    monkeypatch.setattr('requests.get', fake_get)
    fv = FactVerifier()
    res = fv.verify("2+2", "4")
    assert isinstance(res, VerificationResult)
    assert res.is_valid is True
    assert res.source == 'wolfram'
    assert res.confidence == pytest.approx(0.9)


def test_verify_wolfram_failure(monkeypatch):
    monkeypatch.setenv('WOLFRAM_APP_ID', 'dummy')
    pods_data = {"queryresult": {"pods": [{"title": "NoResult"}]}}
    def fake_get(url, params, timeout):
        return DummyResponse(200, pods_data)
    monkeypatch.setattr('requests.get', fake_get)
    fv = FactVerifier()
    res = fv.verify("foo", "bar")
    assert res.is_valid is False
    assert res.source == 'wolfram'
    assert res.confidence == pytest.approx(0.1)


def test_verify_http_error(monkeypatch):
    monkeypatch.setenv('WOLFRAM_APP_ID', 'dummy')
    def fake_get(url, params, timeout):
        return DummyResponse(500, {})
    monkeypatch.setattr('requests.get', fake_get)
    fv = FactVerifier()
    res = fv.verify("x", "y")
    assert res.is_valid is False
    assert res.source == 'wolfram'
    assert 'HTTP 500' in (res.error or '')

# Test cases for heuristic fallback

def test_verify_heuristic_numeric(monkeypatch):
    # Ensure no Wolfram key
    monkeypatch.delenv('WOLFRAM_APP_ID', raising=False)
    fv = FactVerifier()
    res = fv.verify("anything", "12345")
    assert res.is_valid is True
    assert res.source == 'heuristic'
    assert res.confidence == fv.fallback_confidence


def test_verify_heuristic_non_numeric(monkeypatch):
    monkeypatch.delenv('WOLFRAM_APP_ID', raising=False)
    fv = FactVerifier()
    res = fv.verify("anything", "non-numeric")
    assert res.is_valid is False
    assert res.source == 'heuristic'
    assert res.confidence == fv.fallback_confidence 