import ipaddress
import json
import math
import os
import re
import secrets
import smtplib
import tempfile
import threading
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from functools import wraps
from email.message import EmailMessage

import stripe
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import Flask, redirect, render_template, request, send_from_directory, render_template_string, session
from sqlalchemy import case, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from saas.extensions import db
from saas.modules.bookings.models import Booking, BookingDispute
from saas.modules.bookings.settings import AdminSetting
from saas.modules.bookings.service import (
    LAMU_TIMEZONE,
    calculate_booking_price as calculate_booking_price_service,
    parse_local_datetime,
    release_schedule,
    reserve_schedule,
    save_booking as save_booking_service,
)
from saas.modules.catalog.models import Destination, Property, Review, Tour, TourSchedule
from saas.modules.identity.models import AdminAccount, User, VendorAccount
from saas.modules.messaging.models import Submission

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
FRONTEND_DIST = os.path.join(BASE_DIR, 'frontend', 'dist')

EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USERNAME = os.environ.get('EMAIL_USERNAME', '')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
EMAIL_FROM = os.environ.get('EMAIL_FROM', EMAIL_USERNAME)
EMAIL_TO = os.environ.get('EMAIL_TO', 'info@lamutours.com')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() in ('1', 'true', 'yes')
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'false').lower() in ('1', 'true', 'yes')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
SITE_URL = os.environ.get('SITE_URL', 'https://lamutours.co.ke').strip().rstrip('/')
IS_PRODUCTION = (
    os.environ.get('FLASK_ENV', '').lower() == 'production'
    or os.environ.get('VERCEL') == '1'
    or (bool(os.environ.get('SITE_URL')) and SITE_URL.startswith('https://'))
)
RATE_LIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI', 'memory://')
if IS_PRODUCTION and RATE_LIMIT_STORAGE_URI.startswith('memory://'):
    raise RuntimeError('Configure RATELIMIT_STORAGE_URI with a shared Redis backend in production.')
SESSION_SECRET_KEY = os.environ.get('SECRET_KEY')
if IS_PRODUCTION and not SESSION_SECRET_KEY:
    raise RuntimeError('Configure a persistent SECRET_KEY in production.')

CURRENCY_CACHE_TTL = 60 * 60 * 12
CURRENCY_API_TIMEOUT = 4
_currency_cache_lock = threading.Lock()
_exchange_rates_cache = {'expires_at': 0.0, 'rates': None, 'updated_at': None}
_geolocation_cache = {}

app = Flask(__name__, static_folder=None)
app.config['SECRET_KEY'] = SESSION_SECRET_KEY or secrets.token_hex(32)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = IS_PRODUCTION or os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() in ('1', 'true', 'yes')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri=RATE_LIMIT_STORAGE_URI,
    headers_enabled=True,
)
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
sqlite_path = os.path.join(tempfile.gettempdir() if os.environ.get('VERCEL') else BASE_DIR, 'submissions.db')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or f'sqlite:///{sqlite_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}
db.init_app(app)

def ensure_booking_payment_columns():
    inspector = db.inspect(db.engine)
    booking_columns = {column['name'] for column in inspector.get_columns('booking')}
    with db.engine.begin() as connection:
        if 'amount' not in booking_columns:
            connection.execute(text('ALTER TABLE booking ADD COLUMN amount FLOAT NOT NULL DEFAULT 0.0'))
        if 'payment_status' not in booking_columns:
            connection.execute(text("ALTER TABLE booking ADD COLUMN payment_status VARCHAR(30) NOT NULL DEFAULT 'pending'"))
        if 'stripe_session_id' not in booking_columns:
            connection.execute(text('ALTER TABLE booking ADD COLUMN stripe_session_id VARCHAR(255)'))
        if 'user_id' not in booking_columns:
            connection.execute(text('ALTER TABLE booking ADD COLUMN user_id INTEGER'))
        if 'schedule_id' not in booking_columns:
            connection.execute(text('ALTER TABLE booking ADD COLUMN schedule_id INTEGER'))
        if 'status' not in booking_columns:
            connection.execute(text("ALTER TABLE booking ADD COLUMN status VARCHAR(30) NOT NULL DEFAULT 'requested'"))
        if 'commission_rate' not in booking_columns:
            connection.execute(text('ALTER TABLE booking ADD COLUMN commission_rate FLOAT NOT NULL DEFAULT 15.0'))
        if 'refund_status' not in booking_columns:
            connection.execute(text("ALTER TABLE booking ADD COLUMN refund_status VARCHAR(30) NOT NULL DEFAULT 'none'"))


def ensure_identity_columns():
    with db.engine.begin() as connection:
        for table in ('user', 'vendor_account'):
            if db.inspect(connection).has_table(table):
                columns = {column['name'] for column in db.inspect(connection).get_columns(table)}
                if 'is_active' not in columns:
                    connection.execute(text(f'ALTER TABLE {table} ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE'))


def ensure_admin_settings():
    for key, value in {
        'commission_rate': '15',
        'refund_policy': 'manual_review',
        'cancellation_window_hours': '48',
    }.items():
        if not db.session.get(AdminSetting, key):
            db.session.add(AdminSetting(key=key, value=value))
    db.session.commit()


def get_admin_setting(key, default):
    setting = db.session.get(AdminSetting, key)
    return setting.value if setting else str(default)


def ensure_catalog_columns():
    inspector = db.inspect(db.engine)
    table_columns = {table: {column['name'] for column in inspector.get_columns(table)}
                     for table in ('property', 'review', 'tour') if inspector.has_table(table)}
    with db.engine.begin() as connection:
        if 'slug' not in table_columns.get('property', set()):
            connection.execute(text('ALTER TABLE property ADD COLUMN slug VARCHAR(160)'))
        if 'vendor_id' not in table_columns.get('property', set()):
            connection.execute(text('ALTER TABLE property ADD COLUMN vendor_id INTEGER'))
        if 'vendor_id' not in table_columns.get('tour', set()):
            connection.execute(text('ALTER TABLE tour ADD COLUMN vendor_id INTEGER'))
        tour_columns = table_columns.get('tour', set())
        for column, declaration in {
            'category': "VARCHAR(100) NOT NULL DEFAULT 'Island experiences'",
            'itinerary': "TEXT NOT NULL DEFAULT ''",
            'inclusions': "TEXT NOT NULL DEFAULT ''",
            'exclusions': "TEXT NOT NULL DEFAULT ''",
            'pickup_point': "VARCHAR(200) NOT NULL DEFAULT 'Lamu Town waterfront'",
            'min_group_size': 'INTEGER NOT NULL DEFAULT 1',
            'max_group_size': 'INTEGER NOT NULL DEFAULT 12',
        }.items():
            if column not in tour_columns:
                connection.execute(text(f'ALTER TABLE tour ADD COLUMN {column} {declaration}'))
        review_columns = table_columns.get('review', set())
        if 'target_type' not in review_columns:
            connection.execute(text('ALTER TABLE review ADD COLUMN target_type VARCHAR(20)'))
        if 'target_id' not in review_columns:
            connection.execute(text('ALTER TABLE review ADD COLUMN target_id VARCHAR(160)'))

    properties = Property.query.filter((Property.slug.is_(None)) | (Property.slug == '')).all()
    for property_listing in properties:
        property_listing.slug = unique_slug(property_listing.name, Property, property_listing.id)
    if properties:
        db.session.commit()
    categories = {
        'dhow': 'Dhow & Island Hopping',
        'sandbank': 'Dhow & Island Hopping',
        'old-town': 'Lamu Old Town Walk',
        'cultural': 'Lamu Old Town Walk',
        'day-trips': 'Island Day Trips',
    }
    for slug, category in categories.items():
        tour = db.session.get(Tour, slug)
        if tour and tour.category == 'Island experiences':
            tour.category = category
    db.session.commit()


DEFAULT_TOURS = (
    ('dhow', 'Dhow Trips', "Enjoy traditional dhow sailing around Lamu's coastline with snorkeling and island stops.", 'Half day', 8500, 'images/shela-lamu-kenya-09.jpg'),
    ('old-town', 'Old Town Walks', 'Explore the historic streets, architecture, and marketplaces of Lamu Old Town.', '3 hours', 3500, "images/Lamu_Fort_Museum's.jpg"),
    ('sandbank', 'Sandbank Picnics', 'Relax on a private sandbank with picnic lunch, swimming, and beach activities.', 'Half day', 7000, 'images/shela-village.webp'),
    ('fishing', 'Fishing Trips', 'Go deep-sea fishing with local crew and enjoy fresh catch barbecue.', 'Full day', 12000, 'images/Lamu_coast.jpg'),
    ('water-sports', 'Water Sports', 'Experience adrenaline with jet skiing, windsurfing, and paddleboarding in clear waters.', 'Half day', 9500, 'images/Spiritedpursuit_leelitumbe-106_lamu_kenya.webp'),
    ('day-trips', 'Day Trips', 'Explore nearby islands and coastal attractions on a full-day guided excursion.', 'Full day', 9000, 'images/Spiritedpursuit_leelitumbe-49_lamu_kenya.webp'),
    ('cultural', 'Cultural Tours', 'Visit museums, traditional workshops, and attend local cultural performances.', '4 hours', 4000, 'images/Riadha_Mosque_in_Lamu.jpg'),
)

DEFAULT_TOUR_DETAILS = {
    'dhow': {
        'itinerary': 'Meet your crew at the Lamu waterfront\nSail along the coastline and island channels\nReturn to the waterfront',
        'inclusions': 'Dhow and local crew\nCoastal sailing experience',
        'exclusions': 'Meals and personal expenses',
        'pickup_point': 'Lamu Town waterfront',
    },
    'old-town': {
        'itinerary': 'Meet your local guide in Lamu Old Town\nExplore historic lanes and landmarks\nReturn to the meeting point',
        'inclusions': 'Local walking guide',
        'exclusions': 'Entry fees and personal purchases',
        'pickup_point': 'Lamu Old Town waterfront',
    },
    'sandbank': {
        'itinerary': 'Depart by dhow from Lamu\nEnjoy time on a nearby sandbank\nSail back to Lamu',
        'inclusions': 'Dhow transfer\nPicnic lunch',
        'exclusions': 'Personal expenses',
        'pickup_point': 'Lamu Town waterfront',
    },
    'fishing': {
        'itinerary': 'Meet the fishing crew\nSail to local fishing grounds\nReturn to shore with the crew',
        'inclusions': 'Boat and local fishing crew',
        'exclusions': 'Personal fishing equipment',
        'pickup_point': 'Lamu Town waterfront',
    },
    'water-sports': {
        'itinerary': 'Meet the activity team\nChoose from available water activities\nReturn to the launch point',
        'inclusions': 'Activity briefing',
        'exclusions': 'Optional activities not selected at booking',
        'pickup_point': 'Confirm with the activity team',
    },
    'day-trips': {
        'itinerary': 'Meet your local guide\nExplore a nearby island or coastal destination\nReturn to Lamu',
        'inclusions': 'Local guide',
        'exclusions': 'Meals and destination entry fees',
        'pickup_point': 'Lamu Town waterfront',
    },
    'cultural': {
        'itinerary': 'Meet your local guide\nVisit cultural landmarks and local workshops\nReturn to the meeting point',
        'inclusions': 'Local cultural guide',
        'exclusions': 'Entry fees and personal purchases',
        'pickup_point': 'Lamu Old Town waterfront',
    },
}

