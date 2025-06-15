from services.trading_daemon import app, state


def test_status_endpoint():
    with app.test_client() as client:
        resp = client.get('/status')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'mode' in data and 'paused' in data


def test_pause_resume():
    with app.test_client() as client:
        client.post('/pause')
        assert state.paused is True
        client.post('/resume')
        assert state.paused is False
