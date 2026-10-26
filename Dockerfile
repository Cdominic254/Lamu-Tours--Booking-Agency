FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    SITE_URL=http://localhost:5000 \
    DATABASE_URL=sqlite:////tmp/submissions.db \
    RATELIMIT_STORAGE_URI=memory://

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./
COPY saas/ ./saas/
COPY templates/ ./templates/
COPY images/ ./images/
COPY pictures/ ./pictures/
COPY *.html *.js *.css *.svg ./
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

RUN mkdir -p /app/uploads \
    && chown -R 10001:10001 /app/uploads

USER 10001:10001

EXPOSE 5000

CMD ["gunicorn", "--workers", "2", "--threads", "4", "--timeout", "120", "--bind", "0.0.0.0:5000", "app:app"]
