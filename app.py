import json
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from flask import Flask, redirect, request, send_from_directory, render_template_string, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'submissions.json')

EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USERNAME = os.environ.get('EMAIL_USERNAME', '')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
EMAIL_FROM = os.environ.get('EMAIL_FROM', EMAIL_USERNAME)
EMAIL_TO = os.environ.get('EMAIL_TO', 'info@lamutours.com')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() in ('1', 'true', 'yes')
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'false').lower() in ('1', 'true', 'yes')

app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'lamu-tours-development-secret')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "submissions.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    email_sent = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'subject': self.subject,
            'message': self.message,
            'timestamp': self.timestamp.isoformat() + 'Z' if self.timestamp else None,
            'email_sent': self.email_sent
        }

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    tour = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(20), nullable=False)
    guests = db.Column(db.Integer, nullable=False)
    message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'tour': self.tour,
            'date': self.date,
            'time': self.time,
            'guests': self.guests,
            'message': self.message,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None
        }

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_name = db.Column(db.String(100), nullable=False)
    owner_email = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    property_type = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(120), nullable=False)
    price_per_night = db.Column(db.Integer, nullable=False)
    guests = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'owner_name': self.owner_name,
            'name': self.name,
            'property_type': self.property_type,
            'location': self.location,
            'price_per_night': self.price_per_night,
            'guests': self.guests,
            'image_url': self.image_url,
            'description': self.description,
        }

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reviewer_name = db.Column(db.String(100), nullable=False)
    reviewer_email = db.Column(db.String(120), nullable=False)
    place = db.Column(db.String(150), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'reviewer_name': self.reviewer_name,
            'place': self.place,
            'rating': self.rating,
            'comment': self.comment,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
        }


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


def save_booking(booking: dict) -> Booking:
    new_booking = Booking(
        name=booking['name'],
        email=booking['email'],
        phone=booking['phone'],
        tour=booking['tour'],
        date=booking['date'],
        time=booking['time'],
        guests=int(booking['guests']),
        message=booking.get('message', ''),
        created_at=datetime.fromisoformat(booking['timestamp'][:-1]) if booking.get('timestamp') else datetime.utcnow()
    )
    db.session.add(new_booking)
    db.session.commit()
    return new_booking


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

