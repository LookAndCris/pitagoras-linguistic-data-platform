from __future__ import annotations

from collections.abc import Sequence

from apps.frontend.api.client import BackendApiError, BackendClient, build_subcategory_list
from apps.frontend.ui.feedback import render_created_document_summary, render_error

import streamlit as st


def _required_fields_present(payload: dict[str, str]) -> bool:
    required_keys = ["category", "subcategory_raw", "source", "raw_text"]
    missing = [key for key in required_keys if not payload.get(key, "").strip()]
    if missing:
        st.warning("Complete all required fields: Category, Subcategory, Source, and Raw text.")
        return False
    return True


def render_manual_ingestion_view(client: BackendClient, metadata_options: dict[str, Sequence[str]]) -> None:
    st.subheader("Manual ingestion")

    categories = list(metadata_options.get("categories", []))
    sources = list(metadata_options.get("sources", []))

    payload = {
        "category": st.selectbox("Category", categories),
        "subcategory_raw": st.text_input("Subcategory (comma-separated)"),
        "source": st.selectbox("Source", sources),
        "url": st.text_input("URL (optional)"),
        "publication_year": st.number_input("Publication year (optional)", min_value=1, max_value=9999, value=None),
        "raw_text": st.text_area("Raw text", height=180),
    }

    if not st.button("Submit manual document"):
        return

    if not _required_fields_present(payload):
        return

    request_body = {
        "category": payload["category"].strip(),
        "subcategory": build_subcategory_list(payload["subcategory_raw"]),
        "source": payload["source"].strip(),
        "raw_text": payload["raw_text"].strip(),
    }

    if payload["url"].strip():
        request_body["url"] = payload["url"].strip()
    if payload["publication_year"] is not None:
        request_body["publication_year"] = int(payload["publication_year"])

    try:
        created = client.create_document(request_body)
    except BackendApiError as error:
        render_error(error)
        return

    render_created_document_summary("Document created successfully.", created)
