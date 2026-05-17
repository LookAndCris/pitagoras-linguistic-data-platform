import tomllib
from pathlib import Path


def test_pdf_ingestion_dependencies_are_declared() -> None:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    dependencies = data["tool"]["poetry"]["dependencies"]

    assert "pypdf" in dependencies
    assert "python-multipart" in dependencies


def test_backend_runtime_dependency_for_container_entrypoint_is_declared() -> None:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    dependencies = data["tool"]["poetry"]["dependencies"]

    assert "uvicorn" in dependencies


def test_psycopg_uses_binary_distribution_for_slim_docker_runtime() -> None:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    dependencies = data["tool"]["poetry"]["dependencies"]

    psycopg_dependency = dependencies["psycopg"]
    assert isinstance(psycopg_dependency, dict)
    assert "binary" in psycopg_dependency["extras"]


def test_frontend_runtime_dependencies_are_declared() -> None:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    dependencies = data["tool"]["poetry"]["dependencies"]

    assert "streamlit" in dependencies
    assert "httpx" in dependencies