DEFAULT_PROPERTIES = (
    ('shela-guest-house', 'Shela Village Guest House', 'guest house', 'Shela', 4500, 2, 'images/shela-village.webp', 'Comfortable guest house in Shela village.'),
    ('old-town-hotel', 'Old Town Swahili Hotel', 'hotel', 'Lamu Old Town', 6500, 3, "images/Lamu_Fort_Museum's.jpg", 'A Swahili hotel close to the history and culture of Lamu Old Town.'),
    ('manda-beach-home', 'Manda Island Beach Home', 'home', 'Manda Island', 10000, 5, 'images/Lamu_coast.jpg', 'An island home with spacious ocean views.'),
    ('shela-palm-villa', 'Shela Palm Villa', 'villa', 'Shela', 12500, 4, 'pictures/187747945.jpg', 'A private villa close to Shela beach.'),
    ('mjini-budget-hotel', 'Lamu Mjini Budget Hotel', 'hotel', 'Lamu Mjini', 5500, 2, 'pictures/292079957.jpg', 'An affordable hotel in Lamu Mjini.'),
    ('kipungani-guest-house', 'Kipungani Coast Guest House', 'guest house', 'Kipungani', 5000, 3, 'pictures/611137747.jpg', 'A quiet guest house along the Kipungani coast.'),
    ('manda-ocean-villa', 'Manda Ocean Villa', 'villa', 'Manda Island', 16000, 6, 'pictures/552000169.jpg', 'A private ocean villa on Manda Island.'),
)

DEFAULT_DESTINATIONS = (
    ('shela', 'Shela', 'Beach apartments and peaceful villas.', 'pictures/187747945.jpg', 'Shela'),
    ('lamu-old-town', 'Lamu Old Town', 'Swahili stays close to history and culture.', "pictures/292079957.jpg", 'Old Town'),
    ('manda-island', 'Manda Island', 'Ocean homes and spacious private villas.', 'pictures/552000169.jpg', 'Manda'),
    ('kipungani', 'Kipungani', 'Quiet guest houses along the coast.', 'pictures/611137747.jpg', 'Kipungani'),
    ('lamu-mjini', 'Lamu Mjini', 'Affordable city stays and apartments.', 'pictures/460469483.jpg', 'Mjini'),
    ('lamu-coast', 'Lamu Coast', 'Waterfront escapes for every kind of traveler.', 'pictures/187168867.jpg', 'Lamu'),
)


def unique_slug(value, model, current_id=None):
    base = re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-') or 'listing'
    slug = base
    suffix = 2
    while True:
        query = model.query.filter_by(slug=slug)
        if current_id is not None:
            query = query.filter(model.id != current_id) if hasattr(model, 'id') else query.filter(model.slug != current_id)
        if not query.first():
            return slug
        slug = f'{base}-{suffix}'
        suffix += 1


def seed_catalogue():
    for slug, name, description, duration, price, image_url in DEFAULT_TOURS:
        tour = db.session.get(Tour, slug)
        if not tour:
            tour = Tour(slug=slug, name=name, description=description, duration=duration, price=price, image_url=image_url)
            db.session.add(tour)
        defaults = DEFAULT_TOUR_DETAILS[slug]
        if not tour.itinerary:
            tour.itinerary = defaults['itinerary']
        if not tour.inclusions:
            tour.inclusions = defaults['inclusions']
        if not tour.exclusions:
            tour.exclusions = defaults['exclusions']
        if tour.pickup_point == 'Lamu Town waterfront':
            tour.pickup_point = defaults['pickup_point']

    for slug, name, property_type, location, price, guests, image_url, description in DEFAULT_PROPERTIES:
        if not Property.query.filter_by(slug=slug).first():
            db.session.add(Property(
                slug=slug,
                owner_name='Lamu Tours',
                owner_email='admin@lamutours.com',
                name=name,
                property_type=property_type,
                location=location,
                price_per_night=price,
                guests=guests,
                image_url=image_url,
                description=description,
            ))

    for slug, name, description, image_url, search_location in DEFAULT_DESTINATIONS:
        if not db.session.get(Destination, slug):
            db.session.add(Destination(
                slug=slug,
                name=name,
                description=description,
                image_url=image_url,
                search_location=search_location,
            ))
    db.session.commit()

    legacy_reviews = Review.query.filter(Review.target_type.is_(None)).all()
    for review in legacy_reviews:
        tour = Tour.query.filter(db.func.lower(Tour.name) == review.place.lower()).first()
        listing = Property.query.filter(db.func.lower(Property.name) == review.place.lower()).first()
        if tour:
            review.target_type, review.target_id = 'tour', tour.slug
        elif listing:
            review.target_type, review.target_id = 'property', listing.slug
    if legacy_reviews:
        db.session.commit()


def bootstrap_admin_account():
    email = os.environ.get('ADMIN_EMAIL', '').strip().lower()
    password = os.environ.get('ADMIN_PASSWORD', '')
    if not email or not password or AdminAccount.query.count():
        return
    db.session.add(AdminAccount(
        name=os.environ.get('ADMIN_NAME', 'Administrator').strip() or 'Administrator',
        email=email,
        password_hash=generate_password_hash(password),
    ))
    db.session.commit()


def is_admin_logged_in():
    admin_id = session.get('admin_id')
    return bool(admin_id and db.session.get(AdminAccount, admin_id))


def get_current_vendor():
    vendor_id = session.get('vendor_id')
    vendor = db.session.get(VendorAccount, vendor_id) if vendor_id else None
    return vendor if vendor and vendor.is_active else None


def auth_attempt_key():
    email = request.form.get('email', '').strip().lower()[:120]
    return f'{get_remote_address()}:{email}'


def is_vendor_logged_in():
    return get_current_vendor() is not None


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_admin_logged_in():
            if request.path.startswith('/api/'):
                return {'error': 'Admin sign-in is required.'}, 401
            return redirect('/admin/login')
        return view(*args, **kwargs)
    return wrapped


def vendor_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_vendor_logged_in():
            if request.path.startswith('/api/'):
                return {'error': 'Vendor sign-in is required.'}, 401
            return redirect('/vendor/login')
        return view(*args, **kwargs)
    return wrapped


def customer_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = session.get('user_id')
        user = db.session.get(User, user_id) if user_id else None
        if not user or not user.is_active:
            return {'error': 'Sign in to view and manage your bookings.'}, 401
        return view(*args, **kwargs)
    return wrapped


def valid_admin_csrf():
    token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
    return bool(token and secrets.compare_digest(token, session.get('admin_csrf', '')))


def require_admin_csrf():
    if not valid_admin_csrf():
        return {'error': 'Your session expired. Refresh the page and try again.'}, 403
    return None


def valid_vendor_csrf():
    token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
    return bool(token and secrets.compare_digest(token, session.get('vendor_csrf', '')))


def require_vendor_csrf():
    if not valid_vendor_csrf():
        return {'error': 'Your session expired. Refresh the page and try again.'}, 403
    return None


def require_customer_csrf():
    token = request.headers.get('X-CSRF-Token')
    if not token or not secrets.compare_digest(token, session.get('customer_csrf', '')):
        return {'error': 'Your session expired. Refresh the page and try again.'}, 403
    return None


def require_vendor_registration_csrf():
    token = request.headers.get('X-CSRF-Token')
    expected = session.get('vendor_registration_csrf', '')
    if not token or not expected or not secrets.compare_digest(token, expected):
        return {'error': 'Refresh the page before creating a vendor account.'}, 403
    return None


def safe_image_url(value):
    image_url = str(value or '').strip()
    if not image_url:
        return None
    if image_url.startswith(('https://', 'http://')):
        return image_url
    if image_url.startswith(('images/', 'pictures/', 'uploads/')) and '..' not in image_url.split('/'):
        return image_url
    raise ValueError('Image must use an http(s) URL or a path under images/, pictures/, or uploads/.')


with app.app_context():
    db.create_all()
    ensure_booking_payment_columns()
    ensure_identity_columns()
    ensure_catalog_columns()
    ensure_admin_settings()
    seed_catalogue()
    bootstrap_admin_account()


def save_submission(submission: dict) -> Submission:
    new_submission = Submission(
        name=submission['name'],
        email=submission['email'],
        subject=submission['subject'],
        message=submission['message'],
        timestamp=datetime.fromisoformat(submission['timestamp'][:-1]) if submission.get('timestamp') else datetime.utcnow(),
        email_sent=submission.get('email_sent', False)
    )
    db.session.add(new_submission)
    db.session.commit()
    return new_submission


def calculate_booking_price(tour: str, guests: int) -> int:
    return calculate_booking_price_service(tour, guests, app)


def save_booking(booking: dict) -> Booking:
    return save_booking_service(booking)


