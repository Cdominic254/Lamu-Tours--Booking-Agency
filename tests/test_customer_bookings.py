from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import uuid

import pytest

import app as application


@pytest.fixture
def customer_trip(monkeypatch):
    monkeypatch.setattr(application, 'STRIPE_SECRET_KEY', 'sk_test_checkout_mock')
    email = f'customer-{uuid.uuid4().hex}@example.test'
    slug = f'customer-trip-{uuid.uuid4().hex}'
    with application.app.app_context():
        user = application.User(
            name='Booking Customer',
            email=email,
            password_hash=application.generate_password_hash('customer-test-password'),
        )
        tour = application.Tour(
            slug=slug,
            name='Customer Test Island Tour',
            description='A tour used to test the customer booking flow.',
            duration='Two hours',
            price=1500,
            category='Dhow & Island Hopping',
            itinerary='Meet your guide\nSail along the coast',
            inclusions='Local guide',
            exclusions='Meals',
            pickup_point='Lamu waterfront',
            min_group_size=1,
            max_group_size=6,
        )
        application.db.session.add_all([user, tour])
        application.db.session.commit()
        user_id = user.id

        start = (datetime.now(ZoneInfo('Africa/Nairobi')).replace(tzinfo=None) + timedelta(days=6)).replace(second=0, microsecond=0)
        near_start = (datetime.now(ZoneInfo('Africa/Nairobi')).replace(tzinfo=None) + timedelta(hours=24)).replace(second=0, microsecond=0)
        slots = [
            application.TourSchedule(tour_slug=slug, starts_at=start, capacity=4),
            application.TourSchedule(tour_slug=slug, starts_at=start + timedelta(days=1), capacity=4),
            application.TourSchedule(tour_slug=slug, starts_at=near_start, capacity=2),
        ]
        application.db.session.add_all(slots)
        application.db.session.commit()
        schedule_ids = [slot.id for slot in slots]

    monkeypatch.setattr(application, 'send_booking_confirmation', lambda booking, checkout_url=None: True)
    def mock_checkout_session(**params):
        session_id = f"cs_test_{params['metadata']['booking_id']}"
        return type('CheckoutSession', (), {
            'id': session_id,
            'url': f'https://checkout.stripe.test/{session_id}',
        })()

    monkeypatch.setattr(application.stripe.checkout.Session, 'create', mock_checkout_session)
    monkeypatch.setattr(application, 'expire_booking_checkout', lambda booking: None)
    client = application.app.test_client()
    response = client.post('/login', data={'email': email, 'password': 'customer-test-password'})
    assert response.status_code == 302
    with client.session_transaction() as session:
        csrf_token = session['customer_csrf']

    yield {
        'client': client,
        'csrf': csrf_token,
        'email': email,
        'slug': slug,
        'user_id': user_id,
        'schedule_ids': schedule_ids,
        'starts_at': start,
    }

    with application.app.app_context():
        application.Booking.query.filter_by(user_id=user_id).delete()
        application.TourSchedule.query.filter_by(tour_slug=slug).delete()
        application.db.session.delete(application.db.session.get(application.Tour, slug))
        application.db.session.delete(application.db.session.get(application.User, user_id))
        application.db.session.commit()


def booking_payload(trip, schedule_id, guests=1):
    return {
        'name': 'Booking Customer',
        'email': trip['email'],
        'country_code': '+254',
        'phone': '712345678',
        'tour': trip['slug'],
        'schedule_id': schedule_id,
        'guests': guests,
        'date': 'ignored-for-scheduled-tour',
        'time': 'ignored-for-scheduled-tour',
        'message': '',
    }


