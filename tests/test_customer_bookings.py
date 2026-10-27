from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import uuid

import pytest

import app as application


@pytest.fixture
def customer_trip(monkeypatch):
    monkeypatch.setattr(application, 'is_daraja_configured', lambda: True)
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

    monkeypatch.setattr(application, 'send_booking_confirmation', lambda booking, **kwargs: True)
    def mock_stk_push(phone_number, amount, booking_id):
        return {
            'checkout_request_id': f'ws_CO_{booking_id}',
            'merchant_request_id': f'merchant_{booking_id}',
            'customer_message': 'STK prompt sent.',
        }

    monkeypatch.setattr(application, 'initiate_stk_push', mock_stk_push)
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
    assert result['booking']['payment_status'] == 'pending'
    assert result['payment_reference']
    assert result['message'] == 'STK prompt sent.'
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
    assert response.status_code == 409
    assert 'M-Pesa request is still pending' in response.get_json()['error']
    with application.app.app_context():
        assert application.db.session.get(application.TourSchedule, second_slot).booked_count == 2


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
    assert blocked.status_code == 409
    assert 'M-Pesa request is still pending' in blocked.get_json()['error']


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


def test_booking_is_blocked_when_daraja_is_not_configured(customer_trip, monkeypatch):
    trip = customer_trip
    monkeypatch.setattr(application, 'is_daraja_configured', lambda: False)

    response = trip['client'].post(
        '/booking-confirmation',
        json=booking_payload(trip, trip['schedule_ids'][0]),
    )

    assert response.status_code == 503
    with application.app.app_context():
        assert application.Booking.query.filter_by(user_id=trip['user_id']).count() == 0
        assert application.db.session.get(application.TourSchedule, trip['schedule_ids'][0]).booked_count == 0


def test_stk_push_uses_kenyan_phone_booking_total_and_booking_id(customer_trip, monkeypatch):
    trip = customer_trip
    captured = {}

    def request_stk_push(phone_number, amount, booking_id):
        captured.update(phone_number=phone_number, amount=amount, booking_id=booking_id)
        return {
            'checkout_request_id': 'ws_CO_test',
            'merchant_request_id': 'merchant_test',
            'customer_message': 'Prompt sent.',
        }

    monkeypatch.setattr(application, 'initiate_stk_push', request_stk_push)
    with application.app.app_context():
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

        payment_request = application.create_daraja_stk_push(booking)

        assert payment_request['customer_message'] == 'Prompt sent.'
        assert captured == {
            'phone_number': '254712345678',
            'amount': 1500,
            'booking_id': booking.id,
        }
        assert booking.checkout_request_id == 'ws_CO_test'
        assert booking.merchant_request_id == 'merchant_test'


def _daraja_callback(booking, result_code, metadata=None):
    callback = {
        'MerchantRequestID': booking.merchant_request_id,
        'CheckoutRequestID': booking.checkout_request_id,
        'ResultCode': result_code,
        'ResultDesc': 'The service request is processed.',
    }
    if metadata is not None:
        callback['CallbackMetadata'] = {
            'Item': [{'Name': key, 'Value': value} for key, value in metadata.items()],
        }
    return {'Body': {'stkCallback': callback}}


def test_m_pesa_callback_marks_paid_only_after_daraja_query_verification(customer_trip, monkeypatch):
    trip = customer_trip
    response = trip['client'].post(
        '/booking-confirmation',
        json=booking_payload(trip, trip['schedule_ids'][0]),
    )
    booking_data = response.get_json()['booking']
    with application.app.app_context():
        booking = application.db.session.get(application.Booking, booking_data['id'])
        callback = _daraja_callback(booking, 0, {
            'Amount': 1500,
            'MpesaReceiptNumber': 'TST123ABC',
            'TransactionDate': 20260516123456,
            'PhoneNumber': 254712345678,
        })
    monkeypatch.setattr(application, 'query_stk_push', lambda checkout_id: {
        'ResponseCode': '0',
        'ResultCode': '0',
        'CheckoutRequestID': f"ws_CO_{booking_data['id']}",
    })

    result = trip['client'].post('/daraja/callback', json=callback)

    assert result.status_code == 204
    with application.app.app_context():
        booking = application.db.session.get(application.Booking, booking_data['id'])
        assert booking.payment_status == 'paid'
        assert booking.status == 'confirmed'
        assert booking.mpesa_receipt_number == 'TST123ABC'


