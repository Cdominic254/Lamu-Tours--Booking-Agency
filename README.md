# Lamu Tours & Booking Agency

Lamu Tours is a Flask-powered booking website for Lamu tours, accommodation, property listings, and traveler reviews.

## Project structure

```text
api/index.py             Vercel Python Function entrypoint
app.py                   Flask application and compatibility routes
saas/                    Shared database extension and domain modules
  modules/
    identity/            Customer, vendor, and admin models
    catalog/             Tours, properties, schedules, and reviews
    bookings/            Booking models, settings, and services
    messaging/            Contact and messaging models
frontend/                React, Vite, and Tailwind application
images/  pictures/       Committed listing and Lamu photography
templates/               Server-rendered fallback/admin templates
tests/                   Backend and deployment configuration tests
```

Keep `app.py`, `api/index.py`, and `requirements.txt` at the repository root: Vercel's Python builder uses the root dependency file, and `api/index.py` imports the Flask application. Existing package and static-asset folder names are deliberately retained because routes, catalogue records, and the frontend reference them.

The backend is a modular monolith: one Flask deployment and database, with code grouped by business domain. The shared SQLAlchemy extension is in `saas/extensions.py`. `app.py` remains the compatibility layer for existing URLs while services move into `saas/modules/`.

## Local setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
npm --prefix frontend install
npm --prefix frontend run build
cp .env.example .env
python app.py
```

Open `http://127.0.0.1:5000` in a browser.

The `run.sh` script also starts the app and uses the local `venv` when it exists.

### React frontend

The visitor-facing website is built with React, Vite, and Tailwind CSS. Flask remains the backend for bookings, payments, accounts, the public catalogue, and admin pages.

For frontend development, start Flask with `python app.py` and run the Vite development server in a second terminal:

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

Open `http://127.0.0.1:5173`. Vite proxies API, form, and image requests to Flask on port 5000. To serve the production frontend through Flask locally, run `npm --prefix frontend run build` before starting the app. Vercel builds the frontend during deployment.

### Language selection

Visitor pages include a language button in the navigation to switch between English and Kiswahili. The selected language is saved in the browser and used across the site's pages. Shared translations and the client-side localization engine are in `localization.js`; add English-to-Kiswahili entries there as page copy is updated.

### Currency display