def create_stripe_checkout_session(booking: Booking):
    if not STRIPE_SECRET_KEY:
        raise RuntimeError('Stripe is not configured. Set STRIPE_SECRET_KEY to enable payments.')

    line_item_name = booking.tour.replace('-', ' ').title()
    line_total = int(round(booking.amount * 100))
    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        customer_email=booking.email,
        client_reference_id=str(booking.id),
        line_items=[{
            'price_data': {
                'currency': 'kes',
                'unit_amount': line_total,
                'product_data': {
                    'name': f'Lamu booking: {line_item_name}',
                    'description': f'{booking.guests} guest(s) · booking #{booking.id}'
                },
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=f"{SITE_URL}/payment-success?booking_id={booking.id}&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{SITE_URL}/payment-cancel?booking_id={booking.id}",
        metadata={'booking_id': str(booking.id)},
        idempotency_key=f'booking-checkout-{booking.id}',
    )
    booking.stripe_session_id = checkout_session.id
    db.session.commit()
    return checkout_session.url


def confirm_stripe_checkout(checkout_session):
    booking_id = checkout_session.get('metadata', {}).get('booking_id')
    session_id = checkout_session.get('id')
    if not booking_id or not str(booking_id).isdigit() or not session_id:
        return None

    booking = db.session.get(Booking, int(booking_id))
    if (
        not booking
        or booking.stripe_session_id != session_id
        or checkout_session.get('client_reference_id') != str(booking.id)
        or checkout_session.get('status') != 'complete'
        or checkout_session.get('payment_status') != 'paid'
        or checkout_session.get('currency', '').lower() != 'kes'
        or checkout_session.get('amount_total') != int(round(booking.amount * 100))
        or booking.payment_status == 'refunded'
        or booking.payment_status == 'cancelled'
        or booking.status == 'cancelled'
    ):
        return None

    already_paid = booking.payment_status == 'paid'
    booking.payment_status = 'paid'
    if booking.status != 'cancelled':
        booking.status = 'confirmed'
    db.session.commit()
    if not already_paid:
        send_booking_confirmation(booking)
    return booking


def expire_booking_checkout(booking: Booking):
    if not booking.stripe_session_id or booking.payment_status != 'pending':
        return
    if not STRIPE_SECRET_KEY:
        raise RuntimeError('Stripe is not configured.')
    checkout_session = stripe.checkout.Session.retrieve(booking.stripe_session_id)
    if checkout_session.status == 'open':
        stripe.checkout.Session.expire(booking.stripe_session_id)


def expire_booking_from_webhook(checkout_session):
    booking_id = checkout_session.get('metadata', {}).get('booking_id')
    session_id = checkout_session.get('id')
    if not booking_id or not str(booking_id).isdigit() or not session_id:
        return

    booking = db.session.get(Booking, int(booking_id))
    if not booking or booking.stripe_session_id != session_id or booking.payment_status != 'pending':
        return

    try:
        release_schedule(booking.schedule_id, booking.guests)
    except ValueError:
        db.session.rollback()
        app.logger.exception('Could not release availability for expired checkout %s.', session_id)
        return
    booking.payment_status = 'cancelled'
    booking.status = 'cancelled'
    db.session.commit()


def send_email_notification(submission: dict) -> bool:
    if not (EMAIL_HOST and EMAIL_USERNAME and EMAIL_PASSWORD and EMAIL_FROM and EMAIL_TO):
        app.logger.warning('Email notification skipped: missing SMTP configuration.')
        return False

    message = EmailMessage()
    message['Subject'] = f"New contact message from {submission['name']}"
    message['From'] = EMAIL_FROM
    message['To'] = EMAIL_TO
    message.set_content(
        f"Name: {submission['name']}\n"
        f"Email: {submission['email']}\n"
        f"Subject: {submission['subject']}\n"
        f"Message:\n{submission['message']}\n"
        f"Sent at: {submission['timestamp']}\n"
    )

    try:
        if EMAIL_USE_SSL:
            with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT) as server:
                server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
                server.send_message(message)
        else:
            with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
                server.ehlo()
                if EMAIL_USE_TLS:
                    server.starttls()
                    server.ehlo()
                server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
                server.send_message(message)
        app.logger.info('Email notification sent to %s', EMAIL_TO)
        return True
    except Exception as exc:
        app.logger.error('Failed to send email notification: %s', exc)
        return False


def send_booking_confirmation(booking: Booking, checkout_url=None) -> bool:
    if not (EMAIL_HOST and EMAIL_USERNAME and EMAIL_PASSWORD and EMAIL_FROM):
        app.logger.warning('Booking confirmation email skipped: missing SMTP configuration.')
        return False

    message = EmailMessage()
    message['Subject'] = f"Booking request #{booking.id} received"
    message['From'] = EMAIL_FROM
    message['To'] = booking.email
    message.set_content(
        f"Hello {booking.name},\n\n"
        f"We received your booking request for {booking.tour.replace('-', ' ').title()}.\n"
        f"Date and time: {booking.date} at {booking.time} (Lamu time)\n"
        f"Guests: {booking.guests}\n"
        f"Estimated total: KSh {booking.amount:,.0f}\n"
        f"Booking status: {booking.status}\n"
        + (f"Complete payment securely: {checkout_url}\n" if checkout_url else '')
        + "\nYou can sign in at the Lamu Tours website to view and manage bookings made with your account.\n"
    )
    try:
        if EMAIL_USE_SSL:
            with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT) as server:
                server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
                server.send_message(message)
        else:
            with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
                server.ehlo()
                if EMAIL_USE_TLS:
                    server.starttls()
                    server.ehlo()
                server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
                server.send_message(message)
        app.logger.info('Booking confirmation email sent for booking %s.', booking.id)
        return True
    except (OSError, smtplib.SMTPException) as exc:
        app.logger.error('Failed to send booking confirmation for booking %s: %s', booking.id, exc)
        return False


def send_booking_status_notification(booking: Booking) -> bool:
    if not (EMAIL_HOST and EMAIL_USERNAME and EMAIL_PASSWORD and EMAIL_FROM):
        app.logger.warning('Booking status email skipped: missing SMTP configuration.')
        return False
    message = EmailMessage()
    message['Subject'] = f"Booking #{booking.id} status updated"
    message['From'] = EMAIL_FROM
    message['To'] = booking.email
    message.set_content(
        f"Hello {booking.name},\n\n"
        f"The status of your Lamu Tours booking #{booking.id} is now: {booking.status.replace('_', ' ').title()}.\n"
        f"Experience: {booking.tour.replace('-', ' ').title()}\n"
        f"Departure: {booking.date} at {booking.time} (Lamu time)\n\n"
        "Contact our team if you have questions about this update.\n"
    )
    try:
        if EMAIL_USE_SSL:
            with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT) as server:
                server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
                server.send_message(message)
        else:
            with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
                server.ehlo()
                if EMAIL_USE_TLS:
                    server.starttls()
                    server.ehlo()
                server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
                server.send_message(message)
        app.logger.info('Booking status email sent for booking %s.', booking.id)
        return True
    except (OSError, smtplib.SMTPException) as exc:
        app.logger.error('Failed to send booking status email for booking %s: %s', booking.id, exc)
        return False


@app.route('/')
def index():
    frontend_index = os.path.join(FRONTEND_DIST, 'index.html')
    if os.path.isfile(frontend_index):
        return send_from_directory(FRONTEND_DIST, 'index.html')
    return send_from_directory(BASE_DIR, 'index.html')


def frontend_page():
    frontend_index = os.path.join(FRONTEND_DIST, 'index.html')
    if os.path.isfile(frontend_index):
        return send_from_directory(FRONTEND_DIST, 'index.html')
    return send_from_directory(BASE_DIR, 'index.html')


@app.route('/admin/login', methods=['GET', 'POST'])
@limiter.limit('5 per minute', key_func=auth_attempt_key, methods=['POST'])
@limiter.limit('30 per hour', methods=['POST'])
def admin_login():
    if request.method == 'GET':
        if os.path.isfile(os.path.join(FRONTEND_DIST, 'index.html')):
            return frontend_page()
        return render_template('admin-login.html', setup_required=AdminAccount.query.count() == 0)

    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    admin = AdminAccount.query.filter_by(email=email).first()
    if not admin or not check_password_hash(admin.password_hash, password):
        if os.path.isfile(os.path.join(FRONTEND_DIST, 'index.html')):
            return redirect('/admin/login?error=Invalid%20admin%20email%20or%20password.')
        return render_template('admin-login.html', error='Invalid admin email or password.', setup_required=AdminAccount.query.count() == 0), 401

    session.clear()
    session['admin_id'] = admin.id
    session['admin_csrf'] = secrets.token_urlsafe(32)
    return redirect('/admin')


@app.route('/vendor/login', methods=['GET', 'POST'])
@limiter.limit('5 per minute', key_func=auth_attempt_key, methods=['POST'])
@limiter.limit('30 per hour', methods=['POST'])
def vendor_login():
    if request.method == 'GET':
        return frontend_page()

    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    vendor = VendorAccount.query.filter_by(email=email).first()
    if not vendor or not vendor.is_active or not check_password_hash(vendor.password_hash, password):
        return redirect('/vendor/login?error=Invalid%20vendor%20email%20or%20password.')

    session.clear()
    session['vendor_id'] = vendor.id
    session['vendor_csrf'] = secrets.token_urlsafe(32)
    return redirect('/vendor/dashboard')


@app.route('/api/vendor/registration-token', methods=['GET'])
def vendor_registration_token():
    token = secrets.token_urlsafe(32)
    session['vendor_registration_csrf'] = token
    return {'csrf_token': token}


@app.route('/vendor/register', methods=['GET', 'POST'])
@limiter.limit('3 per hour', methods=['POST'])
def vendor_register():
    if request.method == 'GET':
        return frontend_page()

    response = require_vendor_registration_csrf()
    if response:
        return response
    data = admin_payload()
    name = str(data.get('name', '')).strip()
    email = str(data.get('email', '')).strip().lower()
    password = data.get('password', '')
    if not name or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email) or not isinstance(password, str) or len(password) < 12:
        return {'error': 'Enter your name, a valid email, and a password of at least 12 characters.'}, 400
    if VendorAccount.query.filter_by(email=email).first():
        return {'error': 'A vendor account with that email already exists.'}, 409

    vendor = VendorAccount(name=name, email=email, password_hash=generate_password_hash(password))
    db.session.add(vendor)
    db.session.commit()
    session.clear()
    session['vendor_id'] = vendor.id
    session['vendor_csrf'] = secrets.token_urlsafe(32)
    return {'vendor': vendor.to_dict(), 'csrf_token': session['vendor_csrf']}, 201


@app.route('/vendor/logout', methods=['POST'])
@vendor_required
def vendor_logout():
    response = require_vendor_csrf()
    if response:
        return response
    session.clear()
    return '', 204


@app.route('/vendor/dashboard', methods=['GET'])
@vendor_required
def vendor_dashboard_page():
    return frontend_page()


@app.route('/my-bookings', methods=['GET'])
def customer_bookings_page():
    return frontend_page()


@app.route('/admin/logout', methods=['POST'])
@admin_required
def admin_logout():
    response = require_admin_csrf()
    if response:
        return response
    session.clear()
    if request.accept_mimetypes.best == 'application/json':
        return '', 204
    return redirect('/admin/login')


@app.route('/admin', methods=['GET'])
@admin_required
def admin_page():
    if os.path.isfile(os.path.join(FRONTEND_DIST, 'index.html')):
        return frontend_page()
    return render_template('admin.html', csrf_token=session['admin_csrf'])


@app.route('/admin/dashboard', methods=['GET'])
@admin_required
def admin_dashboard_page():
    return frontend_page()


@app.route('/api/admin/catalogue', methods=['GET'])
@admin_required
def admin_catalogue():
    return {
        'csrf_token': session['admin_csrf'],
        'tours': [{**item.to_dict(), 'vendor_id': item.vendor_id} for item in Tour.query.order_by(Tour.name).all()],
        'properties': [{
            **item.to_dict(),
            'vendor_id': item.vendor_id,
            'owner_name': item.owner_name,
            'owner_email': item.owner_email,
        } for item in Property.query.order_by(Property.name).all()],
        'destinations': [item.to_dict() for item in Destination.query.order_by(Destination.name).all()],
        'admins': [{'id': item.id, 'name': item.name, 'email': item.email} for item in AdminAccount.query.order_by(AdminAccount.email).all()],
        'vendors': [{
            **vendor.to_dict(),
            'tour_count': Tour.query.filter_by(vendor_id=vendor.id).count(),
            'property_count': Property.query.filter_by(vendor_id=vendor.id).count(),
        } for vendor in VendorAccount.query.order_by(VendorAccount.email).all()],
    }


@app.route('/api/admin/dashboard', methods=['GET'])
@admin_required
def admin_dashboard_data():
    recent_submissions = Submission.query.order_by(Submission.timestamp.desc()).limit(20).all()
    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(20).all()
    return {
        'csrf_token': session['admin_csrf'],
        'total_submissions': Submission.query.count(),
        'total_bookings': Booking.query.count(),
        'recent_submissions': [item.to_dict() for item in recent_submissions],
        'recent_bookings': [item.to_dict() for item in recent_bookings],
    }


