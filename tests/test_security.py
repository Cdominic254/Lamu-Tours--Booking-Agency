import pytest

import app as application


@pytest.fixture
def application_client():
    return application.app.test_client()


def test_login_attempts_are_rate_limited_by_ip_and_account(application_client):
    responses = [
        application_client.post(
            '/login',
            data={'email': 'guessed-user@example.test', 'password': 'incorrect'},
            environ_overrides={'REMOTE_ADDR': '203.0.113.41'},
        )
        for _ in range(6)
    ]

    assert [response.status_code for response in responses[:5]] == [302] * 5
    assert responses[5].status_code == 429


def test_public_review_submissions_are_rate_limited(application_client):
    payload = {
        'reviewer_name': 'Test Reviewer',
        'reviewer_email': 'reviewer@example.test',
        'target_type': 'tour',
        'target_id': 'not-a-tour',
        'rating': 5,
        'comment': 'A review used to exercise the public rate limit.',
    }
    responses = [
        application_client.post(
            '/review-submit',
            json=payload,
            environ_overrides={'REMOTE_ADDR': '203.0.113.42'},
        )
        for _ in range(6)
    ]

    assert [response.status_code for response in responses[:5]] == [400] * 5
    assert responses[5].status_code == 429


def test_booking_checkout_creation_is_rate_limited(application_client, monkeypatch):
    monkeypatch.setattr(application, 'is_daraja_configured', lambda: False)
    responses = [
        application_client.post(
            '/booking-confirmation',
            json={},
            environ_overrides={'REMOTE_ADDR': '203.0.113.43'},
        )
        for _ in range(11)
    ]

    assert [response.status_code for response in responses[:10]] == [503] * 10
    assert responses[10].status_code == 429


def test_public_reviews_reject_overlong_fields(application_client):
    with application_client.application.app_context():
        tour = application.Tour.query.first()
        assert tour is not None
        slug = tour.slug

    response = application_client.post('/review-submit', json={
        'reviewer_name': 'Test Reviewer',
        'reviewer_email': 'reviewer@example.test',
        'target_type': 'tour',
        'target_id': slug,
        'rating': 5,
        'comment': 'x' * 3001,
    })

    assert response.status_code == 400
    assert 'error' in response.get_json()


@pytest.mark.parametrize('url', [
    'file:///etc/passwd',
    'http://open.er-api.com/v6/latest/KES',
    'https://attacker.example/data',
])
def test_currency_fetch_rejects_untrusted_urls(url):
    with pytest.raises(ValueError, match='URL is not allowed'):
        application._fetch_json(url)


def test_catalog_image_upload_fails_clearly_on_vercel(monkeypatch):
    monkeypatch.setenv('VERCEL', '1')

    with application.app.test_request_context('/api/vendor/uploads', method='POST'):
        response, status_code = application.save_catalog_image('vendors/1')

    assert status_code == 503
    assert 'persistent object storage' in response['error']
