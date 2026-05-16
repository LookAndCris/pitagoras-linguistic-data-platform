# pitagoras-linguistic-data-platform

## Backend foundation bootstrap

Run the backend with an external PostgreSQL instance (no compose-managed DB sidecar):

```bash
poetry install
cp .env.example .env
# edit .env with your external PostgreSQL values
poetry run alembic -c apps/backend/alembic.ini upgrade head
docker compose up -d backend
```

Required external PostgreSQL contract:

- `PITAGORAS_DB_HOST`
- `PITAGORAS_DB_PORT`
- `PITAGORAS_DB_NAME`
- `PITAGORAS_DB_USER`
- `PITAGORAS_DB_PASSWORD`

Recommended optional settings:

- `PITAGORAS_DB_SSLMODE`
- `PITAGORAS_DB_POOL_SIZE`
- `PITAGORAS_DB_MAX_OVERFLOW`
- `PITAGORAS_DB_POOL_RECYCLE_SECONDS`

Deploy order for external DB environments:
1. Configure `.env` from `.env.example`.
2. Run Alembic migrations against the external PostgreSQL target.
3. Start backend container with `docker compose up -d backend`.

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
