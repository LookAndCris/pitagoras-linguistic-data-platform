from pathlib import Path
import tomllib


def test_pytest_runner_bootstraps() -> None:
    assert Path("pyproject.toml").is_file()

    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["tool"]["poetry"].get("package-mode") is False
