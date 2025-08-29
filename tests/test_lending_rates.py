import pytest

from fundrunner.services.lending_rates import LendingRateService
from fundrunner.utils.error_handling import FundRunnerError


def test_fetch_stub_rates_returns_deterministic_values():
    service = LendingRateService()
    symbols = ["AAPL", "MSFT", "GOOG"]
    rates = service.fetch_stub_rates(symbols)
    assert rates == {"AAPL": 0.01, "MSFT": 0.015, "GOOG": 0.02}


def test_get_rates_falls_back_to_stub(monkeypatch):
    service = LendingRateService()
    monkeypatch.setattr(
        service,
        "fetch_live_rates",
        lambda symbols: (_ for _ in ()).throw(FundRunnerError("boom")),
    )
    called = {}

    def fake_failure(symbols, error):
        called["failure"] = (symbols, error)

    monkeypatch.setattr(
        "fundrunner.services.lending_rates.log_lending_rate_failure", fake_failure
    )
    symbols = ["AAPL", "MSFT"]
    rates = service.get_rates(symbols)
    assert rates == {"AAPL": 0.01, "MSFT": 0.015}
    assert called["failure"][0] == symbols


def test_get_rates_uses_live_when_available(monkeypatch):
    service = LendingRateService()
    monkeypatch.setattr(
        service, "fetch_live_rates", lambda symbols: {s: 0.5 for s in symbols}
    )
    called = {}

    def fake_success(symbols, rates):
        called["success"] = (symbols, rates)

    monkeypatch.setattr(
        "fundrunner.services.lending_rates.log_lending_rate_success", fake_success
    )
    result = service.get_rates(["AAPL"])
    assert result == {"AAPL": 0.5}
    assert called["success"] == (["AAPL"], {"AAPL": 0.5})


def test_fetch_live_rates_requires_credentials(monkeypatch):
    monkeypatch.delenv("APCA_API_KEY_ID", raising=False)
    monkeypatch.delenv("APCA_API_SECRET_KEY", raising=False)
    service = LendingRateService()
    with pytest.raises(FundRunnerError):
        service.fetch_live_rates(["AAPL"])
