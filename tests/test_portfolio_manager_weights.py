"""Tests for PortfolioManager target weight calculations."""

import importlib

import pytest

from fundrunner.utils import config as config_mod
import fundrunner.alpaca.portfolio_manager as pm_mod


def test_equal_weight_mode(monkeypatch):
    """All tickers share equal weight when SECTOR_MODE is disabled."""

    monkeypatch.delenv("SECTOR_MODE", raising=False)
    importlib.reload(config_mod)
    importlib.reload(pm_mod)

    pm = pm_mod.PortfolioManager()
    weights = pm.determine_target_weights({"AAPL": "Tech", "MSFT": "Tech", "JPM": "Fin"})

    assert config_mod.SECTOR_MODE is False
    assert weights == pytest.approx({"AAPL": 1 / 3, "MSFT": 1 / 3, "JPM": 1 / 3})


def test_sector_weight_mode(monkeypatch):
    """Sectors receive equal weight when SECTOR_MODE is enabled."""

    monkeypatch.setenv("SECTOR_MODE", "true")
    importlib.reload(config_mod)
    importlib.reload(pm_mod)

    pm = pm_mod.PortfolioManager()
    weights = pm.determine_target_weights({"AAPL": "Tech", "MSFT": "Tech", "JPM": "Fin"})

    assert config_mod.SECTOR_MODE is True
    assert weights["JPM"] == pytest.approx(0.5)
    assert weights["AAPL"] == pytest.approx(0.25)
    assert weights["MSFT"] == pytest.approx(0.25)

