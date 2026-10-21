import app as application


def clear_currency_cache():
    with application._currency_cache_lock:
        application._exchange_rates_cache.update({
            'expires_at': 0.0,
            'rates': None,
            'updated_at': None,
        })
        application._geolocation_cache.clear()


def test_currency_endpoint_detects_country_currency_and_returns_rates(monkeypatch):
    clear_currency_cache()

    def fake_fetch_json(url):
        if 'open.er-api.com' in url:
            return {
                'result': 'success',
                'rates': {'KES': 1, 'USD': 0.0077, 'EUR': 0.0068},
                'time_last_update_utc': 'Wed, 14 Oct 2026 00:00:00 +0000',
            }
        assert url == 'https://ipapi.co/8.8.8.8/json/'
        return {'country_code': 'US', 'currency': 'USD'}

    monkeypatch.setattr(application, '_fetch_json', fake_fetch_json)
    client = application.app.test_client()
    response = client.get(
        '/api/currency',
        headers={'X-Forwarded-For': '8.8.8.8'},
        environ_overrides={'REMOTE_ADDR': '10.0.0.1'},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['currency'] == 'USD'
    assert payload['country_code'] == 'US'
    assert payload['detected'] is True
    assert payload['rates']['KES'] == 1
    assert payload['rates']['USD'] == 0.0077


def test_currency_endpoint_falls_back_to_kes_for_private_ip(monkeypatch):
    clear_currency_cache()
    requested_urls = []

    def fake_fetch_json(url):
        requested_urls.append(url)
        return {
            'result': 'success',
            'rates': {'KES': 1, 'EUR': 0.0068},
            'time_last_update_utc': None,
        }

    monkeypatch.setattr(application, '_fetch_json', fake_fetch_json)
    response = application.app.test_client().get(
        '/api/currency',
        environ_overrides={'REMOTE_ADDR': '127.0.0.1'},
    )

    assert response.status_code == 200
    assert response.get_json()['currency'] == 'KES'
    assert response.get_json()['detected'] is False
    assert requested_urls == ['https://open.er-api.com/v6/latest/KES']


def test_currency_endpoint_returns_service_error_if_exchange_rates_unavailable(monkeypatch):
    clear_currency_cache()

    def fail_fetch_json(_url):
        raise ValueError('service unavailable')

    monkeypatch.setattr(application, '_fetch_json', fail_fetch_json)
    response = application.app.test_client().get('/api/currency')

    assert response.status_code == 503
    assert response.get_json() == {'error': 'Currency rates are temporarily unavailable.'}


def test_currency_endpoint_uses_kes_when_geolocation_fails(monkeypatch):
    clear_currency_cache()

    def fake_fetch_json(url):
        if 'open.er-api.com' in url:
            return {
                'result': 'success',
                'rates': {'KES': 1, 'USD': 0.0077},
                'time_last_update_utc': None,
            }
        raise ValueError('geolocation unavailable')

    monkeypatch.setattr(application, '_fetch_json', fake_fetch_json)
    response = application.app.test_client().get(
        '/api/currency',
        headers={'X-Forwarded-For': '8.8.8.8'},
        environ_overrides={'REMOTE_ADDR': '10.0.0.1'},
    )

    assert response.status_code == 200
    assert response.get_json()['currency'] == 'KES'
    assert response.get_json()['detected'] is False
    assert response.get_json()['rates']['USD'] == 0.0077