@app.route('/api/admin/operations', methods=['GET'])
@admin_required
def admin_operations():
    bookings = Booking.query.order_by(Booking.created_at.desc()).limit(200).all()
    tour_slugs = {booking.tour for booking in bookings}
    booking_tour_names = {
        tour.slug: tour.name for tour in Tour.query.filter(Tour.slug.in_(tour_slugs)).all()
    } if tour_slugs else {}
    booking_rows = [
        {**booking.to_dict(), 'tour_name': booking_tour_names.get(booking.tour, booking.tour)}
        for booking in bookings
    ]

    booking_counts = dict(db.session.query(
        Booking.user_id,
        db.func.count(Booking.id),
    ).filter(Booking.user_id.isnot(None)).group_by(Booking.user_id).all())
    customers = [{
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'is_active': user.is_active,
        'created_at': user.created_at.isoformat() + 'Z' if user.created_at else None,
        'booking_count': booking_counts.get(user.id, 0),
    } for user in User.query.order_by(User.created_at.desc()).all()]
    vendors = [vendor.to_dict() for vendor in VendorAccount.query.order_by(VendorAccount.created_at.desc()).all()]

    report_rows = db.session.query(
        Booking.tour,
        db.func.count(Booking.id),
        db.func.coalesce(db.func.sum(
            case((Booking.payment_status == 'paid', Booking.amount), else_=0)
        ), 0),
        db.func.coalesce(db.func.sum(
            case(
                (Booking.payment_status == 'paid', Booking.amount * Booking.commission_rate / 100),
                else_=0,
            )
        ), 0),
    ).group_by(Booking.tour).order_by(db.func.count(Booking.id).desc()).all()
    total_paid = sum(float(row[2] or 0) for row in report_rows)
    total_commission = sum(float(row[3] or 0) for row in report_rows)
    report_tour_slugs = {row[0] for row in report_rows}
    report_tour_names = {
        tour.slug: tour.name for tour in Tour.query.filter(Tour.slug.in_(report_tour_slugs)).all()
    } if report_tour_slugs else {}

    disputes = BookingDispute.query.order_by(BookingDispute.created_at.desc()).limit(100).all()
    dispute_booking_ids = {dispute.booking_id for dispute in disputes}
    dispute_bookings = {
        booking.id: booking for booking in Booking.query.filter(Booking.id.in_(dispute_booking_ids)).all()
    } if dispute_booking_ids else {}
    dispute_rows = []
    for dispute in disputes:
        booking = dispute_bookings.get(dispute.booking_id)
        dispute_rows.append({
            **dispute.to_dict(),
            'booking_name': booking.name if booking else 'Booking removed',
            'booking_email': booking.email if booking else '',
            'tour': booking.tour if booking else '',
        })
    return {
        'csrf_token': session['admin_csrf'],
        'settings': {
            'commission_rate': float(get_admin_setting('commission_rate', 15)),
            'refund_policy': get_admin_setting('refund_policy', 'manual_review'),
            'cancellation_window_hours': int(get_admin_setting('cancellation_window_hours', 48)),
        },
        'customers': customers,
        'vendors': vendors,
        'bookings': booking_rows,
        'bookings_truncated': Booking.query.count() > len(bookings),
        'disputes': dispute_rows,
        'analytics': {
            'total_bookings': Booking.query.count(),
            'paid_revenue': total_paid,
            'commission_earned': total_commission,
            'by_tour': [{
                'tour': row[0],
                'tour_name': report_tour_names.get(row[0], row[0]),
                'bookings': row[1],
                'paid_revenue': float(row[2] or 0),
                'commission_earned': float(row[3] or 0),
            } for row in report_rows],
        },
    }


@app.route('/api/admin/settings', methods=['PUT'])
@admin_required
def admin_update_settings():
    response = require_admin_csrf()
    if response:
        return response
    payload = admin_payload()
    try:
        commission_rate = float(payload.get('commission_rate'))
    except (TypeError, ValueError):
        return {'error': 'Commission must be a number between 10% and 20%.'}, 400
    if not math.isfinite(commission_rate) or not 10 <= commission_rate <= 20:
        return {'error': 'Commission must be between 10% and 20%.'}, 400
    if payload.get('refund_policy', 'manual_review') != 'manual_review':
        return {'error': 'Refund requests must remain subject to manual admin review.'}, 400
    for key, value in {
        'commission_rate': f'{commission_rate:g}',
        'refund_policy': 'manual_review',
        'cancellation_window_hours': '48',
    }.items():
        setting = db.session.get(AdminSetting, key)
        if setting:
            setting.value = value
        else:
            db.session.add(AdminSetting(key=key, value=value))
    db.session.commit()
    return {'settings': {
        'commission_rate': commission_rate,
        'refund_policy': 'manual_review',
        'cancellation_window_hours': 48,
    }}


@app.route('/api/admin/users/<string:role>/<int:user_id>/status', methods=['POST'])
@admin_required
def admin_update_user_status(role, user_id):
    response = require_admin_csrf()
    if response:
        return response
    active = admin_payload().get('active')
    if not isinstance(active, bool) or role not in {'customer', 'vendor'}:
        return {'error': 'Choose a valid customer/vendor account and active status.'}, 400
    model = User if role == 'customer' else VendorAccount
    account = db.session.get(model, user_id)
    if not account:
        return {'error': 'User account not found.'}, 404
    account.is_active = active
    db.session.commit()
    return {'user': {'id': account.id, 'role': role, 'is_active': account.is_active}}


@app.route('/api/admin/bookings/<int:booking_id>/cancel', methods=['POST'])
@admin_required
def admin_cancel_booking(booking_id):
    response = require_admin_csrf()
    if response:
        return response
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return {'error': 'Booking not found.'}, 404
    if booking.status not in {'requested', 'confirmed', 'in_preparation'}:
        return {'error': 'Only active bookings can be cancelled.'}, 409
    try:
        expire_booking_checkout(booking)
    except (stripe.error.StripeError, RuntimeError):
        app.logger.exception('Could not expire Stripe checkout for booking %s.', booking.id)
        return {'error': 'Could not safely cancel the pending checkout. Please try again.'}, 503
    try:
        release_schedule(booking.schedule_id, booking.guests)
    except ValueError as exc:
        db.session.rollback()
        return {'error': str(exc)}, 409
    booking.status = 'cancelled'
    if booking.payment_status == 'pending':
        booking.payment_status = 'cancelled'
    db.session.commit()
    email_sent = send_booking_status_notification(booking)
    return {'booking': booking.to_dict(), 'email_sent': email_sent}


@app.route('/api/admin/bookings/<int:booking_id>/refund', methods=['POST'])
@admin_required
def admin_update_refund(booking_id):
    response = require_admin_csrf()
    if response:
        return response
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return {'error': 'Booking not found.'}, 404
    if booking.payment_status != 'paid':
        return {'error': 'Only paid bookings can enter refund review.'}, 409
    status = admin_payload().get('status')
    transitions = {
        'none': {'pending_review'},
        'pending_review': {'approved', 'rejected'},
        'approved': {'completed'},
        'rejected': {'pending_review'},
        'completed': set(),
    }
    if status not in transitions.get(booking.refund_status, set()):
        return {'error': 'That refund status transition is not allowed.'}, 409
    booking.refund_status = status
    if status == 'completed':
        booking.payment_status = 'refunded'
    db.session.commit()
    return {'booking': booking.to_dict(), 'gateway_refund_issued': False}


@app.route('/api/admin/bookings/<int:booking_id>/disputes', methods=['POST'])
@admin_required
def admin_open_booking_dispute(booking_id):
    response = require_admin_csrf()
    if response:
        return response
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return {'error': 'Booking not found.'}, 404
    reason = str(admin_payload().get('reason', '')).strip()
    if len(reason) < 10 or len(reason) > 3000:
        return {'error': 'Enter a dispute summary between 10 and 3,000 characters.'}, 400
    dispute = BookingDispute(booking_id=booking.id, reason=reason)
    db.session.add(dispute)
    db.session.commit()
    return {'dispute': dispute.to_dict()}, 201


@app.route('/api/admin/disputes/<int:dispute_id>', methods=['PUT'])
@admin_required
def admin_resolve_dispute(dispute_id):
    response = require_admin_csrf()
    if response:
        return response
    dispute = db.session.get(BookingDispute, dispute_id)
    if not dispute:
        return {'error': 'Dispute not found.'}, 404
    if dispute.status != 'open':
        return {'error': 'This dispute has already been resolved.'}, 409
    resolution = str(admin_payload().get('resolution', '')).strip()
    if len(resolution) < 10 or len(resolution) > 3000:
        return {'error': 'Enter a resolution between 10 and 3,000 characters.'}, 400
    dispute.status = 'resolved'
    dispute.resolution = resolution
    dispute.resolved_at = datetime.utcnow()
    db.session.commit()
    return {'dispute': dispute.to_dict()}


def admin_payload():
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


def tour_values(data):
    name = str(data.get('name', '')).strip()
    description = str(data.get('description', '')).strip()
    duration = str(data.get('duration', '')).strip()
    category = str(data.get('category', 'Island experiences')).strip()
    itinerary = data.get('itinerary', '')
    inclusions = data.get('inclusions', '')
    exclusions = data.get('exclusions', '')
    itinerary = '\n'.join(str(step).strip() for step in itinerary if str(step).strip()) if isinstance(itinerary, list) else str(itinerary).strip()
    inclusions = '\n'.join(str(item).strip() for item in inclusions if str(item).strip()) if isinstance(inclusions, list) else str(inclusions).strip()
    exclusions = '\n'.join(str(item).strip() for item in exclusions if str(item).strip()) if isinstance(exclusions, list) else str(exclusions).strip()
    pickup_point = str(data.get('pickup_point', 'Lamu Town waterfront')).strip()
    try:
        price = int(data.get('price', 0))
        min_group_size = int(data.get('min_group_size', 1))
        max_group_size = int(data.get('max_group_size', 12))
        image_url = safe_image_url(data.get('image_url'))
    except (TypeError, ValueError) as exc:
        raise ValueError(str(exc) or 'Price must be a positive whole number.') from exc
    if not name or not description or not duration or not category or not pickup_point or price < 1:
        raise ValueError('Name, category, description, duration, pickup point, and a positive price are required.')
    if min_group_size < 1 or max_group_size < min_group_size:
        raise ValueError('Group sizes must be positive and maximum size cannot be below minimum size.')
    return {
        'name': name,
        'description': description,
        'duration': duration,
        'price': price,
        'category': category,
        'itinerary': itinerary,
        'inclusions': inclusions,
        'exclusions': exclusions,
        'pickup_point': pickup_point,
        'min_group_size': min_group_size,
        'max_group_size': max_group_size,
        'image_url': image_url,
    }


def property_values(data):
    name = str(data.get('name', '')).strip()
    property_type = str(data.get('property_type', '')).strip().lower()
    location = str(data.get('location', '')).strip()
    description = str(data.get('description', '')).strip()
    try:
        price = int(data.get('price_per_night', 0))
        guests = int(data.get('guests', 0))
        image_url = safe_image_url(data.get('image_url'))
    except (TypeError, ValueError) as exc:
        raise ValueError(str(exc) or 'Price and guest capacity must be positive whole numbers.') from exc
    if not name or not location or not description or property_type not in {'hotel', 'home', 'guest house', 'villa'} or price < 1 or guests < 1:
        raise ValueError('Complete all property fields with a valid type, price, and guest capacity.')
    return {
        'name': name,
        'property_type': property_type,
        'location': location,
        'description': description,
        'price_per_night': price,
        'guests': guests,
        'image_url': image_url,
    }


@app.route('/api/admin/tours', methods=['POST'])
@admin_required
def admin_create_tour():
    response = require_admin_csrf()
    if response:
        return response
    data = admin_payload()
    try:
        values = tour_values(data)
    except (TypeError, ValueError) as exc:
        return {'error': str(exc)}, 400
    slug = unique_slug(str(data.get('slug') or values['name']), Tour)
    tour = Tour(slug=slug, **values)
    db.session.add(tour)
    db.session.commit()
    return {'tour': tour.to_dict()}, 201


