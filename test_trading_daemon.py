import json
from services.trading_daemon import DaemonState, create_app


def test_daemon_state_defaults():
    state = DaemonState()
    assert state.mode == "stocks"
    assert not state.paused
    assert state.trade_count == 0
    assert state.daily_pl == 0.0


def test_status_endpoint():
    state = DaemonState()
    app, _ = create_app(state)
    client = app.test_client()
    resp = client.get("/status")
    data = json.loads(resp.data)
    assert resp.status_code == 200
    assert data["mode"] == "stocks"
