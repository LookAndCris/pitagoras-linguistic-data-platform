from pathlib import Path


def test_env_template_and_gitignore_define_secret_boundary() -> None:
    env_example_path = Path(".env.example")
    gitignore_content = Path(".gitignore").read_text(encoding="utf-8")

    assert env_example_path.exists()
    assert ".env" in gitignore_content


def test_runtime_parity_assets_define_backend_service_for_external_database_runtime() -> None:
    compose_content = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "services:" in compose_content
    assert "backend:" in compose_content
    assert "docker/Dockerfile.backend" in compose_content


def test_compose_uses_external_database_contract_without_sidecar() -> None:
    compose_content = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "backend:" in compose_content
    assert "db:" not in compose_content
    assert "postgres:16-alpine" not in compose_content
    assert "env_file:" in compose_content
    assert "- .env" in compose_content
    assert "--reload" not in compose_content
    assert "- .:/app" not in compose_content


def test_backend_container_image_has_fastapi_runtime_entrypoint() -> None:
    dockerfile_content = Path("docker/Dockerfile.backend").read_text(encoding="utf-8")

    assert "FROM python:3.12-slim" in dockerfile_content
    assert "poetry install" in dockerfile_content
    assert "--no-root" in dockerfile_content
    assert '"uvicorn"' in dockerfile_content
    assert "--factory" in dockerfile_content
    assert "apps.backend.app.main:create_app" in dockerfile_content
    assert "--reload" not in dockerfile_content


def test_backend_bootstrap_is_documented_for_local_runtime() -> None:
    readme_content = Path("README.md").read_text(encoding="utf-8")

    assert "## Backend foundation bootstrap" in readme_content
    assert "docker compose up -d backend" in readme_content
    assert "external PostgreSQL instance" in readme_content
    assert "cp .env.example .env" in readme_content


def test_env_template_and_readme_keep_required_database_contract_in_sync() -> None:
    required_env_keys = {
        "PITAGORAS_DB_HOST",
        "PITAGORAS_DB_PORT",
        "PITAGORAS_DB_NAME",
        "PITAGORAS_DB_USER",
        "PITAGORAS_DB_PASSWORD",
    }
    env_example_content = Path(".env.example").read_text(encoding="utf-8")
    readme_content = Path("README.md").read_text(encoding="utf-8")

    for key in required_env_keys:
        assert f"{key}=" in env_example_content
        assert key in readme_content
