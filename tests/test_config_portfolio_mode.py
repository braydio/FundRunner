import importlib

from fundrunner.utils import config as config_mod


def test_portfolio_manager_mode(monkeypatch):
    monkeypatch.setenv("PORTFOLIO_MANAGER_MODE", "true")
    cfg = importlib.reload(config_mod)
    assert cfg.PORTFOLIO_MANAGER_MODE is True
    monkeypatch.delenv("PORTFOLIO_MANAGER_MODE", raising=False)
    cfg = importlib.reload(config_mod)
    assert cfg.PORTFOLIO_MANAGER_MODE is False
