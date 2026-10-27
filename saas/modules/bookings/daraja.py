import base64
import ipaddress
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo


class DarajaError(RuntimeError):
    def __init__(self, message, *, outcome_unknown=False):
        super().__init__(message)
        self.outcome_unknown = outcome_unknown


_TOKEN_CACHE = {}
_TOKEN_LOCK = threading.Lock()
_NAIROBI = ZoneInfo('Africa/Nairobi')


def _configuration():
    environment = os.environ.get('DARAJA_ENV', 'sandbox').strip().lower()
    if environment not in {'sandbox', 'production'}:
        raise DarajaError('DARAJA_ENV must be sandbox or production.')

    config = {
        'environment': environment,
        'base_url': (
            'https://sandbox.safaricom.co.ke'
            if environment == 'sandbox'
            else 'https://api.safaricom.co.ke'
        ),
        'consumer_key': os.environ.get('DARAJA_CONSUMER_KEY', '').strip(),
        'consumer_secret': os.environ.get('DARAJA_CONSUMER_SECRET', '').strip(),
        'shortcode': os.environ.get('DARAJA_SHORTCODE', '').strip(),
        'passkey': os.environ.get('DARAJA_PASSKEY', '').strip(),
        'callback_url': os.environ.get('DARAJA_CALLBACK_URL', '').strip(),
    }
    missing = [
        key for key in ('consumer_key', 'consumer_secret', 'shortcode', 'passkey', 'callback_url')
        if not config[key]
    ]
    if missing:
        raise DarajaError('Daraja payment configuration is incomplete.')

    callback = urllib.parse.urlparse(config['callback_url'])
    callback_host = (callback.hostname or '').lower()
    is_local_host = callback_host in {'localhost'} or callback_host.endswith(('.localhost', '.local', '.internal'))
    try:
        is_local_host = is_local_host or not ipaddress.ip_address(callback_host).is_global
    except ValueError:
        pass
    if callback.scheme != 'https' or not callback.netloc or is_local_host:
        raise DarajaError('DARAJA_CALLBACK_URL must be a publicly reachable HTTPS URL.')
    return config


def is_configured():
    try:
        _configuration()
    except DarajaError:
        return False
    return True


def _request_json(url, *, method='POST', payload=None, headers=None, outcome_unknown=False):
    data = None if payload is None else json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode('utf-8')
            details = json.loads(body)
            message = details.get('errorMessage') or details.get('ResponseDescription') or 'Daraja rejected the request.'
        except (UnicodeDecodeError, json.JSONDecodeError):
            message = 'Daraja rejected the request.'
        raise DarajaError(
            message,
            outcome_unknown=outcome_unknown and exc.code >= 500,
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise DarajaError('Daraja could not be reached.', outcome_unknown=outcome_unknown) from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DarajaError('Daraja returned an invalid response.', outcome_unknown=outcome_unknown) from exc

    if not isinstance(result, dict):
        raise DarajaError('Daraja returned an invalid response.', outcome_unknown=outcome_unknown)
    return result


def _access_token(config):
    cache_key = (config['consumer_key'], config['consumer_secret'], config['environment'])
    now = time.monotonic()
    with _TOKEN_LOCK:
        cached = _TOKEN_CACHE.get(cache_key)
        if cached and cached[1] > now:
            return cached[0]

        credentials = base64.b64encode(
            f"{config['consumer_key']}:{config['consumer_secret']}".encode('utf-8')
        ).decode('ascii')
        response = _request_json(
            f"{config['base_url']}/oauth/v1/generate?grant_type=client_credentials",
            method='GET',
            headers={'Authorization': f'Basic {credentials}'},
        )
        token = response.get('access_token')
        if not isinstance(token, str) or not token:
            raise DarajaError('Daraja did not return an access token.')
        try:
            expires_in = int(response.get('expires_in', 3600))
        except (TypeError, ValueError):
            expires_in = 3600
        _TOKEN_CACHE[cache_key] = (token, now + max(expires_in - 60, 1))
        return token


def _password(config, timestamp):
    raw = f"{config['shortcode']}{config['passkey']}{timestamp}".encode('utf-8')
    return base64.b64encode(raw).decode('ascii')


def initiate_stk_push(phone_number, amount, booking_id):
    config = _configuration()
    timestamp = datetime.now(_NAIROBI).strftime('%Y%m%d%H%M%S')
    token = _access_token(config)
    response = _request_json(
        f"{config['base_url']}/mpesa/stkpush/v1/processrequest",
        payload={
            'BusinessShortCode': config['shortcode'],
            'Password': _password(config, timestamp),
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': int(amount),
            'PartyA': phone_number,
            'PartyB': config['shortcode'],
            'PhoneNumber': phone_number,
            'CallBackURL': config['callback_url'],
            'AccountReference': f'Lamu-{booking_id}',
            'TransactionDesc': f'Lamu Tours booking {booking_id}',
        },
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
        outcome_unknown=True,
    )
    if str(response.get('ResponseCode', '')) != '0':
        raise DarajaError(response.get('ResponseDescription') or 'Daraja could not start the M-Pesa payment.')

    checkout_request_id = response.get('CheckoutRequestID')
    merchant_request_id = response.get('MerchantRequestID')
    if not isinstance(checkout_request_id, str) or not checkout_request_id:
        raise DarajaError('Daraja accepted the payment but did not return a checkout reference.', outcome_unknown=True)
    return {
        'checkout_request_id': checkout_request_id,
        'merchant_request_id': merchant_request_id,
        'customer_message': response.get('CustomerMessage', 'Check your phone for the M-Pesa payment prompt.'),
    }


def query_stk_push(checkout_request_id):
    config = _configuration()
    timestamp = datetime.now(_NAIROBI).strftime('%Y%m%d%H%M%S')
    token = _access_token(config)
    return _request_json(
        f"{config['base_url']}/mpesa/stkpushquery/v1/query",
        payload={
            'BusinessShortCode': config['shortcode'],
            'Password': _password(config, timestamp),
            'Timestamp': timestamp,
            'CheckoutRequestID': checkout_request_id,
        },
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
    )
