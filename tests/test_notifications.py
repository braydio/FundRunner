import fundrunner.services.notifications as notifications
import fundrunner.alpaca.portfolio_manager as portfolio_manager
import fundrunner.alpaca.risk_manager as risk_manager


def test_notify_dispatch(monkeypatch):
    emails = []
    discord = []
    monkeypatch.setattr(notifications, 'send_email', lambda s, b: emails.append((s, b)))
    monkeypatch.setattr(notifications, 'send_discord', lambda m: discord.append(m))
    notifications.notify('Subject', 'Body')
    assert emails == [('Subject', 'Body')]
    assert discord == ['**Subject**\nBody']


def test_portfolio_manager_rebalance_sends_notification(monkeypatch):
    calls = []
    monkeypatch.setattr(portfolio_manager, 'notify', lambda s, m: calls.append((s, m)))
    pm = portfolio_manager.PortfolioManager()
    monkeypatch.setattr(pm.trader, 'buy', lambda *a, **k: {'id': '1'})
    pm.rebalance_portfolio([{'symbol': 'AAPL', 'qty': 1, 'side': 'buy'}])
    assert calls and calls[0][0] == 'Rebalance Trade Executed'


def test_risk_manager_threshold_triggers_notification(monkeypatch):
    calls = []
    monkeypatch.setattr(risk_manager, 'notify', lambda s, m: calls.append((s, m)))
    rm = risk_manager.RiskManager()
    assert rm.check_threshold('drawdown', 5, 3) is True
    assert calls and 'drawdown' in calls[0][1]
    calls.clear()
    assert rm.check_threshold('drawdown', 2, 3) is False
    assert not calls