def test_payment_status_requires_opaque_booking_reference(customer_trip):
    trip = customer_trip
    response = trip['client'].post(
        '/booking-confirmation',
        json=booking_payload(trip, trip['schedule_ids'][0]),
    )
    payment_reference = response.get_json()['payment_reference']

    result = trip['client'].get(f'/api/payment-status/{payment_reference}')
    assert result.status_code == 200
    assert result.get_json()['payment_status'] == 'pending'
    assert trip['client'].get('/api/payment-status/not-a-reference').status_code == 404


def test_m_pesa_callback_does_not_confirm_mismatched_amount(customer_trip, monkeypatch):
    trip = customer_trip
    response = trip['client'].post(
        '/booking-confirmation',
        json=booking_payload(trip, trip['schedule_ids'][0]),
    )
    booking_data = response.get_json()['booking']
    with application.app.app_context():
        booking = application.db.session.get(application.Booking, booking_data['id'])
        callback = _daraja_callback(booking, 0, {
            'Amount': 100,
            'MpesaReceiptNumber': 'TST123ABC',
            'PhoneNumber': 254712345678,
        })
    monkeypatch.setattr(application, 'query_stk_push', lambda checkout_id: {
        'ResponseCode': '0',
        'ResultCode': '0',
        'CheckoutRequestID': f"ws_CO_{booking_data['id']}",
    })

    result = trip['client'].post('/daraja/callback', json=callback)

    assert result.status_code == 400
    with application.app.app_context():
        booking = application.db.session.get(application.Booking, booking_data['id'])
        assert booking.payment_status == 'pending'
        assert booking.status == 'requested'


def test_failed_m_pesa_callback_releases_reserved_capacity(customer_trip, monkeypatch):
    trip = customer_trip
    response = trip['client'].post(
        '/booking-confirmation',
        json=booking_payload(trip, trip['schedule_ids'][0]),
    )
    booking_data = response.get_json()['booking']
    with application.app.app_context():
        booking = application.db.session.get(application.Booking, booking_data['id'])
        callback = _daraja_callback(booking, 1032)
    monkeypatch.setattr(application, 'query_stk_push', lambda checkout_id: {
        'ResponseCode': '0',
        'ResultCode': '1032',
        'CheckoutRequestID': f"ws_CO_{booking_data['id']}",
    })

    result = trip['client'].post('/daraja/callback', json=callback)

    assert result.status_code == 204
    with application.app.app_context():
        booking = application.db.session.get(application.Booking, booking_data['id'])
        schedule = application.db.session.get(application.TourSchedule, trip['schedule_ids'][0])
        assert booking.payment_status == 'failed'
        assert booking.status == 'cancelled'
        assert schedule.booked_count == 0


def test_unknown_stk_request_outcome_keeps_capacity_reserved(customer_trip, monkeypatch):
    trip = customer_trip

    def unknown_outcome(*args):
        raise application.DarajaError('Request timed out.', outcome_unknown=True)

    monkeypatch.setattr(application, 'initiate_stk_push', unknown_outcome)
    response = trip['client'].post(
        '/booking-confirmation',
        json=booking_payload(trip, trip['schedule_ids'][0]),
    )

    assert response.status_code == 202
    with application.app.app_context():
        booking = application.Booking.query.filter_by(user_id=trip['user_id']).order_by(application.Booking.id.desc()).first()
        schedule = application.db.session.get(application.TourSchedule, trip['schedule_ids'][0])
        assert booking.payment_status == 'pending'
        assert schedule.booked_count == 1


def test_m_pesa_bookings_require_a_kenyan_phone_number(customer_trip):
    trip = customer_trip
    payload = booking_payload(trip, trip['schedule_ids'][0])
    payload['country_code'] = '+1'

    response = trip['client'].post('/booking-confirmation', json=payload)

    assert response.status_code == 400
    assert 'Kenyan phone number' in response.get_json()['error']
