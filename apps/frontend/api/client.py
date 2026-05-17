from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx


@dataclass
class BackendApiError(Exception):
    status_code: int
    detail: str

    def __str__(self) -> str:
        return f"Backend API error ({self.status_code}): {self.detail}"


def build_subcategory_list(raw: str | list[str]) -> list[str]:
    if isinstance(raw, list):
        candidates = raw
    else:
        candidates = raw.split(",")
    return [item.strip() for item in candidates if item.strip()]


def _normalize_detail(detail: Any) -> str:
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        messages: list[str] = []
        for item in detail:
            if isinstance(item, dict):
                loc = item.get("loc")
                msg = item.get("msg")
                if loc and msg:
                    loc_value = ".".join(str(part) for part in loc)
                    messages.append(f"{loc_value}: {msg}")
                else:
                    messages.append(str(item))
            else:
                messages.append(str(item))
        return "; ".join(messages)
    if detail is None:
        return "Unknown backend error"
    return str(detail)


def _serialize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    serialized: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, date):
            serialized[key] = value.isoformat()
        else:
            serialized[key] = value
    return serialized


class BackendClient:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def normalize_http_error(self, error: httpx.HTTPStatusError) -> BackendApiError:
        detail: Any
        try:
            payload = error.response.json()
            detail = payload.get("detail") if isinstance(payload, dict) else payload
        except ValueError:
            detail = error.response.text or "HTTP error"
        return BackendApiError(status_code=error.response.status_code, detail=_normalize_detail(detail))

    def normalize_transport_error(self, error: httpx.RequestError) -> BackendApiError:
        return BackendApiError(status_code=503, detail=f"Could not reach backend service: {error}")

    def request_json(self, method: str, path: str, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.request(method=method, url=url, json=json_body)
                response.raise_for_status()
                if response.content:
                    return response.json()
                return {}
        except httpx.HTTPStatusError as error:
            raise self.normalize_http_error(error) from error
        except httpx.RequestError as error:
            raise self.normalize_transport_error(error) from error

    def create_document(self, payload: dict[str, Any]) -> dict[str, Any]:
        serialized = _serialize_payload(payload)
        return self.request_json("POST", "/documents", json_body=serialized)

    def list_documents(self) -> dict[str, Any]:
        return self.request_json("GET", "/documents")

    def upload_pdf_document(
        self,
        metadata: dict[str, Any],
        *,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/documents/upload-pdf"
        data: list[tuple[str, str]] = []

        for key in ("doc_id", "category", "source"):
            value = metadata.get(key)
            if value is not None:
                data.append((key, str(value)))

        for item in build_subcategory_list(metadata.get("subcategory", [])):
            data.append(("subcategory", item))

        for optional_key in ("url", "publication_date"):
            value = metadata.get(optional_key)
            if value:
                data.append((optional_key, str(value)))

        files = {"file": (filename, content, content_type)}

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(url=url, data=data, files=files)
                response.raise_for_status()
                if response.content:
                    return response.json()
                return {}
        except httpx.HTTPStatusError as error:
            raise self.normalize_http_error(error) from error
        except httpx.RequestError as error:
            raise self.normalize_transport_error(error) from error