@app.route('/api/admin/tours/<string:slug>', methods=['PUT', 'DELETE'])
@admin_required
def admin_update_tour(slug):
    response = require_admin_csrf()
    if response:
        return response
    tour = db.session.get(Tour, slug)
    if not tour:
        return {'error': 'Tour not found.'}, 404
    if request.method == 'DELETE':
        schedules = TourSchedule.query.filter_by(tour_slug=tour.slug).all()
        if any(schedule.booked_count for schedule in schedules):
            return {'error': 'A tour with booked departures cannot be deleted. Cancel or complete its bookings first.'}, 409
        for schedule in schedules:
            db.session.delete(schedule)
        Review.query.filter_by(target_type='tour', target_id=tour.slug).delete()
        db.session.delete(tour)
        db.session.commit()
        return '', 204

    data = admin_payload()
    try:
        values = tour_values(data)
    except (TypeError, ValueError) as exc:
        return {'error': str(exc)}, 400
    for field, value in values.items():
        setattr(tour, field, value)
    db.session.commit()
    return {'tour': tour.to_dict()}


@app.route('/api/admin/properties', methods=['POST'])
@admin_required
def admin_create_property():
    response = require_admin_csrf()
    if response:
        return response
    data = admin_payload()
    try:
        values = property_values(data)
    except (TypeError, ValueError) as exc:
        return {'error': str(exc)}, 400
    slug = unique_slug(str(data.get('slug') or values['name']), Property)
    admin = db.session.get(AdminAccount, session['admin_id'])
    listing = Property(
        slug=slug,
        owner_name=admin.name,
        owner_email=admin.email,
        **values,
    )
    db.session.add(listing)
    db.session.commit()
    return {'property': listing.to_dict()}, 201


@app.route('/api/admin/properties/<int:property_id>', methods=['PUT', 'DELETE'])
@admin_required
def admin_update_property(property_id):
    response = require_admin_csrf()
    if response:
        return response
    listing = db.session.get(Property, property_id)
    if not listing:
        return {'error': 'Property not found.'}, 404
    if request.method == 'DELETE':
        Review.query.filter_by(target_type='property', target_id=listing.slug).delete()
        db.session.delete(listing)
        db.session.commit()
        return '', 204

    data = admin_payload()
    try:
        values = property_values(data)
    except (TypeError, ValueError) as exc:
        return {'error': str(exc)}, 400
    for field, value in values.items():
        setattr(listing, field, value)
    db.session.commit()
    return {'property': listing.to_dict()}


@app.route('/api/admin/destinations', methods=['POST'])
@admin_required
def admin_create_destination():
    response = require_admin_csrf()
    if response:
        return response
    data = admin_payload()
    name = str(data.get('name', '')).strip()
    description = str(data.get('description', '')).strip()
    search_location = str(data.get('search_location', '')).strip()
    try:
        image_url = safe_image_url(data.get('image_url'))
    except ValueError as exc:
        return {'error': str(exc)}, 400
    if not name or not description or not search_location:
        return {'error': 'Name, description, and search location are required.'}, 400
    slug = unique_slug(str(data.get('slug') or name), Destination)
    destination = Destination(slug=slug, name=name, description=description, image_url=image_url, search_location=search_location)
    db.session.add(destination)
    db.session.commit()
    return {'destination': destination.to_dict()}, 201


@app.route('/api/admin/destinations/<string:slug>', methods=['PUT', 'DELETE'])
@admin_required
def admin_update_destination(slug):
    response = require_admin_csrf()
    if response:
        return response
    destination = db.session.get(Destination, slug)
    if not destination:
        return {'error': 'Destination not found.'}, 404
    if request.method == 'DELETE':
        db.session.delete(destination)
        db.session.commit()
        return '', 204
    data = admin_payload()
    name = str(data.get('name', '')).strip()
    description = str(data.get('description', '')).strip()
    search_location = str(data.get('search_location', '')).strip()
    try:
        image_url = safe_image_url(data.get('image_url'))
    except ValueError as exc:
        return {'error': str(exc)}, 400
    if not name or not description or not search_location:
        return {'error': 'Name, description, and search location are required.'}, 400
    destination.name, destination.description = name, description
    destination.search_location, destination.image_url = search_location, image_url
    db.session.commit()
    return {'destination': destination.to_dict()}


@app.route('/api/admin/admins', methods=['POST'])
@admin_required
def admin_create_account():
    response = require_admin_csrf()
    if response:
        return response
    data = admin_payload()
    name = str(data.get('name', '')).strip()
    email = str(data.get('email', '')).strip().lower()
    password = data.get('password', '')
    if not name or '@' not in email or not isinstance(password, str) or len(password) < 12:
        return {'error': 'Enter a name, valid email, and a password of at least 12 characters.'}, 400
    if AdminAccount.query.filter_by(email=email).first():
        return {'error': 'An admin account with that email already exists.'}, 409
    admin = AdminAccount(name=name, email=email, password_hash=generate_password_hash(password))
    db.session.add(admin)
    db.session.commit()
    return {'admin': {'id': admin.id, 'name': admin.name, 'email': admin.email}}, 201


@app.route('/api/admin/admins/<int:admin_id>', methods=['DELETE'])
@admin_required
def admin_delete_account(admin_id):
    response = require_admin_csrf()
    if response:
        return response
    admin = db.session.get(AdminAccount, admin_id)
    if not admin:
        return {'error': 'Admin account not found.'}, 404
    if admin.id == session.get('admin_id'):
        return {'error': 'You cannot delete the account you are currently using.'}, 400
    if AdminAccount.query.count() <= 1:
        return {'error': 'At least one admin account must remain.'}, 400
    db.session.delete(admin)
    db.session.commit()
    return '', 204


@app.route('/api/admin/vendors/<int:vendor_id>', methods=['DELETE'])
@admin_required
def admin_delete_vendor(vendor_id):
    response = require_admin_csrf()
    if response:
        return response
    vendor = db.session.get(VendorAccount, vendor_id)
    if not vendor:
        return {'error': 'Vendor account not found.'}, 404
    tours = Tour.query.filter_by(vendor_id=vendor.id).all()
    properties = Property.query.filter_by(vendor_id=vendor.id).all()
    for tour in tours:
        schedules = TourSchedule.query.filter_by(tour_slug=tour.slug).all()
        if any(schedule.booked_count for schedule in schedules):
            return {'error': 'Cancel or complete this vendor’s scheduled bookings before removing the account.'}, 409
        for schedule in schedules:
            db.session.delete(schedule)
        Review.query.filter_by(target_type='tour', target_id=tour.slug).delete()
        db.session.delete(tour)
    for listing in properties:
        Review.query.filter_by(target_type='property', target_id=listing.slug).delete()
        db.session.delete(listing)
    db.session.delete(vendor)
    db.session.commit()
    return '', 204


def availability_payload(data, tour=None):
    tour_slug = tour.slug if tour else str(data.get('tour_slug', '')).strip()
    if not db.session.get(Tour, tour_slug):
        raise ValueError('Choose a valid tour.')
    try:
        starts_at = parse_local_datetime(data.get('starts_at'))
        capacity = int(data.get('capacity', 0))
    except (TypeError, ValueError) as exc:
        raise ValueError(str(exc) or 'Enter a valid departure date, time, and capacity.') from exc
    if starts_at <= datetime.now(LAMU_TIMEZONE).replace(tzinfo=None) or capacity < 1:
        raise ValueError('Departure must be in the future and capacity must be positive.')
    return {'tour_slug': tour_slug, 'starts_at': starts_at, 'capacity': capacity}


def manage_availability(scope):
    if request.method == 'GET':
        query = TourSchedule.query
        if scope:
            query = query.join(Tour, Tour.slug == TourSchedule.tour_slug).filter(Tour.vendor_id == scope)
        return {'schedules': [item.to_dict() for item in query.order_by(TourSchedule.starts_at).all()]}

    response = require_admin_csrf() if scope is None else require_vendor_csrf()
    if response:
        return response
    data = admin_payload()
    if request.method == 'POST':
        try:
            values = availability_payload(data)
        except ValueError as exc:
            return {'error': str(exc)}, 400
        if scope is not None:
            owned_tour = Tour.query.filter_by(slug=values['tour_slug'], vendor_id=scope).first()
            if not owned_tour:
                return {'error': 'You can only schedule your own tours.'}, 404
        schedule = TourSchedule(**values)
        db.session.add(schedule)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return {'error': 'A departure for this tour at that time already exists.'}, 409
        return {'schedule': schedule.to_dict()}, 201

    schedule_id = request.view_args['schedule_id']
    query = TourSchedule.query.filter_by(id=schedule_id)
    if scope is not None:
        query = query.join(Tour, Tour.slug == TourSchedule.tour_slug).filter(Tour.vendor_id == scope)
    schedule = query.first()
    if not schedule:
        return {'error': 'Availability slot not found.'}, 404

    if request.method == 'DELETE':
        if schedule.booked_count:
            return {'error': 'A departure with bookings cannot be deleted. Cancel or complete its bookings first.'}, 409
        db.session.delete(schedule)
        db.session.commit()
        return '', 204

    try:
        capacity = int(data.get('capacity', schedule.capacity))
        starts_at = parse_local_datetime(data.get('starts_at', schedule.starts_at.isoformat()))
    except (TypeError, ValueError) as exc:
        return {'error': str(exc) or 'Enter a valid departure date, time, and capacity.'}, 400
    if capacity < schedule.booked_count or starts_at <= datetime.now(LAMU_TIMEZONE).replace(tzinfo=None):
        return {'error': 'Capacity cannot be below booked guests and departure must remain in the future.'}, 400
    schedule.capacity = capacity
    schedule.starts_at = starts_at
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return {'error': 'A departure for this tour at that time already exists.'}, 409
    return {'schedule': schedule.to_dict()}


@app.route('/api/admin/availability', methods=['GET', 'POST'])
@admin_required
def admin_availability():
    return manage_availability(None)


@app.route('/api/admin/availability/<int:schedule_id>', methods=['PUT', 'DELETE'])
@admin_required
def admin_availability_item(schedule_id):
    return manage_availability(None)


@app.route('/api/vendor/availability', methods=['GET', 'POST'])
@vendor_required
def vendor_availability():
    return manage_availability(get_current_vendor().id)


@app.route('/api/vendor/availability/<int:schedule_id>', methods=['PUT', 'DELETE'])
@vendor_required
def vendor_availability_item(schedule_id):
    return manage_availability(get_current_vendor().id)


def save_catalog_image(owner_folder):
    if os.environ.get('VERCEL') == '1':
        return {
            'error': 'Image uploads need persistent object storage on Vercel. Use an image URL until storage is configured.'
        }, 503

    uploaded = request.files.get('image')
    if not uploaded or not uploaded.filename:
        return {'error': 'Choose an image file to upload.'}, 400
    safe_name = secure_filename(uploaded.filename)
    extension = os.path.splitext(safe_name)[1].lower()
    signatures = {
        '.jpg': lambda header: header.startswith(b'\xff\xd8\xff'),
        '.jpeg': lambda header: header.startswith(b'\xff\xd8\xff'),
        '.png': lambda header: header.startswith(b'\x89PNG\r\n\x1a\n'),
        '.webp': lambda header: header.startswith(b'RIFF') and header[8:12] == b'WEBP',
    }
    signature_matches = signatures.get(extension)
    header = uploaded.stream.read(16)
    uploaded.stream.seek(0)
    if not signature_matches or not signature_matches(header):
        return {'error': 'Upload a valid JPEG, PNG, or WebP image.'}, 400
    filename = f'{uuid.uuid4().hex}{extension}'
    relative_path = os.path.join('uploads', owner_folder, filename)
    destination = os.path.join(BASE_DIR, relative_path)
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    uploaded.save(destination)
    return {'image_url': relative_path.replace(os.sep, '/')}, 201


