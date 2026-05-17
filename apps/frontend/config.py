from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_API_BASE_URL = "http://localhost:8000"
DEFAULT_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class FrontendConfig:
    base_url: str
    timeout_seconds: float


def get_frontend_config() -> FrontendConfig:
    base_url = os.getenv("PITAGORAS_FRONTEND_API_BASE_URL", DEFAULT_API_BASE_URL).strip()
    timeout_raw = os.getenv("PITAGORAS_FRONTEND_API_TIMEOUT_SECONDS")

    if timeout_raw is None:
        timeout_seconds = DEFAULT_TIMEOUT_SECONDS
    else:
        timeout_seconds = float(timeout_raw)

    return FrontendConfig(base_url=base_url, timeout_seconds=timeout_seconds)