@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
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
    session['user_id'] = user.id
    session['user_name'] = user.name
    return redirect('/booking.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return send_from_directory(BASE_DIR, 'login.html')

    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return redirect('/login.html?error=Invalid%20email%20or%20password.')

    session['user_id'] = user.id
    session['user_name'] = user.name
    return redirect('/booking.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login.html')

@app.route('/property-submit', methods=['POST'])
def property_submit():
    property_type = request.form.get('property_type', '').strip().lower()
    allowed_types = {'hotel', 'home', 'guest house', 'villa'}
    try:
        price_per_night = int(request.form.get('price_per_night', '0'))
        guests = int(request.form.get('guests', '0'))
    except ValueError:
        return redirect('/hospitality.html?error=Price%20and%20guest%20capacity%20must%20be%20numbers#list-property')

    property_data = {
        'owner_name': request.form.get('owner_name', '').strip(),
        'owner_email': request.form.get('owner_email', '').strip().lower(),
        'name': request.form.get('name', '').strip(),
        'property_type': property_type,
        'location': request.form.get('location', '').strip(),
        'price_per_night': price_per_night,
        'guests': guests,
        'image_url': request.form.get('image_url', '').strip(),
        'description': request.form.get('description', '').strip(),
    }
    required_values = [property_data['owner_name'], property_data['owner_email'], property_data['name'], property_type, property_data['location'], property_data['description']]
    if not all(required_values) or property_type not in allowed_types or price_per_night < 1 or guests < 1:
        return redirect('/hospitality.html?error=Please%20complete%20all%20listing%20fields%20with%20valid%20values#list-property')

    property_listing = Property(**property_data)
    db.session.add(property_listing)
    db.session.commit()
    return render_template_string(
        '''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Property Submitted - Lamu Tours</title><style>body{font-family:'Segoe UI',sans-serif;background:#eef2f7;margin:0;padding:2rem;color:#1e3c72}.card{max-width:650px;margin:0 auto;background:#fff;padding:2rem;border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,.12)}a{color:#ff7e3f;font-weight:600;text-decoration:none}</style></head><body><div class="card"><h1>Listing received</h1><p>Thank you, {{ listing.owner_name }}. <strong>{{ listing.name }}</strong> has been added to the owner listings.</p><p>Guests can now discover your {{ listing.property_type }} in {{ listing.location }} from ${{ listing.price_per_night }} per night.</p><p><a href="/hospitality.html">Return to hospitality listings</a></p></div></body></html>''', listing=property_listing)

@app.route('/properties', methods=['GET'])
def properties():
    listings = Property.query.order_by(Property.created_at.desc()).all()
    return {'properties': [property_listing.to_dict() for property_listing in listings]}

@app.route('/review-submit', methods=['POST'])
def review_submit():
    try:
        rating = int(request.form.get('rating', '0'))
    except ValueError:
        rating = 0

    review_data = {
        'reviewer_name': request.form.get('reviewer_name', '').strip(),
        'reviewer_email': request.form.get('reviewer_email', '').strip().lower(),
        'place': request.form.get('place', '').strip(),
        'rating': rating,
        'comment': request.form.get('comment', '').strip(),
    }
    if not all([review_data['reviewer_name'], review_data['reviewer_email'], review_data['place'], review_data['comment']]) or rating not in range(1, 6):
        return redirect('/hospitality.html?review_error=Please%20complete%20the%20review%20form%20and%20choose%20a%20rating#reviews')

    review = Review(**review_data)
    db.session.add(review)
    db.session.commit()
    return redirect('/hospitality.html?review_success=Your%20review%20was%20published#reviews')

@app.route('/reviews', methods=['GET'])
def reviews():
    recent_reviews = Review.query.order_by(Review.created_at.desc()).limit(50).all()
    return {'reviews': [review.to_dict() for review in recent_reviews]}

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(BASE_DIR, filename)

@app.route('/contact-submit', methods=['POST'])
def contact_submit():
    submission = {
        'name': request.form.get('name', 'Guest'),
        'email': request.form.get('email', ''),
        'subject': request.form.get('subject', ''),
        'message': request.form.get('message', ''),
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }

    email_sent = send_email_notification(submission)
    submission['email_sent'] = email_sent
    saved_submission = save_submission(submission)
    app.logger.info('Contact submission saved: %s', saved_submission.to_dict())

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
def booking_confirmation():
    allowed_country_codes = {'+1', '+27', '+44', '+91', '+254', '+255', '+256', '+971'}
    country_code = request.form.get('country_code', '').strip()
    phone = request.form.get('phone', '').strip()
    if country_code not in allowed_country_codes or not phone.isdigit():
        return redirect('/booking.html?error=Select%20a%20country%20code%20and%20enter%20numbers%20only')

    booking = {
        'name': request.form.get('name', 'Guest'),
        'email': request.form.get('email', ''),
        'phone': f'{country_code}{phone}',
        'tour': request.form.get('tour', ''),
        'date': request.form.get('date', ''),
        'time': request.form.get('time', ''),
        'guests': request.form.get('guests', '1'),
        'message': request.form.get('message', ''),
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    saved_booking = save_booking(booking)
    app.logger.info('Booking request saved: %s', saved_booking.to_dict())
    return send_from_directory(BASE_DIR, 'booking-confirmation.html')

@app.route('/dashboard', methods=['GET'])
def dashboard():
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
def submissions():
    all_submissions = Submission.query.order_by(Submission.timestamp.desc()).all()
    return {'submissions': [s.to_dict() for s in all_submissions]}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
