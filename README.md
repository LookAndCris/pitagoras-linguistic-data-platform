# pitagoras-linguistic-data-platform

## Backend foundation bootstrap

Run the backend foundation stack locally with Poetry and Docker Compose:

```bash
poetry install
docker compose up -d db
poetry run alembic -c apps/backend/alembic.ini upgrade head
poetry run uvicorn apps.backend.app.main:app --reload
```

Smoke-check API runtime endpoints:

```bash
curl http://127.0.0.1:8000/health/live
curl http://127.0.0.1:8000/health/ready
curl http://127.0.0.1:8000/documents
```

## Test bootstrap

Run the minimal repository smoke test from the project root:

```bash
poetry install
poetry run pytest
```
