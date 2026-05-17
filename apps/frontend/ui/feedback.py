from __future__ import annotations

from typing import Any

import streamlit as st

from apps.frontend.api.client import BackendApiError

STATUS_TITLES = {
    409: "Conflict",
    415: "Unsupported media type",
    422: "Validation error",
    503: "Service unavailable",
}


def format_error_detail(detail: Any) -> str:
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        messages: list[str] = []
        for item in detail:
            if isinstance(item, dict):
                loc = item.get("loc")
                msg = item.get("msg")
                if loc and msg:
                    messages.append(f"{'.'.join(str(part) for part in loc)}: {msg}")
                else:
                    messages.append(str(item))
            else:
                messages.append(str(item))
        return "; ".join(messages)
    return str(detail)


def build_error_message(error: BackendApiError) -> str:
    title = STATUS_TITLES.get(error.status_code, "Request failed")
    return f"{title} ({error.status_code}): {error.detail}"


def render_error(error: BackendApiError) -> None:
    st.error(build_error_message(error))


def render_success(message: str) -> None:
    st.success(message)


def render_created_document_summary(message: str, payload: dict[str, Any]) -> None:
    render_success(message)
    st.json(payload)


def render_empty_state(message: str) -> None:
    st.info(message)
