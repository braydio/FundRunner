import json

import requests

from fundrunner.services import news
from fundrunner.alpaca import portfolio_manager


def test_fetch_news_success(monkeypatch):
    class DummyResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"news": [{"headline": "h1"}]}

    def fake_get(url, params, headers, timeout):
        return DummyResponse()

    monkeypatch.setattr(news.requests, "get", fake_get)
    headlines = news.fetch_news(["AAPL"])
    assert headlines == ["h1"]


def test_fetch_news_failure(monkeypatch):
    def fake_get(url, params, headers, timeout):
        raise requests.RequestException("boom")

    monkeypatch.setattr(news.requests, "get", fake_get)
    assert news.fetch_news(["AAPL"]) == []


def test_determine_target_weights_includes_news(monkeypatch):
    monkeypatch.setattr(
        portfolio_manager, "fetch_news", lambda symbols: ["Breaking"]
    )

    captured = {}

    def fake_ask(prompt: str, model: str = "gpt-4"):
        captured["prompt"] = prompt
        return json.dumps({"AAPL": 1.0})

    monkeypatch.setattr(portfolio_manager, "ask_gpt", fake_ask)

    pm = portfolio_manager.PortfolioManager()
    weights = pm.determine_target_weights(["AAPL"])
    assert weights == {"AAPL": 1.0}
    assert "Breaking" in captured["prompt"]
