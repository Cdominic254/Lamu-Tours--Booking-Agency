# Lamu Tours & Booking Agency

Lamu Tours is a Flask-powered booking website for Lamu tours, accommodation, property listings, and traveler reviews.

## Local setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Open `http://127.0.0.1:5000` in a browser.

The `run.sh` script also starts the app and uses the local `venv` when it exists.

## Hosting

The included `Procfile` starts the app with Gunicorn:

```text
web: gunicorn --workers 2 --threads 4 --timeout 120 app:app
```

Configure these environment variables on the hosting provider:

- `SECRET_KEY`: long random value used to sign sessions
- `DATABASE_URL`: managed PostgreSQL URL for production persistence, or SQLite for temporary/single-instance hosting
- `SESSION_COOKIE_SECURE=true` when the site is served over HTTPS
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USERNAME`, `EMAIL_PASSWORD`, `EMAIL_FROM`, and `EMAIL_TO` for contact notifications

Install dependencies with `pip install -r requirements.txt`. The service should run the `Procfile` command and expose the provider's `PORT` value.

SQLite is suitable for local development, but many hosted platforms use ephemeral filesystems. Use managed PostgreSQL in production so bookings, users, properties, and reviews survive redeployments.