def test_customer_can_book_view_reschedule_and_cancel_while_capacity_is_reserved(customer_trip):
    trip = customer_trip
    client = trip['client']
    first_slot, second_slot, _ = trip['schedule_ids']
    response = client.post('/booking-confirmation', json=booking_payload(trip, first_slot, guests=2))

    assert response.status_code == 201
    result = response.get_json()
    booking_id = result['booking']['id']
    assert result['email_sent'] is True
    assert result['managed'] is True
    assert result['booking']['status'] == 'requested'
    assert result['checkout_url'].startswith('https://checkout.stripe.test/')
    assert result['booking']['date'] == trip['starts_at'].date().isoformat()

    with application.app.app_context():
        assert application.db.session.get(application.TourSchedule, first_slot).booked_count == 2
        saved_booking = application.db.session.get(application.Booking, booking_id)
        assert saved_booking.commission_rate == float(application.get_admin_setting('commission_rate', 15))

    response = client.get('/api/customer/bookings')
    assert response.status_code == 200
    assert [booking['id'] for booking in response.get_json()['bookings']] == [booking_id]

    other_client = application.app.test_client()
    assert other_client.get('/api/customer/bookings').status_code == 401

    response = client.post(
        f'/api/customer/bookings/{booking_id}/reschedule',
        json={'schedule_id': second_slot},
        headers={'X-CSRF-Token': trip['csrf']},
    )
    assert response.status_code == 200
    assert response.get_json()['booking']['schedule_id'] == second_slot
    with application.app.app_context():
        assert application.db.session.get(application.TourSchedule, first_slot).booked_count == 0
        assert application.db.session.get(application.TourSchedule, second_slot).booked_count == 2

    response = client.post(
        f'/api/customer/bookings/{booking_id}/cancel',
        headers={'X-CSRF-Token': trip['csrf']},
    )
    assert response.status_code == 200
    assert response.get_json()['booking']['status'] == 'cancelled'
    with application.app.app_context():
        assert application.db.session.get(application.TourSchedule, second_slot).booked_count == 0


def test_capacity_is_enforced_and_customer_changes_are_blocked_inside_48_hours(customer_trip):
    trip = customer_trip
    client = trip['client']
    _, _, limited_slot = trip['schedule_ids']
    payload = booking_payload(trip, limited_slot, guests=2)

    response = client.post('/booking-confirmation', json=payload)
    assert response.status_code == 201
    available = client.get(f"/api/tours/{trip['slug']}/availability").get_json()['schedules']
    assert limited_slot not in {item['id'] for item in available}
    assert client.post('/booking-confirmation', json=payload).status_code == 409

    booking_id = response.get_json()['booking']['id']
    blocked = client.post(
        f'/api/customer/bookings/{booking_id}/cancel',
        headers={'X-CSRF-Token': trip['csrf']},
    )
    assert blocked.status_code == 400
    assert '48 hours' in blocked.get_json()['error']


def test_booking_requires_a_valid_departure_and_customer_csrf(customer_trip):
    trip = customer_trip
    client = trip['client']
    payload = booking_payload(trip, 999999)

    response = client.post('/booking-confirmation', json=payload)
    assert response.status_code == 400

    booked = client.post('/booking-confirmation', json=booking_payload(trip, trip['schedule_ids'][0]))
    assert booked.status_code == 201
    booking_id = booked.get_json()['booking']['id']
    assert client.post(f'/api/customer/bookings/{booking_id}/cancel').status_code == 403


def test_booking_is_blocked_when_stripe_is_not_configured(customer_trip, monkeypatch):
    trip = customer_trip
    monkeypatch.setattr(application, 'STRIPE_SECRET_KEY', '')

    response = trip['client'].post(
        '/booking-confirmation',
        json=booking_payload(trip, trip['schedule_ids'][0]),
    )

    assert response.status_code == 503
    with application.app.app_context():
        assert application.Booking.query.filter_by(user_id=trip['user_id']).count() == 0
        assert application.db.session.get(application.TourSchedule, trip['schedule_ids'][0]).booked_count == 0


def test_checkout_session_uses_booking_total_and_kes(customer_trip, monkeypatch):
    trip = customer_trip
    captured = {}

    def create_session(**params):
        captured.update(params)
        return type('CheckoutSession', (), {'id': 'cs_test_created', 'url': 'https://checkout.stripe.test/pay'})()

    monkeypatch.setattr(application.stripe.checkout.Session, 'create', create_session)
    with application.app.test_request_context('/', base_url='https://lamutours.test'):
        booking = application.Booking(
            user_id=trip['user_id'],
            schedule_id=trip['schedule_ids'][0],
            name='Booking Customer',
            email=trip['email'],
            phone='+254712345678',
            tour=trip['slug'],
            date=trip['starts_at'].date().isoformat(),
            time=trip['starts_at'].strftime('%H:%M'),
            guests=1,
            amount=1500,
            payment_status='pending',
            status='requested',
        )
        application.db.session.add(booking)
        application.db.session.commit()

        checkout_url = application.create_stripe_checkout_session(booking)

        assert checkout_url == 'https://checkout.stripe.test/pay'
        assert captured['line_items'][0]['price_data']['currency'] == 'kes'
        assert captured['line_items'][0]['price_data']['unit_amount'] == 150000
        assert captured['customer_email'] == trip['email']
        assert captured['metadata']['booking_id'] == str(booking.id)
        assert captured['idempotency_key'] == f'booking-checkout-{booking.id}'
        assert captured['success_url'].startswith('https://lamutours.co.ke/payment-success?')
        assert captured['cancel_url'].startswith('https://lamutours.co.ke/payment-cancel?')
        assert booking.stripe_session_id == 'cs_test_created'


