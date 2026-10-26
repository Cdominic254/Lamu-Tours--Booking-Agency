import urllib.error

import pytest

from saas.modules.bookings import daraja


@pytest.fixture
def daraja_environment(monkeypatch):
    values = {
        'DARAJA_ENV': 'sandbox',
        'DARAJA_CONSUMER_KEY': 'sandbox-consumer-key',
        'DARAJA_CONSUMER_SECRET': 'sandbox-consumer-secret',
        'DARAJA_SHORTCODE': '174379',
        'DARAJA_PASSKEY': 'sandbox-passkey',
        'DARAJA_CALLBACK_URL': 'https://example.com/daraja/callback',
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    return values


def test_stk_push_builds_sandbox_request(daraja_environment, monkeypatch):
    calls = []

    def request_json(url, **kwargs):
        calls.append((url, kwargs))
        return {
            'ResponseCode': '0',
            'CheckoutRequestID': 'ws_CO_123',
            'MerchantRequestID': 'merchant_123',
            'CustomerMessage': 'Prompt sent.',
        }

    monkeypatch.setattr(daraja, '_access_token', lambda config: 'sandbox-token')
    monkeypatch.setattr(daraja, '_request_json', request_json)

    result = daraja.initiate_stk_push('254712345678', 1500, 123)

    url, request = calls[0]
    assert url == 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
    assert request['payload']['BusinessShortCode'] == '174379'
    assert request['payload']['TransactionType'] == 'CustomerPayBillOnline'
    assert request['payload']['Amount'] == 1500
    assert request['payload']['PhoneNumber'] == '254712345678'
    assert request['payload']['PartyA'] == '254712345678'
    assert request['payload']['AccountReference'] == 'Lamu-123'
    assert request['payload']['CallBackURL'] == daraja_environment['DARAJA_CALLBACK_URL']
    assert request['headers']['Authorization'] == 'Bearer sandbox-token'
    assert result == {
        'checkout_request_id': 'ws_CO_123',
        'merchant_request_id': 'merchant_123',
        'customer_message': 'Prompt sent.',
    }


def test_production_uses_live_daraja_host(daraja_environment, monkeypatch):
    monkeypatch.setenv('DARAJA_ENV', 'production')
    monkeypatch.setattr(daraja, '_access_token', lambda config: 'live-token')
    calls = []

    def request_json(url, **kwargs):
        calls.append(url)
        return {'ResponseCode': '0', 'CheckoutRequestID': 'ws_CO_live'}

    monkeypatch.setattr(daraja, '_request_json', request_json)

    daraja.initiate_stk_push('254712345678', 2500, 42)

    assert calls == ['https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest']


def test_daraja_configuration_requires_public_https_callback(daraja_environment, monkeypatch):
    monkeypatch.setenv('DARAJA_CALLBACK_URL', 'http://localhost/daraja/callback')

    assert daraja.is_configured() is False
    with pytest.raises(daraja.DarajaError, match='publicly reachable HTTPS'):
        daraja.initiate_stk_push('254712345678', 1500, 1)


def test_unknown_stk_transport_outcome_is_not_treated_as_a_rejection(monkeypatch):
    def unavailable(*args, **kwargs):
        raise urllib.error.URLError('connection timed out')

    monkeypatch.setattr(daraja.urllib.request, 'urlopen', unavailable)

    with pytest.raises(daraja.DarajaError) as error:
        daraja._request_json(
            'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest',
            payload={},
            outcome_unknown=True,
        )

    assert error.value.outcome_unknown is True
