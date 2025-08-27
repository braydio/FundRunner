"""Tests for the lending rates service."""

from __future__ import annotations

import requests

from fundrunner.services.lending_rates import fetch_lending_rates


class DummyResponse:
    """Simple mock HTTP response object."""

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        """Pretend the HTTP status was successful."""

    def json(self):
        """Return the injected JSON payload."""
        return self._payload


def test_fetch_lending_rates_valid(monkeypatch):
    """Parses a valid API response into a rates dictionary."""

    payload = {"rates": [{"symbol": "AAA", "rate": 0.05}, {"symbol": "BBB", "rate": 0.04}]}
    monkeypatch.setattr(requests, "get", lambda *a, **k: DummyResponse(payload))
    rates = fetch_lending_rates()
    assert rates == {"AAA": 0.05, "BBB": 0.04}


def test_fetch_lending_rates_fallback(monkeypatch):
    """Falls back to stub data when the request errors."""

    def mock_get(*args, **kwargs):
        raise requests.RequestException("network down")

    monkeypatch.setattr(requests, "get", mock_get)
    rates = fetch_lending_rates()
    assert "AAPL" in rates and rates["AAPL"] > 0
