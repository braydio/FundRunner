from fundrunner.services.trading_daemon import app, state


def test_status_endpoint():
    client = app.test_client()
    resp = client.get('/status')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['mode'] == state.mode
    assert data['portfolio_active'] == state.portfolio_active


def test_mode_change():
    client = app.test_client()
    resp = client.post('/mode', json={'mode': 'options'})
    assert resp.status_code == 200
    assert state.mode == 'options'
    resp = client.post('/mode', json={'mode': 'stock'})
    assert resp.status_code == 200
    assert state.mode == 'stock'


def test_pause_resume():
    client = app.test_client()
    client.post('/pause')
    assert state.paused is True
    client.post('/resume')
    assert state.paused is False


def test_portfolio_start_stop():
    client = app.test_client()
    client.post('/portfolio/start')
    assert state.portfolio_active is True
    client.post('/portfolio/stop')
    assert state.portfolio_active is False