@app.route('/api/admin/uploads', methods=['POST'])
@admin_required
def admin_upload_image():
    response = require_admin_csrf()
    if response:
        return response
    return save_catalog_image('admin')


@app.route('/api/vendor/uploads', methods=['POST'])
@vendor_required
def vendor_upload_image():
    response = require_vendor_csrf()
    if response:
        return response
    return save_catalog_image(f'vendors/{get_current_vendor().id}')


@app.route('/api/tours/<string:tour_slug>/availability', methods=['GET'])
def public_tour_availability(tour_slug):
    tour = db.session.get(Tour, tour_slug)
    if not tour:
        return {'error': 'Tour not found.'}, 404
    now = datetime.now(LAMU_TIMEZONE).replace(tzinfo=None)
    schedules = TourSchedule.query.filter(
        TourSchedule.tour_slug == tour.slug,
        TourSchedule.is_active.is_(True),
        TourSchedule.starts_at >= now,
        TourSchedule.booked_count < TourSchedule.capacity,
    ).order_by(TourSchedule.starts_at).limit(180).all()
    return {'schedules': [item.to_dict() for item in schedules]}


@app.route('/api/vendor/catalogue', methods=['GET'])
@vendor_required
def vendor_catalogue():
    vendor = get_current_vendor()
    return {
        'vendor': vendor.to_dict(),
        'csrf_token': session['vendor_csrf'],
        'tours': [item.to_dict() for item in Tour.query.filter_by(vendor_id=vendor.id).order_by(Tour.name).all()],
        'properties': [item.to_dict() for item in Property.query.filter_by(vendor_id=vendor.id).order_by(Property.name).all()],
    }


@app.route('/api/vendor/bookings', methods=['GET'])
@vendor_required
def vendor_bookings():
    vendor_id = get_current_vendor().id
    rows = db.session.query(Booking, Tour.name).join(
        Tour, Tour.slug == Booking.tour
    ).filter(
        Tour.vendor_id == vendor_id
    ).order_by(Booking.created_at.desc()).all()
    return {'bookings': [{**booking.to_dict(), 'tour_name': tour_name} for booking, tour_name in rows]}


@app.route('/api/vendor/bookings/<int:booking_id>/status', methods=['POST'])
@vendor_required
def vendor_update_booking_status(booking_id):
    response = require_vendor_csrf()
    if response:
        return response
    vendor_id = get_current_vendor().id
    booking = db.session.query(Booking).join(
        Tour, Tour.slug == Booking.tour
    ).filter(
        Booking.id == booking_id,
        Tour.vendor_id == vendor_id,
    ).first()
    if not booking:
        return {'error': 'Booking not found.'}, 404

    requested_status = str(admin_payload().get('status', '')).strip()
    transitions = {
        'requested': {'confirmed', 'cancelled'},
        'confirmed': {'in_preparation', 'cancelled'},
        'in_preparation': {'completed', 'cancelled'},
        'completed': set(),
        'cancelled': set(),
    }
    if requested_status not in transitions.get(booking.status, set()):
        return {'error': 'That booking status transition is not allowed.'}, 409
    if requested_status != 'cancelled' and booking.payment_status != 'paid':
        return {'error': 'Stripe payment must be verified before this booking can be confirmed.'}, 409
    if requested_status == 'cancelled':
        try:
            expire_booking_checkout(booking)
        except (stripe.error.StripeError, RuntimeError):
            app.logger.exception('Could not expire Stripe checkout for booking %s.', booking.id)
            return {'error': 'Could not safely cancel the pending checkout. Please try again.'}, 503
        try:
            release_schedule(booking.schedule_id, booking.guests)
        except ValueError as exc:
            db.session.rollback()
            return {'error': str(exc)}, 409
        if booking.payment_status == 'pending':
            booking.payment_status = 'cancelled'
    booking.status = requested_status
    db.session.commit()
    email_sent = send_booking_status_notification(booking)
    return {'booking': booking.to_dict(), 'email_sent': email_sent}


@app.route('/api/vendor/tours', methods=['POST'])
@vendor_required
def vendor_create_tour():
    response = require_vendor_csrf()
    if response:
        return response
    data = admin_payload()
    try:
        values = tour_values(data)
    except ValueError as exc:
        return {'error': str(exc)}, 400
    vendor = get_current_vendor()
    slug = unique_slug(str(data.get('slug') or values['name']), Tour)
    tour = Tour(slug=slug, vendor_id=vendor.id, **values)
    db.session.add(tour)
    db.session.commit()
    return {'tour': tour.to_dict()}, 201


@app.route('/api/vendor/tours/<string:slug>', methods=['PUT', 'DELETE'])
@vendor_required
def vendor_update_tour(slug):
    response = require_vendor_csrf()
    if response:
        return response
    vendor = get_current_vendor()
    tour = Tour.query.filter_by(slug=slug, vendor_id=vendor.id).first()
    if not tour:
        return {'error': 'Tour not found.'}, 404
    if request.method == 'DELETE':
        schedules = TourSchedule.query.filter_by(tour_slug=tour.slug).all()
        if any(schedule.booked_count for schedule in schedules):
            return {'error': 'A tour with booked departures cannot be deleted. Cancel or complete its bookings first.'}, 409
        for schedule in schedules:
            db.session.delete(schedule)
        Review.query.filter_by(target_type='tour', target_id=tour.slug).delete()
        db.session.delete(tour)
        db.session.commit()
        return '', 204

    try:
        values = tour_values(admin_payload())
    except ValueError as exc:
        return {'error': str(exc)}, 400
    for field, value in values.items():
        setattr(tour, field, value)
    db.session.commit()
    return {'tour': tour.to_dict()}


@app.route('/api/vendor/properties', methods=['POST'])
@vendor_required
def vendor_create_property():
    response = require_vendor_csrf()
    if response:
        return response
    data = admin_payload()
    try:
        values = property_values(data)
    except ValueError as exc:
        return {'error': str(exc)}, 400
    vendor = get_current_vendor()
    slug = unique_slug(str(data.get('slug') or values['name']), Property)
    listing = Property(
        slug=slug,
        vendor_id=vendor.id,
        owner_name=vendor.name,
        owner_email=vendor.email,
        **values,
    )
    db.session.add(listing)
    db.session.commit()
    return {'property': listing.to_dict()}, 201


@app.route('/api/vendor/properties/<int:property_id>', methods=['PUT', 'DELETE'])
@vendor_required
def vendor_update_property(property_id):
    response = require_vendor_csrf()
    if response:
        return response
    vendor = get_current_vendor()
    listing = Property.query.filter_by(id=property_id, vendor_id=vendor.id).first()
    if not listing:
        return {'error': 'Property not found.'}, 404
    if request.method == 'DELETE':
        Review.query.filter_by(target_type='property', target_id=listing.slug).delete()
        db.session.delete(listing)
        db.session.commit()
        return '', 204

    try:
        values = property_values(admin_payload())
    except ValueError as exc:
        return {'error': str(exc)}, 400
    for field, value in values.items():
        setattr(listing, field, value)
    db.session.commit()
    return {'property': listing.to_dict()}


@app.route('/api/catalogue', methods=['GET'])
def public_catalogue():
    return {
        'tours': [item.to_dict() for item in Tour.query.order_by(Tour.name).all()],
        'properties': [item.to_dict() for item in Property.query.order_by(Property.name).all()],
        'destinations': [item.to_dict() for item in Destination.query.order_by(Destination.name).all()],
    }


def _fetch_json(url):
    parsed_url = urllib.parse.urlparse(url)
    if parsed_url.scheme != 'https' or parsed_url.hostname not in {'open.er-api.com', 'ipapi.co'}:
        raise ValueError('Currency service URL is not allowed')

    request_object = urllib.request.Request(
        url,
        headers={'Accept': 'application/json', 'User-Agent': 'LamuTours/1.0'}
    )
    try:
        # Only allow-listed HTTPS provider hosts reach this call.
        with urllib.request.urlopen(request_object, timeout=CURRENCY_API_TIMEOUT) as response:  # nosec B310
            payload = response.read(1024 * 1024)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ValueError('Currency service request failed') from exc

    try:
        result = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('Currency service returned invalid JSON') from exc
    if not isinstance(result, dict):
        raise ValueError('Currency service returned an invalid response')
    return result


def _get_exchange_rates():
    now = time.time()
    with _currency_cache_lock:
        if _exchange_rates_cache['rates'] and _exchange_rates_cache['expires_at'] > now:
            return _exchange_rates_cache['rates'], _exchange_rates_cache['updated_at']

    data = _fetch_json('https://open.er-api.com/v6/latest/KES')
    rates = data.get('rates')
    if data.get('result') != 'success' or not isinstance(rates, dict) or rates.get('KES') != 1:
        raise ValueError('Exchange rate service returned invalid rates')

    valid_rates = {
        code: float(rate)
        for code, rate in rates.items()
        if re.fullmatch(r'[A-Z]{3}', code)
        and isinstance(rate, (int, float))
        and not isinstance(rate, bool)
        and math.isfinite(rate)
        and rate > 0
    }
    if valid_rates.get('KES') != 1:
        raise ValueError('Exchange rate service did not return KES rates')

    updated_at = data.get('time_last_update_utc')
    with _currency_cache_lock:
        _exchange_rates_cache.update({
            'expires_at': now + CURRENCY_CACHE_TTL,
            'rates': valid_rates,
            'updated_at': updated_at if isinstance(updated_at, str) else None,
        })
    return valid_rates, _exchange_rates_cache['updated_at']


def _get_client_public_ip():
    candidates = [*request.access_route, request.remote_addr]
    for candidate in candidates:
        try:
            address = ipaddress.ip_address(candidate)
        except (TypeError, ValueError):
            continue
        if address.is_global:
            return str(address)
    return None


def _get_geolocation(ip_address):
    now = time.time()
    with _currency_cache_lock:
        cached = _geolocation_cache.get(ip_address)
        if cached and cached['expires_at'] > now:
            return cached

    url = f'https://ipapi.co/{urllib.parse.quote(ip_address, safe="")}/json/'
    data = _fetch_json(url)
    currency = data.get('currency')
    country_code = data.get('country_code')
    if not isinstance(currency, str) or not re.fullmatch(r'[A-Z]{3}', currency):
        raise ValueError('Geolocation service returned an invalid currency')

    result = {
        'currency': currency,
        'country_code': country_code if isinstance(country_code, str) and re.fullmatch(r'[A-Z]{2}', country_code) else None,
        'expires_at': now + CURRENCY_CACHE_TTL,
    }
    with _currency_cache_lock:
        if len(_geolocation_cache) >= 1024:
            oldest = min(_geolocation_cache, key=lambda key: _geolocation_cache[key]['expires_at'])
            del _geolocation_cache[oldest]
        _geolocation_cache[ip_address] = result
    return result


@app.route('/api/currency', methods=['GET'])
def currency_info():
    try:
        rates, updated_at = _get_exchange_rates()
    except ValueError as exc:
        app.logger.warning('Currency rate lookup failed: %s', exc)
        return {'error': 'Currency rates are temporarily unavailable.'}, 503

    currency = 'KES'
    country_code = None
    detected = False
    ip_address = _get_client_public_ip()
    if ip_address:
        try:
            location = _get_geolocation(ip_address)
            country_code = location['country_code']
            if location['currency'] in rates:
                currency = location['currency']
                detected = True
            else:
                app.logger.warning('Exchange rates do not include the detected currency %s.', location['currency'])
        except ValueError as exc:
            app.logger.warning('IP geolocation lookup failed: %s', exc)

    return {
        'base': 'KES',
        'currency': currency,
        'country_code': country_code,
        'detected': detected,
        'rates': rates,
        'updated_at': updated_at,
    }


