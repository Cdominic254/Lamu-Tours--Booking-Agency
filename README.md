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

## Deploy to Vercel

The project includes `vercel.json` and `api/index.py` for Vercel's Python runtime.

1. Import this repository in the Vercel dashboard, or run `vercel` from the project directory.
2. Set the project environment variables from the hosting section above. In particular, configure `DATABASE_URL` with a hosted PostgreSQL connection string and set a persistent `SECRET_KEY`.
3. Deploy with `vercel --prod`.

The deployed site will serve the Flask application at the Vercel URL. Do not open the HTML files directly when testing bookings; use the deployed URL so the form can reach the Flask booking endpoint.

### Host the database with Neon

1. Create a project at [neon.tech](https://neon.tech) and create a database named `lamu_tours`.
2. Copy the **pooled** PostgreSQL connection string from Neon. It normally starts with `postgresql://` and includes `sslmode=require`.
3. In Vercel, open the project settings, choose **Environment Variables**, and add `DATABASE_URL` with that connection string for Production, Preview, and Development.
4. Add a persistent random value as `SECRET_KEY` and set `SESSION_COOKIE_SECURE` to `true`.
5. Redeploy with `vercel --prod`.

When the deployment starts, the Flask application runs `db.create_all()` and creates the application's tables in the hosted database. The local `submissions.db` file is not uploaded to Vercel and remains useful only for local development.
