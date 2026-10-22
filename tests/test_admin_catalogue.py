import io
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

import app as application


@pytest.fixture
def admin_client():
    email = f"catalogue-test-{uuid.uuid4().hex}@example.test"
    with application.app.app_context():
        admin = application.AdminAccount(
            name='Catalogue test',
            email=email,
            password_hash=application.generate_password_hash('test-admin-password'),
        )
        application.db.session.add(admin)
        application.db.session.commit()
        admin_id = admin.id

    client = application.app.test_client()
    response = client.post('/admin/login', data={'email': email, 'password': 'test-admin-password'})
    assert response.status_code == 302
    with client.session_transaction() as session:
        csrf_token = session['admin_csrf']
    yield client, {'X-CSRF-Token': csrf_token}

    with application.app.app_context():
        application.AdminAccount.query.filter_by(id=admin_id).delete()
        application.db.session.commit()


@pytest.fixture
def vendor_pair():
    vendors = []
    with application.app.app_context():
        for label in ('one', 'two'):
            email = f'vendor-{label}-{uuid.uuid4().hex}@example.test'
            vendor = application.VendorAccount(
                name=f'Test Vendor {label}',
                email=email,
                password_hash=application.generate_password_hash('test-vendor-password'),
            )
            application.db.session.add(vendor)
            vendors.append((email, vendor))
        application.db.session.commit()
        vendor_accounts = [(email, vendor.id) for email, vendor in vendors]
        vendor_ids = [vendor_id for _, vendor_id in vendor_accounts]

    clients = []
    for email, vendor_id in vendor_accounts:
        client = application.app.test_client()
        response = client.post('/vendor/login', data={
            'email': email,
            'password': 'test-vendor-password',
        })
        assert response.status_code == 302
        with client.session_transaction() as session:
            csrf_token = session['vendor_csrf']
        clients.append((client, {'X-CSRF-Token': csrf_token}, vendor_id))
    yield clients

    with application.app.app_context():
        for vendor_id in vendor_ids:
            for tour in application.Tour.query.filter_by(vendor_id=vendor_id).all():
                booking_ids = [
                    booking_id for (booking_id,) in application.db.session.query(application.Booking.id).filter_by(tour=tour.slug).all()
                ]
                if booking_ids:
                    application.BookingDispute.query.filter(application.BookingDispute.booking_id.in_(booking_ids)).delete(synchronize_session=False)
                application.Booking.query.filter_by(tour=tour.slug).delete()
                application.TourSchedule.query.filter_by(tour_slug=tour.slug).delete()
                application.Review.query.filter_by(target_type='tour', target_id=tour.slug).delete()
                application.db.session.delete(tour)
            for listing in application.Property.query.filter_by(vendor_id=vendor_id).all():
                application.Review.query.filter_by(target_type='property', target_id=listing.slug).delete()
                application.db.session.delete(listing)
            vendor = application.db.session.get(application.VendorAccount, vendor_id)
            if vendor:
                application.db.session.delete(vendor)
        application.db.session.commit()