Visitor pages use the incoming public IP address to detect a visitor's country and automatically display prices in the country's currency. Currency is converted from KSh using daily rates from [ExchangeRate-API](https://www.exchangerate-api.com/), while geolocation is provided by [ipapi](https://ipapi.co/). The server caches currency data for 12 hours. These services receive the visitor IP for geolocation; review their current privacy policies and terms before deployment.

Converted prices are estimates for display only. Booking records and M-Pesa payments use KSh. If IP detection or rate lookup fails, the site falls back to KSh.

### Catalog and admin accounts

Tours, properties, trending destinations, role accounts, platform operations, and analytics are managed from `/admin`; recent bookings and contact messages are available at `/dashboard`. Admin operations include customer/vendor access suspension, booking oversight, dispute case notes/resolution, paid revenue reporting, and commission settings. Commission defaults to 15% and is limited to 10–20%; each new booking snapshots the current rate. The cancellation cutoff remains 48 hours. Paid refund requests require manual review and processing outside the application; the dashboard does not issue gateway refunds. Configure `ADMIN_EMAIL` and `ADMIN_PASSWORD` in the app environment before the first start to bootstrap the initial admin account. The password is stored as a hash; signed-in admins can add other admin accounts and manage the public catalog. Use a unique password of at least 12 characters for additional accounts.

Reviews are associated with the tour or property they describe. Bookable tours and stays, and trending destinations, are loaded from the catalog.
Public review submission is rate-limited and validates field lengths, rating, target, and email server-side.

### Vendor accounts

Vendors register at `/vendor/register` and sign in at `/vendor/login`; vendor access is separate from traveler and admin sign-in. The `/vendor/dashboard` portal allows each vendor to create, update, and remove only the tours and properties they own, publish dated departures with guest capacity, upload listing photos, manage itinerary and inclusions, and process bookings for their own tours. Admins can review vendor accounts and their listings in `/admin`, and remove vendor accounts when needed. Configure `SECRET_KEY` with a persistent random value so secure registration and role sessions remain valid across app restarts.

Vendor booking statuses follow `requested → confirmed → in preparation → completed`; a requested, confirmed, or in-preparation booking can instead be cancelled. Each transition is scoped to tours belonging to the signed-in vendor. Customer status emails are sent when SMTP is configured. A cancellation updates the booking and releases its reserved capacity; it does not automatically refund a captured payment.

### Customer bookings and tour information

Tours can be browsed by category. Admins and vendors can edit category, itinerary, inclusions/exclusions, pickup point, group-size limits, and tour photos. A tour must have future departures published in the dashboard before it can be booked. Departure capacity is reserved atomically when a request is submitted; a full departure is removed from public availability. Photo uploads accept JPEG, PNG, or WebP files up to 10 MB.

Customers can book as guests or while signed in. Only bookings made while signed in are associated with a customer account and visible at `/my-bookings`. Signed-in customers can cancel or reschedule eligible bookings at least 48 hours before departure. Changes are protected by account ownership and CSRF checks. Tour reviews remain available on the tour detail page.

Tour bookings are paid in KES through Safaricom Daraja Lipa Na M-Pesa Online (STK Push). A booking remains pending until its callback is checked against Daraja's STK Query API; browser redirects are not used as proof of payment. The departure remains reserved while the customer completes the M-Pesa prompt, and failed payments release the reservation. Pending payments cannot be cancelled because Daraja does not provide a reliable way to withdraw an STK prompt after it has been sent. Booking and status emails are sent when SMTP is configured. WhatsApp delivery is not enabled; the messaging service can be extended with a WhatsApp provider when credentials and provider preferences are available.

## Hosting

The included `Procfile` starts the app with Gunicorn:

```text
web: gunicorn --workers 2 --threads 4 --timeout 120 app:app
```

Configure these environment variables on the hosting provider:

- `SECRET_KEY`: long random value used to sign sessions
- `DATABASE_URL`: managed PostgreSQL URL for production persistence, or SQLite for temporary/single-instance hosting
- `SITE_URL=https://lamutours.co.ke`: canonical public site URL
- `SESSION_COOKIE_SECURE=true` when the site is served over HTTPS
- `RATELIMIT_STORAGE_URI`: shared Redis URL for production rate-limit state (`memory://` is only for local development and the app refuses to start in production with it)
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USERNAME`, `EMAIL_PASSWORD`, `EMAIL_FROM`, and `EMAIL_TO` for contact notifications
- `DARAJA_ENV`: `sandbox` while testing, then `production` after go-live approval
- `DARAJA_CONSUMER_KEY`, `DARAJA_CONSUMER_SECRET`, `DARAJA_SHORTCODE`, and `DARAJA_PASSKEY`: credentials from the Safaricom Daraja portal; keep them in secret environment settings
- `DARAJA_CALLBACK_URL`: public HTTPS endpoint, for example `https://lamutours.co.ke/daraja/callback`
- `ADMIN_EMAIL` and `ADMIN_PASSWORD`: bootstrap the first admin account when the database has no admins

Install dependencies with `pip install -r requirements.txt`. The service should run the `Procfile` command and expose the provider's `PORT` value.

Start with Daraja sandbox credentials and use a publicly reachable HTTPS callback URL. Verify successful, cancelled, and timed-out STK requests before switching `DARAJA_ENV` to `production` and using production credentials. Safaricom must approve the shortcode, passkey, and Lipa Na M-Pesa Online product for live transactions. Never commit credentials or put them in callback URLs.

SQLite is suitable for local development, but many hosted platforms use ephemeral filesystems. Use managed PostgreSQL in production so bookings, users, properties, and reviews survive redeployments.

## Deploy to Vercel

The project includes `vercel.json` and `api/index.py` for Vercel's Python runtime. The Vercel config builds the React app from `frontend/package.json`, routes requests through Flask, and packages the built frontend, local image directories, and fallback templates with the Python function. `.vercelignore` omits local environments, secrets, databases, test files, and temporary uploads.

### Continuous integration and deployment

GitHub Actions runs backend tests and builds the frontend on every push and pull request. To enable automatic Vercel deployments, add these repository secrets in **Settings → Secrets and variables → Actions**:

- `VERCEL_TOKEN`: a Vercel access token
- `VERCEL_ORG_ID`: the Vercel team or account ID
- `VERCEL_PROJECT_ID`: this project's Vercel project ID

Then add the repository variable `VERCEL_DEPLOY_ENABLED` with the value `true`. Pull requests from branches in this repository deploy a Vercel Preview; pushes to `main` deploy to Production. Fork pull requests run CI but do not deploy, because GitHub does not provide repository secrets to them. Leave the variable unset to run CI without deployments.

1. Import this repository in the Vercel dashboard, or run `vercel` from the project directory.
2. Add `lamutours.co.ke` to the Vercel project's **Settings → Domains** and follow Vercel's DNS instructions at your domain registrar. Set the apex domain as the primary domain; add `www.lamutours.co.ke` too if you want Vercel to redirect it.
3. Set the project environment variables from the hosting section above, including `SITE_URL=https://lamutours.co.ke`, a Redis-backed `RATELIMIT_STORAGE_URI`, and `SESSION_COOKIE_SECURE=true`. The app refuses to start in production if the shared rate-limit store or persistent `SECRET_KEY` is missing. Configure `DATABASE_URL` with a hosted PostgreSQL connection string. Use a Redis-compatible managed store and keep its URL private.
4. Deploy with `vercel --prod`, then confirm HTTPS works at `https://lamutours.co.ke` and set `DARAJA_CALLBACK_URL` to `https://lamutours.co.ke/daraja/callback`.

Vercel must verify the domain through the DNS records it provides before the custom domain serves the deployment. Do not open the HTML files directly when testing bookings; use the deployed URL so the form can reach the Flask booking endpoint.

**Before launch:** configure external object storage for admin/vendor image uploads. Vercel Function filesystems are not durable, so uploads are deliberately rejected on Vercel until persistent storage is integrated. Existing committed files under `images/` and `pictures/` are bundled and served normally. Use image URLs or current static assets until uploads have a persistent storage provider.

For other hosting providers, build the React frontend before starting the Flask `Procfile` command:

```bash
npm --prefix frontend ci
npm --prefix frontend run build
```

### Host the database with Neon

1. Create a project at [neon.tech](https://neon.tech) and create a database named `lamu_tours`.
2. Copy the **pooled** PostgreSQL connection string from Neon. It normally starts with `postgresql://` and includes `sslmode=require`.
3. In Vercel, open the project settings, choose **Environment Variables**, and add `DATABASE_URL` with that connection string for Production, Preview, and Development.
4. Add a persistent random value as `SECRET_KEY` and set `SESSION_COOKIE_SECURE` to `true`.
5. Redeploy with `vercel --prod`.

When the deployment starts, the Flask application runs `db.create_all()` and creates the application's tables in the hosted database. The local `submissions.db` file is not uploaded to Vercel and remains useful only for local development.
