# Lamu Tourism App – Backend

Backend service for the Lamu tourism platform, providing APIs for experience discovery, booking, payments, and operator management. Built with Python and FastAPI, designed to support a low-bandwidth-friendly Android client for tourists and operators in Lamu, Kenya.

## Features

- Experience discovery and search (by date, category, price, availability)
- Booking management with capacity control and overbooking prevention
- Payments integration (e.g., M-Pesa, card providers)
- Operator onboarding and experience management
- Role-based access (tourist, operator, admin)
- SMS/push notifications for bookings and reminders

## Tech Stack

- **Language**: Python
- **Framework**: FastAPI
- **Database**: PostgreSQL
- **Cache / Queue**: Redis (caching, background tasks)
- **Deployment**: Docker on AWS ECS (or similar)
- **Auth**: JWT/OAuth2 with role-based access

## Project Structure

```text
backend/
  app/
    api/v1/          # API routes (experiences, bookings, payments, operators, auth)
    core/            # Config, security, utilities
    models/          # SQLAlchemy / ORM models
    schemas/         # Pydantic schemas (request/response)
    services/        # Business logic (search, booking, payments, notifications)
    db.py            # Database connection
    main.py          # FastAPI app entry point
  tests/
    api/             # API tests
    services/        # Service layer tests
  docs/
    requirements.md  # Detailed requirements and traceability
    architecture.md  # High-level design and data flows
    api-spec.yaml    # OpenAPI spec (can be auto-generated)
  Dockerfile
  pyproject.toml
  README.md
```

## Getting Started

### Prerequisites

- Python 3.11+  
- Docker (optional, for containerized run)  
- PostgreSQL  
- Redis  

### Local Development

1. **Clone the repository**

   ```bash
   git clone <repo-url>
   cd backend
   ```

2. **Set up environment variables**

   Create a `.env` file in the project root:

   ```env
   DATABASE_URL=postgresql://user:password@localhost:5432/lamu_db
   REDIS_URL=redis://localhost:6379/0
   SECRET_KEY=your-secret-key
   ENV=development
   ```

3. **Install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

4. **Run database migrations** *(adjust to your migration tool)*

   ```bash
   # Example if using Alembic or similar
   alembic upgrade head
   ```

5. **Start the server**

   ```bash
   uvicorn app.main:app --reload
   ```

6. **Open API docs**

   Visit: `http://localhost:8000/docs`

### Running with Docker

```bash
docker build -t lamu-backend .
docker run --env-file .env -p 8000:8000 lamu-backend
```

## Configuration

Key environment variables:

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: Secret for JWT signing
- `ENV`: `development`, `staging`, or `production`
- Payment and SMS provider keys (as needed)

## Testing

Run tests:

```bash
pytest
```

Structure:

- `tests/api/` – endpoint-level tests
- `tests/services/` – business logic tests (booking, payments, etc.)

Aim for tests that reflect acceptance criteria in `docs/requirements.md`.

## Documentation

- **Requirements**: [`docs/requirements.md`](docs/requirements.md)  
  Detailed functional and non-functional requirements, user personas, and traceability.
- **Architecture**: [`docs/architecture.md`](docs/architecture.md)  
  High-level design, data flows, and deployment overview.
- **API Spec**: [`docs/api-spec.yaml`](docs/api-spec.yaml) or `/docs` endpoint  
  OpenAPI/Swagger documentation for all endpoints.

## Deployment

Example (AWS ECS):

1. Build and push Docker image to ECR.
2. Update ECS task definition with new image and env vars.
3. Deploy new task revision.
4. Verify health checks and logs.

Adjust to your actual CI/CD pipeline.

## Contributing

1. Create a feature branch from `main`.
2. Implement changes with tests and updated docs as needed.
3. Ensure all tests pass:
   ```bash
   pytest
   ```
4. Open a pull request with:
   - Summary of changes
   - Linked issues or requirements from `docs/requirements.md`
   - Notes on any breaking changes

## License

[Add your license here, e.g., MIT, Proprietary, etc.]
