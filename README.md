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

### Optional: run a local Dockerized PostgreSQL for product-like simulation

Use this only for local/dev/test when you want to simulate production with a containerized PostgreSQL while preserving the external-DB-first default.

```bash
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d
PITAGORAS_DB_HOST=127.0.0.1 PITAGORAS_DB_PORT=${PITAGORAS_LOCAL_DB_PORT:-55432} PITAGORAS_DB_NAME=${PITAGORAS_LOCAL_DB_NAME:-pitagoras} PITAGORAS_DB_USER=${PITAGORAS_LOCAL_DB_USER:-pitagoras} PITAGORAS_DB_PASSWORD=${PITAGORAS_LOCAL_DB_PASSWORD:-pitagoras} PITAGORAS_DB_SSLMODE=disable poetry run alembic -c apps/backend/alembic.ini upgrade head
curl http://127.0.0.1:8000/health/ready
```

What this overlay changes:

| Area | Default (`docker-compose.yml`) | With `docker-compose.postgres.yml` |
|------|--------------------------------|-------------------------------------|
| Database source | External PostgreSQL | Compose-managed local PostgreSQL (`postgres:16-alpine`) |
| Backend DB host | `PITAGORAS_DB_HOST` from `.env` | Forced to `postgres` service name |
| SSL mode | `require` (or your env value) | Forced to `disable` for local container networking |
| DB port exposure | N/A | Host `${PITAGORAS_LOCAL_DB_PORT:-55432}` → container `5432` |

To stop/remove the local simulation stack:

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml down
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

## Frontend ingestion shell (Streamlit)

Run the thin frontend shell against the existing backend API:

```bash
export PITAGORAS_FRONTEND_API_BASE_URL="http://127.0.0.1:8000"
poetry run streamlit run apps/frontend/main.py
```

Notes:

- Default API base URL is `http://localhost:8000` when `PITAGORAS_FRONTEND_API_BASE_URL` is not set.
- The shell currently includes only these flows: **Manual ingestion**, **PDF upload**, and **Document list**.
- Auth, document detail, pagination, and search are intentionally out of scope for this slice.

## Test bootstrap

Run the minimal repository smoke test from the project root:

```bash
poetry install
poetry run pytest
```
