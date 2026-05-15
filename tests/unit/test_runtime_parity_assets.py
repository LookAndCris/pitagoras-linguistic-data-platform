from pathlib import Path


def test_runtime_parity_assets_define_backend_and_database_services() -> None:
    compose_content = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "services:" in compose_content
    assert "db:" in compose_content
    assert "backend:" in compose_content
    assert "postgres:16-alpine" in compose_content


def test_backend_container_image_has_fastapi_runtime_entrypoint() -> None:
    dockerfile_content = Path("docker/Dockerfile.backend").read_text(encoding="utf-8")

    assert "FROM python:3.12-slim" in dockerfile_content
    assert "poetry install" in dockerfile_content
    assert '"uvicorn"' in dockerfile_content
    assert "apps.backend.app.main:app" in dockerfile_content


def test_backend_bootstrap_is_documented_for_local_runtime() -> None:
    readme_content = Path("README.md").read_text(encoding="utf-8")

    assert "## Backend foundation bootstrap" in readme_content
    assert "docker compose up -d db" in readme_content
    assert "poetry run alembic -c apps/backend/alembic.ini upgrade head" in readme_content