@app.route('/register', methods=['GET', 'POST'])
@limiter.limit('3 per hour', methods=['POST'])
def register():
    if request.method == 'GET':
        frontend_index = os.path.join(FRONTEND_DIST, 'index.html')
        if os.path.isfile(frontend_index):
            return send_from_directory(FRONTEND_DIST, 'index.html')
        return send_from_directory(BASE_DIR, 'register.html')

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not name or not email or not password:
        return redirect('/register.html?error=Please%20complete%20all%20fields.')
    if len(password) < 8:
        return redirect('/register.html?error=Password%20must%20be%20at%20least%208%20characters.')
    if password != confirm_password:
        return redirect('/register.html?error=Passwords%20do%20not%20match.')
    if User.query.filter_by(email=email).first():
        return redirect('/register.html?error=An%20account%20with%20that%20email%20already%20exists.')

    user = User(name=name, email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    session.clear()
    session['user_id'] = user.id
    session['user_name'] = user.name
    session['customer_csrf'] = secrets.token_urlsafe(32)
    return redirect('/booking.html')

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit('5 per minute', key_func=auth_attempt_key, methods=['POST'])
@limiter.limit('30 per hour', methods=['POST'])
def login():
    if request.method == 'GET':
        frontend_index = os.path.join(FRONTEND_DIST, 'index.html')
        if os.path.isfile(frontend_index):
            return send_from_directory(FRONTEND_DIST, 'index.html')
        return send_from_directory(BASE_DIR, 'login.html')

    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    user = User.query.filter_by(email=email).first()
    if not user or not user.is_active or not check_password_hash(user.password_hash, password):
        return redirect('/login.html?error=Invalid%20email%20or%20password.')

    session.clear()
    session['user_id'] = user.id
    session['user_name'] = user.name
    session['customer_csrf'] = secrets.token_urlsafe(32)
    return redirect('/booking.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login.html')


def booking_change_deadline(booking):
    try:
        starts_at = datetime.strptime(f'{booking.date} {booking.time}', '%Y-%m-%d %H:%M')
    except ValueError as exc:
        raise ValueError('This booking has an invalid departure time and cannot be changed online.') from exc
    now = datetime.now(LAMU_TIMEZONE).replace(tzinfo=None)
    if starts_at - now < timedelta(hours=48):
        raise ValueError('Bookings can only be cancelled or rescheduled at least 48 hours before departure.')


@app.route('/api/customer/profile', methods=['GET'])
@customer_required
def customer_profile():
    user = db.session.get(User, session['user_id'])
    session.setdefault('customer_csrf', secrets.token_urlsafe(32))
    return {'customer': {'id': user.id, 'name': user.name, 'email': user.email}, 'csrf_token': session['customer_csrf']}


@app.route('/api/customer/bookings', methods=['GET'])
@customer_required
def customer_bookings():
    user = db.session.get(User, session['user_id'])
    return {'bookings': [
        item.to_dict()
        for item in Booking.query.filter_by(user_id=user.id).order_by(Booking.created_at.desc()).all()
    ]}


@app.route('/api/customer/bookings/<int:booking_id>/cancel', methods=['POST'])
@customer_required
def customer_cancel_booking(booking_id):
    response = require_customer_csrf()
    if response:
        return response
    booking = Booking.query.filter_by(id=booking_id, user_id=session['user_id']).first()
    if not booking:
        return {'error': 'Booking not found.'}, 404
    if booking.status not in {'requested', 'confirmed'}:
        return {'error': 'Only requested or confirmed bookings can be cancelled.'}, 409
    try:
        booking_change_deadline(booking)
        expire_booking_checkout(booking)
        release_schedule(booking.schedule_id, booking.guests)
    except ValueError as exc:
        db.session.rollback()
        return {'error': str(exc)}, 400
    except (stripe.error.StripeError, RuntimeError):
        app.logger.exception('Could not expire Stripe checkout for booking %s.', booking.id)
        return {'error': 'Could not safely cancel the pending checkout. Please try again.'}, 503
    booking.status = 'cancelled'
    if booking.payment_status == 'pending':
        booking.payment_status = 'cancelled'
    db.session.commit()
    return {'booking': booking.to_dict()}


@app.route('/api/customer/bookings/<int:booking_id>/reschedule', methods=['POST'])
@customer_required
def customer_reschedule_booking(booking_id):
    response = require_customer_csrf()
    if response:
        return response
    booking = Booking.query.filter_by(id=booking_id, user_id=session['user_id']).first()
    if not booking:
        return {'error': 'Booking not found.'}, 404
    if booking.status not in {'requested', 'confirmed'}:
        return {'error': 'Only requested or confirmed bookings can be rescheduled.'}, 409
    data = admin_payload()
    try:
        booking_change_deadline(booking)
    except ValueError as exc:
        return {'error': str(exc)}, 400
    schedule = TourSchedule.query.filter_by(id=data.get('schedule_id'), tour_slug=booking.tour).first()
    if not schedule:
        return {'error': 'Choose an available departure for this tour.'}, 400
    if schedule.id == booking.schedule_id:
        return {'error': 'Choose a different departure to reschedule.'}, 400
    if schedule.starts_at - datetime.now(LAMU_TIMEZONE).replace(tzinfo=None) < timedelta(hours=48):
        return {'error': 'The new departure must be at least 48 hours away.'}, 400
    try:
        reserve_schedule(schedule.id, booking.guests)
        release_schedule(booking.schedule_id, booking.guests)
    except ValueError as exc:
        db.session.rollback()
        return {'error': str(exc)}, 409
    booking.schedule_id = schedule.id
    booking.date = schedule.starts_at.date().isoformat()
    booking.time = schedule.starts_at.strftime('%H:%M')
    db.session.commit()
    email_sent = send_booking_confirmation(booking)
    return {'booking': booking.to_dict(), 'email_sent': email_sent}


@app.route('/properties', methods=['GET'])
def properties():
    listings = Property.query.order_by(Property.name).all()
    return {'properties': [property_listing.to_dict() for property_listing in listings]}

@app.route('/review-submit', methods=['POST'])
@limiter.limit('5 per hour', methods=['POST'])
def review_submit():
    data = request.get_json(silent=True) if request.is_json else request.form
    data = data or {}
    try:
        rating = int(data.get('rating', '0'))
    except (TypeError, ValueError):
        rating = 0

    review_data = {
        'reviewer_name': str(data.get('reviewer_name', '')).strip(),
        'reviewer_email': str(data.get('reviewer_email', '')).strip().lower(),
        'place': '',
        'target_type': str(data.get('target_type', '')).strip(),
        'target_id': str(data.get('target_id', '')).strip(),
        'rating': rating,
        'comment': str(data.get('comment', '')).strip(),
    }
    target = None
    if review_data['target_type'] == 'tour':
        target = db.session.get(Tour, review_data['target_id'])
        review_data['place'] = target.name if target else ''
    elif review_data['target_type'] == 'property':
        target = Property.query.filter_by(slug=review_data['target_id']).first()
        review_data['place'] = target.name if target else ''
    if (
        not target
        or not review_data['reviewer_name']
        or len(review_data['reviewer_name']) > 100
        or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', review_data['reviewer_email'])
        or len(review_data['reviewer_email']) > 120
        or not review_data['comment']
        or len(review_data['comment']) > 3000
        or len(review_data['target_id']) > 160
        or rating not in range(1, 6)
    ):
        if request.is_json:
            return {'error': 'Complete the review form and select a valid tour or property.'}, 400
        return redirect('/tours.html?review_error=Complete%20the%20review%20form%20and%20choose%20a%20listing#reviews')

    review = Review(**review_data)
    db.session.add(review)
    db.session.commit()
    if request.is_json:
        return {'review': review.to_dict()}, 201
    return redirect('/tours.html?review_success=Your%20review%20was%20published#reviews')

@app.route('/reviews', methods=['GET'])
def reviews():
    query = Review.query
    target_type = request.args.get('target_type', '')
    target_id = request.args.get('target_id', '')
    if target_type and target_id:
        query = query.filter_by(target_type=target_type, target_id=target_id)
    recent_reviews = query.order_by(Review.created_at.desc()).limit(50).all()
    return {'reviews': [review.to_dict() for review in recent_reviews]}


@app.route('/hospitality.html')
def removed_hospitality_page():
    return {'error': 'Not found'}, 404


@app.route('/<path:filename>')
def static_files(filename):
    allowed_extensions = {'.html', '.css', '.js', '.svg', '.ico', '.jpg', '.jpeg', '.png', '.gif', '.webp'}
    extension = os.path.splitext(filename)[1].lower()
    if extension not in allowed_extensions or filename.startswith(('.', '_', 'templates/')):
        return {'error': 'Not found'}, 404
    frontend_index = os.path.join(FRONTEND_DIST, 'index.html')
    frontend_file = os.path.join(FRONTEND_DIST, filename)
    if os.path.isfile(frontend_file):
        return send_from_directory(FRONTEND_DIST, filename)
    if filename.endswith('.html') and os.path.isfile(frontend_index):
        return send_from_directory(FRONTEND_DIST, 'index.html')
    return send_from_directory(BASE_DIR, filename)

@app.route('/contact-submit', methods=['POST'])
@limiter.limit('10 per hour', methods=['POST'])
def contact_submit():
    form_data = request.get_json(silent=True) if request.is_json else request.form
    form_data = form_data or {}
    submission = {
        'name': form_data.get('name', 'Guest'),
        'email': form_data.get('email', ''),
        'subject': form_data.get('subject', ''),
        'message': form_data.get('message', ''),
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }

    email_sent = send_email_notification(submission)
    submission['email_sent'] = email_sent
    saved_submission = save_submission(submission)
    app.logger.info('Contact submission saved: %s', saved_submission.to_dict())

    if request.is_json:
        return {'message': 'Your message has been received.', 'email_sent': email_sent}, 201

    return render_template_string(
        '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Message Sent - Lamu Tours</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #eef2f7; margin: 0; padding: 2rem; color: #1e3c72; }
        .card { max-width: 600px; margin: 0 auto; background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.12); }
        a { color: #ff7e3f; text-decoration: none; font-weight: 600; }
        a:hover { text-decoration: underline; }
        .status { margin-top: 1rem; font-weight: 700; }
        dl { margin-top: 1rem; }
        dt { font-weight: 700; margin-top: 1rem; }
        dd { margin-left: 0; margin-bottom: 0.75rem; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Thank you, {{ name }}!</h1>
        <p>Your message has been received and stored successfully.</p>
        <p class="status">{% if email_sent %}A notification email was sent to the support team.{% else %}Email notification could not be sent. Please check server email settings.{% endif %}</p>
        <dl>
            <dt>Email</dt><dd>{{ email }}</dd>
            <dt>Subject</dt><dd>{{ subject }}</dd>
            <dt>Message</dt><dd>{{ message }}</dd>
        </dl>
        <p><a href="/contact.html">Return to Contact page</a></p>
    </div>
</body>
</html>''', email_sent=email_sent, **submission)

@app.route('/booking-confirmation', methods=['POST'])
@limiter.limit('10 per hour', methods=['POST'])
def booking_confirmation():
    data = request.get_json(silent=True) if request.is_json else request.form
    data = data or {}
    if not STRIPE_SECRET_KEY:
        message = 'Secure online payment is unavailable right now. Please try again later.'
        if request.is_json:
            return {'error': message}, 503
        return redirect('/booking.html?error=' + urllib.parse.quote(message))

    allowed_country_codes = {'+1', '+27', '+44', '+91', '+254', '+255', '+256', '+971'}
    country_code = str(data.get('country_code', '')).strip()
    phone = str(data.get('phone', '')).strip()
    if country_code not in allowed_country_codes or not phone.isdigit():
        return redirect('/booking.html?error=Select%20a%20country%20code%20and%20enter%20numbers%20only')

    tour = str(data.get('tour', ''))
    guests = data.get('guests', '1')
    try:
        guest_count = int(guests)
        total_amount = calculate_booking_price(tour, guest_count)
    except (TypeError, ValueError):
        message = 'Please select a valid tour and guest count.'
        if request.is_json:
            return {'error': message}, 400
        return redirect('/booking.html?error=Please%20select%20a%20valid%20tour%20and%20guest%20count')

    tour_item = db.session.get(Tour, tour)
    schedule = None
    if tour_item:
        schedule = TourSchedule.query.filter_by(
            id=int(data.get('schedule_id') or 0),
            tour_slug=tour_item.slug,
            is_active=True,
        ).first()
        if not schedule or schedule.starts_at <= datetime.now(LAMU_TIMEZONE).replace(tzinfo=None):
            message = 'Choose an available departure before submitting your booking.'
            if request.is_json:
                return {'error': message}, 400
            return redirect('/booking.html?error=Choose%20an%20available%20departure')
        if guest_count < tour_item.min_group_size or guest_count > tour_item.max_group_size:
            message = f'Group size for this tour must be between {tour_item.min_group_size} and {tour_item.max_group_size}.'
            if request.is_json:
                return {'error': message}, 400
            return redirect('/booking.html?error=' + urllib.parse.quote(message))
        try:
            reserve_schedule(schedule.id, guest_count)
        except ValueError as exc:
            db.session.rollback()
            if request.is_json:
                return {'error': str(exc)}, 409
            return redirect('/booking.html?error=' + urllib.parse.quote(str(exc)))

    booking = {
        'user_id': session.get('user_id'),
        'schedule_id': schedule.id if schedule else None,
        'name': data.get('name', 'Guest'),
        'email': data.get('email', ''),
        'phone': f'{country_code}{phone}',
        'tour': tour,
        'date': schedule.starts_at.date().isoformat() if schedule else data.get('date', ''),
        'time': schedule.starts_at.strftime('%H:%M') if schedule else data.get('time', ''),
        'guests': guests,
        'message': data.get('message', ''),
        'amount': total_amount,
        'commission_rate': float(get_admin_setting('commission_rate', 15)),
        'payment_status': 'pending',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    saved_booking = save_booking(booking)
    app.logger.info('Booking request saved: %s', saved_booking.to_dict())

    try:
        payment_url = create_stripe_checkout_session(saved_booking)
        email_sent = send_booking_confirmation(saved_booking, payment_url)
        if request.is_json:
            return {'booking': saved_booking.to_dict(), 'checkout_url': payment_url, 'email_sent': email_sent, 'managed': saved_booking.user_id is not None}, 201
        return redirect(payment_url)
    except (stripe.error.StripeError, RuntimeError, SQLAlchemyError):
        app.logger.exception('Stripe checkout failed for booking %s.', saved_booking.id)
        try:
            expire_booking_checkout(saved_booking)
            if saved_booking.payment_status == 'pending':
                release_schedule(saved_booking.schedule_id, saved_booking.guests)
                saved_booking.payment_status = 'cancelled'
                saved_booking.status = 'cancelled'
                db.session.commit()
        except (ValueError, stripe.error.StripeError, RuntimeError):
            db.session.rollback()
            app.logger.exception('Could not release failed checkout booking %s.', saved_booking.id)
        if request.is_json:
            return {'error': 'Secure checkout could not be started. Your booking was not confirmed; please try again.'}, 503
        return send_from_directory(BASE_DIR, 'booking-confirmation.html')


@app.route('/payment-success')
def payment_success():
    booking_id = request.args.get('booking_id')
    booking = Booking.query.get(int(booking_id)) if booking_id and booking_id.isdigit() else None
    session_id = request.args.get('session_id', '')
    payment_confirmed = False
    if booking and booking.stripe_session_id == session_id and STRIPE_SECRET_KEY:
        try:
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            booking = confirm_stripe_checkout(checkout_session)
            payment_confirmed = booking is not None
        except (stripe.error.StripeError, RuntimeError):
            app.logger.exception('Could not verify Stripe checkout for booking %s.', booking_id)

    return render_template_string(
        '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Payment Successful - Lamu Tours</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #eef2f7; margin: 0; padding: 2rem; color: #1e3c72; }
        .card { max-width: 700px; margin: 1.5rem auto; background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,.12); }
        a { color: #ff7e3f; font-weight: 600; text-decoration: none; }
    </style>
</head>
<body>
    <div class="card">
        <h1>{{ 'Payment confirmed' if payment_confirmed else 'Payment not confirmed' }}</h1>
        <p>{% if payment_confirmed %}Your payment was verified by Stripe and your booking is confirmed.{% else %}We could not verify a completed payment. Your booking is not confirmed yet. If you completed checkout, please contact our team with your booking reference.{% endif %}</p>
        {% if payment_confirmed and booking %}
        <p><strong>Booking ID:</strong> {{ booking.id }}</p>
        <p><strong>Tour:</strong> {{ booking.tour }}</p>
        <p><strong>Total paid:</strong> KSh {{ '{:,.0f}'.format(booking.amount) }}</p>
        {% else %}<p>No booking was confirmed for this checkout.</p>{% endif %}
        <p><a href="/booking.html">Return to bookings</a></p>
    </div>
</body>
</html>''', booking=booking, payment_confirmed=payment_confirmed)


@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    if not STRIPE_WEBHOOK_SECRET:
        app.logger.warning('Stripe webhook called without a configured webhook secret.')
        return 'Webhook not configured', 400

    payload = request.get_data(as_text=False)
    signature = request.headers.get('Stripe-Signature', '')

    try:
        event = stripe.Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError:
        return 'Invalid signature', 400

    event_type = event.get('type')
    if event_type in {'checkout.session.completed', 'checkout.session.async_payment_succeeded'}:
        session_data = event.get('data', {}).get('object', {})
        confirm_stripe_checkout(session_data)
    elif event_type == 'checkout.session.expired':
        expire_booking_from_webhook(event.get('data', {}).get('object', {}))

    return '', 204


@app.route('/payment-cancel')
def payment_cancel():
    return redirect('/booking.html?error=Payment%20was%20not%20completed.%20Your%20booking%20is%20not%20confirmed.')


@app.route('/dashboard', methods=['GET'])
@admin_required
def dashboard():
    if os.path.isfile(os.path.join(FRONTEND_DIST, 'index.html')):
        return frontend_page()
    total_submissions = Submission.query.count()
    total_bookings = Booking.query.count()
    recent_submissions = Submission.query.order_by(Submission.timestamp.desc()).limit(20).all()
    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(20).all()
    return render_template_string(
        '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Lamu Tours</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
        header { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 2rem 1rem; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
        h1 { margin: 0; font-size: 3em; }
        nav { background: linear-gradient(90deg, #2a5298 0%, #1e3c72 100%); padding: 0.8rem; display: flex; justify-content: center; flex-wrap: wrap; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        nav a { color: white; text-decoration: none; margin: 0 1rem; padding: 0.7rem 1rem; border-radius: 6px; transition: all 0.3s ease; font-weight: 500; }
        nav a:hover { background-color: #ff9a56; color: #1e3c72; transform: translateY(-2px); }
        .container { max-width: 1200px; margin: 2rem auto; padding: 2rem; background-color: white; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.12); }
        .stats { display: grid; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); gap: 1rem; margin-bottom: 2rem; }
        .card { background: #f9f9f9; padding: 1.5rem; border-radius: 12px; border-left: 4px solid #ff9a56; }
        .card h2 { margin-top: 0; font-size: 1.25rem; color: #1e3c72; }
        table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
        th, td { padding: 0.9rem 0.75rem; text-align: left; border-bottom: 1px solid #e0e0e0; }
        th { background: #f0f8ff; }
        tr:hover { background: #fafafa; }
        .badge { display: inline-flex; align-items: center; padding: 0.35rem 0.65rem; border-radius: 999px; font-size: 0.9rem; background: #e0f4ff; color: #1e3c72; }
    </style>
</head>
<body>
    <header>
        <h1>Admin Dashboard</h1>
    </header>
    <nav>
        <a href="index.html">Home</a>
        <a href="tours.html">Tours</a>
        <a href="booking.html">Booking</a>
        <a href="about-lamu.html">About Lamu</a>
        <a href="contact.html">Contact</a>
    </nav>
    <div class="container">
        <div class="stats">
            <div class="card">
                <h2>Total Contact Messages</h2>
                <p class="badge">{{ total_submissions }}</p>
            </div>
            <div class="card">
                <h2>Total Booking Requests</h2>
                <p class="badge">{{ total_bookings }}</p>
            </div>
            <div class="card">
                <h2>Recent Messages</h2>
                <p class="badge">Showing latest {{ recent_submissions|length }}</p>
            </div>
            <div class="card">
                <h2>Recent Bookings</h2>
                <p class="badge">Showing latest {{ recent_bookings|length }}</p>
            </div>
        </div>

        <h2>Latest Contact Submissions</h2>
        {% if recent_submissions %}
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Subject</th>
                    <th>Received</th>
                    <th>Email Sent</th>
                </tr>
            </thead>
            <tbody>
                {% for item in recent_submissions %}
                <tr>
                    <td>{{ item.id }}</td>
                    <td>{{ item.name }}</td>
                    <td>{{ item.email }}</td>
                    <td>{{ item.subject }}</td>
                    <td>{{ item.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</td>
                    <td>{{ 'Yes' if item.email_sent else 'No' }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p>No submissions have been received yet.</p>
        {% endif %}

        <h2>Latest Booking Requests</h2>
        {% if recent_bookings %}
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Phone</th>
                    <th>Tour</th>
                    <th>Date</th>
                    <th>Time</th>
                    <th>Guests</th>
                </tr>
            </thead>
            <tbody>
                {% for item in recent_bookings %}
                <tr>
                    <td>{{ item.id }}</td>
                    <td>{{ item.name }}</td>
                    <td>{{ item.email }}</td>
                    <td>{{ item.phone }}</td>
                    <td>{{ item.tour }}</td>
                    <td>{{ item.date }}</td>
                    <td>{{ item.time }}</td>
                    <td>{{ item.guests }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p>No booking requests have been received yet.</p>
        {% endif %}
    </div>
</body>
</html>''', total_submissions=total_submissions, total_bookings=total_bookings, recent_submissions=recent_submissions, recent_bookings=recent_bookings)

@app.route('/submissions', methods=['GET'])
@admin_required
def submissions():
    all_submissions = Submission.query.order_by(Submission.timestamp.desc()).all()
    return {'submissions': [s.to_dict() for s in all_submissions]}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(
        host=os.environ.get('HOST', '127.0.0.1'),
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('FLASK_DEBUG', 'false').lower() in ('1', 'true', 'yes')
    )