def test_admin_operations_manage_accounts_bookings_refunds_disputes_and_analytics(admin_client, vendor_pair):
    admin, headers = admin_client
    vendor_client, vendor_headers, vendor_id = vendor_pair[0]
    customer_email = f'customer-{uuid.uuid4().hex}@example.test'
    with application.app.app_context():
        vendor_email = application.db.session.get(application.VendorAccount, vendor_id).email
        original_commission_rate = float(application.get_admin_setting('commission_rate', 15))
    if original_commission_rate != 15:
        assert admin.put('/api/admin/settings', json={'commission_rate': 15}, headers=headers).status_code == 200
    with application.app.app_context():
        customer = application.User(
            name='Operations Customer',
            email=customer_email,
            password_hash=application.generate_password_hash('customer-password'),
        )
        tour = application.Tour(
            slug=f'operations-tour-{vendor_id}',
            vendor_id=vendor_id,
            name='Operations Sailing',
            description='A tour used to test admin operations.',
            duration='Two hours',
            price=2500,
        )
        application.db.session.add_all([customer, tour])
        application.db.session.flush()
        departure = application.TourSchedule(
            tour_slug=tour.slug,
            starts_at=(datetime.now(ZoneInfo('Africa/Nairobi')).replace(tzinfo=None) + timedelta(days=8)).replace(second=0, microsecond=0),
            capacity=6,
            booked_count=2,
        )
        application.db.session.add(departure)
        application.db.session.flush()
        booking = application.Booking(
            user_id=customer.id,
            schedule_id=departure.id,
            name=customer.name,
            email=customer.email,
            phone='+254712345678',
            tour=tour.slug,
            date=departure.starts_at.date().isoformat(),
            time=departure.starts_at.strftime('%H:%M'),
            guests=2,
            amount=5000,
            commission_rate=15,
            payment_status='paid',
            status='confirmed',
        )
        application.db.session.add(booking)
        application.db.session.commit()
        booking_id = booking.id
        customer_id = customer.id
        departure_id = departure.id
        tour_slug = tour.slug

    response = admin.get('/api/admin/operations')
    assert response.status_code == 200
    operations = response.get_json()
    assert operations['settings'] == {
        'commission_rate': 15,
        'refund_policy': 'manual_review',
        'cancellation_window_hours': 48,
    }
    assert operations['analytics']['paid_revenue'] == 5000
    assert operations['analytics']['commission_earned'] == 750
    assert operations['analytics']['by_tour'][0]['tour_name'] == 'Operations Sailing'
    assert next(row for row in operations['customers'] if row['id'] == customer_id)['booking_count'] == 1

    assert admin.put('/api/admin/settings', json={'commission_rate': 21}, headers=headers).status_code == 400
    response = admin.put('/api/admin/settings', json={'commission_rate': 17.5}, headers=headers)
    assert response.status_code == 200
    assert response.get_json()['settings']['commission_rate'] == 17.5
    assert admin.put(
        '/api/admin/settings',
        json={'commission_rate': 17.5, 'refund_policy': 'automatic'},
        headers=headers,
    ).status_code == 400

    assert admin.post(
        f'/api/admin/users/customer/{customer_id}/status',
        json={'active': False},
        headers=headers,
    ).status_code == 200
    inactive_customer_login = application.app.test_client().post('/login', data={
        'email': customer_email,
        'password': 'customer-password',
    })
    assert inactive_customer_login.status_code == 302
    assert 'Invalid%20email' in inactive_customer_login.location
    assert admin.post(
        f'/api/admin/users/vendor/{vendor_id}/status',
        json={'active': False},
        headers=headers,
    ).status_code == 200
    assert vendor_client.get('/api/vendor/catalogue').status_code == 401
    inactive_login = application.app.test_client().post('/vendor/login', data={
        'email': vendor_email,
        'password': 'test-vendor-password',
    })
    assert inactive_login.status_code == 302
    assert 'Invalid%20vendor%20email' in inactive_login.location
    assert admin.post(
        f'/api/admin/users/customer/{customer_id}/status',
        json={'active': True},
        headers=headers,
    ).status_code == 200
    assert admin.post(
        f'/api/admin/users/vendor/{vendor_id}/status',
        json={'active': True},
        headers=headers,
    ).status_code == 200

    response = admin.post(
        f'/api/admin/bookings/{booking_id}/refund',
        json={'status': 'pending_review'},
        headers=headers,
    )
    assert response.status_code == 200
    response = admin.post(
        f'/api/admin/bookings/{booking_id}/refund',
        json={'status': 'approved'},
        headers=headers,
    )
    assert response.status_code == 200
    response = admin.post(
        f'/api/admin/bookings/{booking_id}/refund',
        json={'status': 'completed'},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.get_json()['gateway_refund_issued'] is False
    assert response.get_json()['booking']['payment_status'] == 'refunded'
    refunded_tour = next(
        row for row in admin.get('/api/admin/operations').get_json()['analytics']['by_tour']
        if row['tour'] == tour_slug
    )
    assert refunded_tour['paid_revenue'] == 0

    response = admin.post(
        f'/api/admin/bookings/{booking_id}/disputes',
        json={'reason': 'Customer reports a disagreement about the tour service.'},
        headers=headers,
    )
    assert response.status_code == 201
    dispute_id = response.get_json()['dispute']['id']
    assert admin.put(
        f'/api/admin/disputes/{dispute_id}',
        json={'resolution': 'Reviewed with the operator and documented the agreed outcome.'},
        headers=headers,
    ).status_code == 200
    assert admin.put(
        f'/api/admin/disputes/{dispute_id}',
        json={'resolution': 'Trying to resolve the same case a second time.'},
        headers=headers,
    ).status_code == 409

    assert admin.post(f'/api/admin/bookings/{booking_id}/cancel', headers=headers).status_code == 200
    with application.app.app_context():
        assert application.db.session.get(application.TourSchedule, departure_id).booked_count == 0
        assert application.db.session.get(application.Booking, booking_id).commission_rate == 15
        application.BookingDispute.query.filter_by(booking_id=booking_id).delete()
        application.db.session.delete(application.db.session.get(application.Booking, booking_id))
        application.db.session.delete(application.db.session.get(application.TourSchedule, departure_id))
        application.db.session.delete(application.db.session.get(application.User, customer_id))
        application.db.session.commit()
    assert admin.put(
        '/api/admin/settings',
        json={'commission_rate': original_commission_rate},
        headers=headers,
    ).status_code == 200


def test_admin_pages_and_catalogue_api_require_sign_in():
    client = application.app.test_client()

    assert client.get('/admin').status_code == 302
    assert client.get('/dashboard').status_code == 302
    assert client.get('/api/admin/catalogue').status_code == 401
    assert client.get('/api/admin/dashboard').status_code == 401


def test_admin_can_create_update_and_delete_tours(admin_client):
    client, headers = admin_client
    response = client.post('/api/admin/tours', json={
        'name': 'Test Sunset Sailing',
        'description': 'A test catalog tour.',
        'duration': 'Two hours',
        'price': 1200,
        'image_url': 'images/shela-village.webp',
    }, headers=headers)

    assert response.status_code == 201
    tour = response.get_json()['tour']
    assert tour['slug'] == 'test-sunset-sailing'
    assert application.calculate_booking_price(tour['slug'], 2) == 2400
    assert tour['slug'] in {item['slug'] for item in client.get('/api/catalogue').get_json()['tours']}

    response = client.put(f"/api/admin/tours/{tour['slug']}", json={
        'name': 'Updated Sunset Sailing',
        'description': 'Updated description.',
        'duration': 'Three hours',
        'price': 1500,
        'image_url': '',
    }, headers=headers)
    assert response.status_code == 200
    assert application.calculate_booking_price(tour['slug'], 2) == 3000

    assert client.delete(f"/api/admin/tours/{tour['slug']}", headers=headers).status_code == 204
    with pytest.raises(ValueError):
        application.calculate_booking_price(tour['slug'], 1)


def test_property_reviews_are_attached_to_the_selected_property(admin_client):
    client, headers = admin_client
    response = client.post('/api/admin/properties', json={
        'name': 'Test Shela Retreat',
        'property_type': 'villa',
        'location': 'Shela',
        'price_per_night': 7000,
        'guests': 4,
        'image_url': 'pictures/187747945.jpg',
        'description': 'A test property.',
    }, headers=headers)
    assert response.status_code == 201
    listing = response.get_json()['property']
    assert application.calculate_booking_price(listing['slug'], 2) == 14000

    response = client.post('/review-submit', json={
        'reviewer_name': 'Guest',
        'reviewer_email': 'guest@example.test',
        'rating': 5,
        'comment': 'Lovely stay.',
        'target_type': 'property',
        'target_id': listing['slug'],
    })
    assert response.status_code == 201
    assert response.get_json()['review']['place'] == listing['name']

    assert len(client.get('/reviews?target_type=property&target_id=' + listing['slug']).get_json()['reviews']) == 1
    assert client.get('/reviews?target_type=tour&target_id=' + listing['slug']).get_json()['reviews'] == []

    assert client.delete(f"/api/admin/properties/{listing['id']}", headers=headers).status_code == 204
    assert client.get('/reviews?target_type=property&target_id=' + listing['slug']).get_json()['reviews'] == []


def test_admin_can_manage_trending_destinations_and_other_admin_accounts(admin_client):
    client, headers = admin_client
    response = client.post('/api/admin/destinations', json={
        'name': 'Test Coast',
        'description': 'A destination for testing.',
        'image_url': 'pictures/187168867.jpg',
        'search_location': 'Test Coast',
    }, headers=headers)
    assert response.status_code == 201
    destination = response.get_json()['destination']
    assert destination in client.get('/api/catalogue').get_json()['destinations']

    response = client.put(f"/api/admin/destinations/{destination['slug']}", json={
        **destination,
        'description': 'Updated destination.',
    }, headers=headers)
    assert response.status_code == 200
    assert response.get_json()['destination']['description'] == 'Updated destination.'

    response = client.post('/api/admin/admins', json={
        'name': 'Second Admin',
        'email': f"second-{uuid.uuid4().hex}@example.test",
        'password': 'a-long-test-password',
    }, headers=headers)
    assert response.status_code == 201
    created_admin = response.get_json()['admin']
    with application.app.app_context():
        admin = application.db.session.get(application.AdminAccount, created_admin['id'])
        assert admin.password_hash != 'a-long-test-password'

    assert client.delete(f"/api/admin/destinations/{destination['slug']}", headers=headers).status_code == 204
    assert client.delete(f"/api/admin/admins/{created_admin['id']}", headers=headers).status_code == 204


def test_hospitality_page_is_removed_and_catalog_is_public():
    response = application.app.test_client().get('/hospitality.html')

    assert response.status_code == 404
    assert not application.os.path.exists(application.os.path.join(application.BASE_DIR, 'hospitality.html'))
    catalogue = application.app.test_client().get('/api/catalogue').get_json()
    assert catalogue['tours']
    assert catalogue['properties']
    assert catalogue['destinations']


def test_public_reviews_require_a_valid_catalog_listing():
    response = application.app.test_client().post('/review-submit', json={
        'reviewer_name': 'Guest',
        'reviewer_email': 'guest@example.test',
        'rating': 5,
        'comment': 'Unattached review.',
        'target_type': 'tour',
        'target_id': 'not-a-real-tour',
    })

    assert response.status_code == 400


def test_admin_mutations_require_csrf(admin_client):
    client, _ = admin_client

    response = client.post('/api/admin/tours', json={
        'name': 'No CSRF',
        'description': 'Should not be created.',
        'duration': 'One hour',
        'price': 1000,
    })

    assert response.status_code == 403


def test_admin_can_publish_and_remove_tour_availability(admin_client):
    client, headers = admin_client
    tour_response = client.post('/api/admin/tours', json={
        'name': 'Availability Test Tour',
        'description': 'A tour to test schedule management.',
        'duration': 'Two hours',
        'price': 1000,
    }, headers=headers)
    assert tour_response.status_code == 201
    slug = tour_response.get_json()['tour']['slug']
    starts_at = (datetime.now(ZoneInfo('Africa/Nairobi')).replace(tzinfo=None) + timedelta(days=5)).replace(second=0, microsecond=0)

    response = client.post('/api/admin/availability', json={
        'tour_slug': slug,
        'starts_at': starts_at.isoformat(timespec='minutes'),
        'capacity': 8,
    }, headers=headers)
    assert response.status_code == 201
    schedule = response.get_json()['schedule']
    assert schedule['capacity'] == 8
    assert schedule['remaining'] == 8
    assert schedule in client.get('/api/admin/availability').get_json()['schedules']

    response = client.put(f"/api/admin/availability/{schedule['id']}", json={
        'capacity': 12,
        'starts_at': starts_at.isoformat(timespec='minutes'),
    }, headers=headers)
    assert response.status_code == 200
    assert response.get_json()['schedule']['capacity'] == 12
    assert client.delete(f"/api/admin/availability/{schedule['id']}", headers=headers).status_code == 204
    assert client.delete(f'/api/admin/tours/{slug}', headers=headers).status_code == 204


def test_admin_dashboard_data_contains_summary_and_recent_activity(admin_client):
    client, _ = admin_client
    response = client.get('/api/admin/dashboard')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['total_submissions'] >= len(payload['recent_submissions'])
    assert payload['total_bookings'] >= len(payload['recent_bookings'])
    assert len(payload['recent_submissions']) <= 20
    assert len(payload['recent_bookings']) <= 20
    assert payload['csrf_token']
    assert client.post('/admin/logout', headers={
        'X-CSRF-Token': payload['csrf_token'],
        'Accept': 'application/json',
    }).status_code == 204
    assert client.get('/api/admin/dashboard').status_code == 401


def test_vendor_registration_requires_csrf_and_a_twelve_character_password():
    client = application.app.test_client()
    data = {
        'name': 'New Lamu Vendor',
        'email': f'new-vendor-{uuid.uuid4().hex}@example.test',
        'password': 'short',
    }

    assert client.post('/vendor/register', json=data).status_code == 403
    token_response = client.get('/api/vendor/registration-token')
    assert token_response.status_code == 200
    headers = {'X-CSRF-Token': token_response.get_json()['csrf_token']}
    assert client.post('/vendor/register', json=data, headers=headers).status_code == 400

    data['password'] = 'pass-1234567'
    response = client.post('/vendor/register', json=data, headers=headers)
    assert response.status_code == 201
    vendor_data = response.get_json()['vendor']
    assert vendor_data['email'] == data['email']
    assert client.get('/api/vendor/catalogue').get_json()['vendor']['id'] == vendor_data['id']

    with application.app.app_context():
        vendor = application.db.session.get(application.VendorAccount, vendor_data['id'])
        assert vendor.password_hash != data['password']
        application.db.session.delete(vendor)
        application.db.session.commit()


def test_vendor_can_manage_only_their_own_tours_and_properties(vendor_pair):
    first, second = vendor_pair
    first_client, first_headers, first_id = first
    second_client, second_headers, _ = second

    tour_response = first_client.post('/api/vendor/tours', json={
        'name': f'Vendor {first_id} Sailing',
        'description': 'A vendor-owned sailing experience.',
        'duration': 'Two hours',
        'price': 1800,
    }, headers=first_headers)
    property_response = first_client.post('/api/vendor/properties', json={
        'name': f'Vendor {first_id} Guest House',
        'property_type': 'guest house',
        'location': 'Shela',
        'price_per_night': 6000,
        'guests': 3,
        'description': 'A vendor-owned guest house.',
    }, headers=first_headers)
    assert tour_response.status_code == 201
    assert property_response.status_code == 201
    tour = tour_response.get_json()['tour']
    listing = property_response.get_json()['property']

    assert [item['slug'] for item in first_client.get('/api/vendor/catalogue').get_json()['tours']] == [tour['slug']]
    assert second_client.get('/api/vendor/catalogue').get_json()['tours'] == []
    assert second_client.put(f"/api/vendor/tours/{tour['slug']}", json=tour, headers=second_headers).status_code == 404
    assert second_client.delete(f"/api/vendor/properties/{listing['id']}", headers=second_headers).status_code == 404

    updated_tour = {
        **tour,
        'name': 'Updated vendor sailing',
        'price': 2200,
    }
    assert first_client.put(f"/api/vendor/tours/{tour['slug']}", json=updated_tour, headers=first_headers).status_code == 200
    assert first_client.delete(f"/api/vendor/tours/{tour['slug']}", headers=first_headers).status_code == 204
    assert first_client.delete(f"/api/vendor/properties/{listing['id']}", headers=first_headers).status_code == 204
    assert first_client.post('/vendor/logout', headers=first_headers).status_code == 204
    assert first_client.get('/api/vendor/catalogue').status_code == 401


def test_admin_can_remove_vendor_account_and_owned_listings(admin_client, vendor_pair):
    admin, admin_headers = admin_client
    vendor_client, vendor_headers, vendor_id = vendor_pair[0]
    response = vendor_client.post('/api/vendor/tours', json={
        'name': 'Vendor Deletion Test Tour',
        'description': 'A listing used to verify vendor removal.',
        'duration': 'One hour',
        'price': 1000,
    }, headers=vendor_headers)
    assert response.status_code == 201
    slug = response.get_json()['tour']['slug']

    response = admin.delete(f'/api/admin/vendors/{vendor_id}', headers=admin_headers)
    assert response.status_code == 204
    public_tours = application.app.test_client().get('/api/catalogue').get_json()['tours']
    assert slug not in {tour['slug'] for tour in public_tours}
    with application.app.app_context():
        assert application.db.session.get(application.VendorAccount, vendor_id) is None
        assert application.db.session.get(application.Tour, slug) is None


def test_vendor_can_view_and_advance_only_their_tour_bookings(monkeypatch, vendor_pair):
    first_client, first_headers, vendor_id = vendor_pair[0]
    second_client, second_headers, _ = vendor_pair[1]
    monkeypatch.setattr(application, 'send_booking_status_notification', lambda booking: True)
    starts_at = (datetime.now(ZoneInfo('Africa/Nairobi')).replace(tzinfo=None) + timedelta(days=7)).replace(second=0, microsecond=0)
    with application.app.app_context():
        tour = application.Tour(
            slug=f'vendor-booking-{vendor_id}',
            vendor_id=vendor_id,
            name='Vendor Booking Tour',
            description='A vendor booking workflow test.',
            duration='Two hours',
            price=1200,
        )
        schedule = application.TourSchedule(tour_slug=tour.slug, starts_at=starts_at, capacity=5, booked_count=2)
        application.db.session.add_all([tour, schedule])
        application.db.session.flush()
        booking = application.Booking(
            tour=tour.slug,
            schedule_id=schedule.id,
            name='Test Guest',
            email='test-guest@example.test',
            phone='+254712345678',
            date=starts_at.date().isoformat(),
            time=starts_at.strftime('%H:%M'),
            guests=2,
            amount=2400,
            payment_status='pending',
            status='requested',
        )
        application.db.session.add(booking)
        application.db.session.commit()
        booking_id, schedule_id = booking.id, schedule.id

    assert [item['id'] for item in first_client.get('/api/vendor/bookings').get_json()['bookings']] == [booking_id]
    assert second_client.get('/api/vendor/bookings').get_json()['bookings'] == []
    assert second_client.post(
        f'/api/vendor/bookings/{booking_id}/status',
        json={'status': 'confirmed'},
        headers=second_headers,
    ).status_code == 404
    assert first_client.post(
        f'/api/vendor/bookings/{booking_id}/status',
        json={'status': 'confirmed'},
        headers=first_headers,
    ).status_code == 409
    with application.app.app_context():
        application.db.session.get(application.Booking, booking_id).payment_status = 'paid'
        application.db.session.commit()

    for status in ('confirmed', 'in_preparation', 'completed'):
        response = first_client.post(
            f'/api/vendor/bookings/{booking_id}/status',
            json={'status': status},
            headers=first_headers,
        )
        assert response.status_code == 200
        assert response.get_json()['booking']['status'] == status
        assert response.get_json()['email_sent'] is True

    assert first_client.post(
        f'/api/vendor/bookings/{booking_id}/status',
        json={'status': 'cancelled'},
        headers=first_headers,
    ).status_code == 409
    with application.app.app_context():
        assert application.db.session.get(application.TourSchedule, schedule_id).booked_count == 2
        tour = application.db.session.get(application.Tour, f'vendor-booking-{vendor_id}')
        cancelled_schedule = application.TourSchedule(
            tour_slug=tour.slug,
            starts_at=starts_at + timedelta(days=1),
            capacity=3,
            booked_count=1,
        )
        application.db.session.add(cancelled_schedule)
        application.db.session.flush()
        cancelled_booking = application.Booking(
            tour=tour.slug,
            schedule_id=cancelled_schedule.id,
            name='Second Test Guest',
            email='second-guest@example.test',
            phone='+254700000000',
            date=cancelled_schedule.starts_at.date().isoformat(),
            time=cancelled_schedule.starts_at.strftime('%H:%M'),
            guests=1,
            amount=1200,
            payment_status='pending',
            status='requested',
        )
        application.db.session.add(cancelled_booking)
        application.db.session.commit()
        cancelled_booking_id, cancelled_schedule_id = cancelled_booking.id, cancelled_schedule.id

    cancelled_response = first_client.post(
        f'/api/vendor/bookings/{cancelled_booking_id}/status',
        json={'status': 'cancelled'},
        headers=first_headers,
    )
    assert cancelled_response.status_code == 200
    assert cancelled_response.get_json()['booking']['status'] == 'cancelled'
    with application.app.app_context():
        assert application.db.session.get(application.TourSchedule, cancelled_schedule_id).booked_count == 0


def test_vendor_image_upload_checks_role_csrf_and_image_signature(tmp_path, monkeypatch, vendor_pair):
    client, headers, vendor_id = vendor_pair[0]
    monkeypatch.setattr(application, 'BASE_DIR', str(tmp_path))
    image = b'\x89PNG\r\n\x1a\n' + b'test-image-data'

    assert application.app.test_client().post('/api/vendor/uploads').status_code == 401
    assert client.post('/api/vendor/uploads', data={
        'image': (io.BytesIO(image), 'cover.png'),
    }, content_type='multipart/form-data').status_code == 403

    response = client.post('/api/vendor/uploads', data={
        'image': (io.BytesIO(b'not an image'), 'cover.png'),
    }, headers=headers, content_type='multipart/form-data')
    assert response.status_code == 400

    response = client.post('/api/vendor/uploads', data={
        'image': (io.BytesIO(image), 'cover.png'),
    }, headers=headers, content_type='multipart/form-data')
    assert response.status_code == 201
    image_url = response.get_json()['image_url']
    assert image_url.startswith(f'uploads/vendors/{vendor_id}/')
    assert client.get(f'/{image_url}').data == image


def test_frontend_routes_serve_the_built_react_app(tmp_path, monkeypatch, admin_client):
    dist = tmp_path / 'dist'
    assets = dist / 'assets'
    assets.mkdir(parents=True)
    (dist / 'index.html').write_text('<div id="root">React app</div>', encoding='utf-8')
    (assets / 'main.js').write_text('console.log("React");', encoding='utf-8')
    monkeypatch.setattr(application, 'FRONTEND_DIST', str(dist))

    client, _ = admin_client

    assert b'React app' in client.get('/').data
    assert b'React app' in client.get('/tours.html').data
    assert b'React app' in client.get('/login').data
    assert b'React app' in client.get('/admin/login').data
    assert b'React app' in client.get('/dashboard').data
    assert b'React app' in client.get('/vendor/login').data
    assert b'React app' in client.get('/vendor/register').data
    assert b'console.log("React")' in client.get('/assets/main.js').data


def test_contact_form_accepts_json_for_the_react_frontend(monkeypatch):
    monkeypatch.setattr(application, 'send_email_notification', lambda submission: False)
    client = application.app.test_client()

    response = client.post('/contact-submit', json={
        'name': 'React visitor',
        'email': 'visitor@example.test',
        'subject': 'A Lamu question',
        'message': 'I would like to learn more about the tours.',
    })

    assert response.status_code == 201
    assert response.get_json() == {
        'message': 'Your message has been received.',
        'email_sent': False,
    }