def test_success_redirect_does_not_confirm_an_unpaid_checkout(customer_trip, monkeypatch):
    trip = customer_trip
    response = trip['client'].post(
        '/booking-confirmation',
        json=booking_payload(trip, trip['schedule_ids'][0]),
    )
    booking_id = response.get_json()['booking']['id']
    monkeypatch.setattr(application.stripe.checkout.Session, 'retrieve', lambda session_id: {
        'id': session_id,
        'metadata': {'booking_id': str(booking_id)},
        'client_reference_id': str(booking_id),
        'status': 'open',
        'payment_status': 'unpaid',
        'currency': 'kes',
        'amount_total': 150000,
    })

    result = trip['client'].get(
        f'/payment-success?booking_id={booking_id}&session_id=cs_test_{booking_id}'
    )

    assert b'Payment not confirmed' in result.data
    with application.app.app_context():
        booking = application.db.session.get(application.Booking, booking_id)
        assert booking.payment_status == 'pending'
        assert booking.status == 'requested'


def test_completed_stripe_checkout_confirms_matching_booking(customer_trip, monkeypatch):
    trip = customer_trip
    response = trip['client'].post(
        '/booking-confirmation',
        json=booking_payload(trip, trip['schedule_ids'][0]),
    )
    booking_id = response.get_json()['booking']['id']
    monkeypatch.setattr(application.stripe.checkout.Session, 'retrieve', lambda session_id: {
        'id': session_id,
        'metadata': {'booking_id': str(booking_id)},
        'client_reference_id': str(booking_id),
        'status': 'complete',
        'payment_status': 'paid',
        'currency': 'kes',
        'amount_total': 150000,
    })

    result = trip['client'].get(
        f'/payment-success?booking_id={booking_id}&session_id=cs_test_{booking_id}'
    )

    assert b'Payment confirmed' in result.data
    with application.app.app_context():
        booking = application.db.session.get(application.Booking, booking_id)
        assert booking.payment_status == 'paid'
        assert booking.status == 'confirmed'


def test_expired_checkout_webhook_releases_reserved_capacity(customer_trip, monkeypatch):
    trip = customer_trip
    response = trip['client'].post(
        '/booking-confirmation',
        json=booking_payload(trip, trip['schedule_ids'][0]),
    )
    booking_id = response.get_json()['booking']['id']
    session_data = {
        'id': f'cs_test_{booking_id}',
        'metadata': {'booking_id': str(booking_id)},
    }
    monkeypatch.setattr(application, 'STRIPE_WEBHOOK_SECRET', 'whsec_test')
    monkeypatch.setattr(application.stripe.Webhook, 'construct_event', lambda *args: {
        'type': 'checkout.session.expired',
        'data': {'object': session_data},
    })

    webhook_response = trip['client'].post('/stripe-webhook', data=b'{}', headers={'Stripe-Signature': 'test'})

    assert webhook_response.status_code == 204
    with application.app.app_context():
        booking = application.db.session.get(application.Booking, booking_id)
        schedule = application.db.session.get(application.TourSchedule, trip['schedule_ids'][0])
        assert booking.payment_status == 'cancelled'
        assert booking.status == 'cancelled'
        assert schedule.booked_count == 0


def test_completed_checkout_webhook_confirms_payment(customer_trip, monkeypatch):
    trip = customer_trip
    response = trip['client'].post(
        '/booking-confirmation',
        json=booking_payload(trip, trip['schedule_ids'][0]),
    )
    booking_id = response.get_json()['booking']['id']
    session_data = {
        'id': f'cs_test_{booking_id}',
        'client_reference_id': str(booking_id),
        'metadata': {'booking_id': str(booking_id)},
        'status': 'complete',
        'payment_status': 'paid',
        'currency': 'kes',
        'amount_total': 150000,
    }
    monkeypatch.setattr(application, 'STRIPE_WEBHOOK_SECRET', 'whsec_test')
    monkeypatch.setattr(application.stripe.Webhook, 'construct_event', lambda *args: {
        'type': 'checkout.session.completed',
        'data': {'object': session_data},
    })

    webhook_response = trip['client'].post('/stripe-webhook', data=b'{}', headers={'Stripe-Signature': 'test'})

    assert webhook_response.status_code == 204
    with application.app.app_context():
        booking = application.db.session.get(application.Booking, booking_id)
        assert booking.payment_status == 'paid'
        assert booking.status == 'confirmed'
