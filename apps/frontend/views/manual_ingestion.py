from __future__ import annotations

from apps.frontend.api.client import BackendApiError, BackendClient, build_subcategory_list
from apps.frontend.ui.feedback import render_created_document_summary, render_error

import streamlit as st


def _required_fields_present(payload: dict[str, str]) -> bool:
    required_keys = ["doc_id", "category", "subcategory_raw", "source", "raw_text"]
    missing = [key for key in required_keys if not payload.get(key, "").strip()]
    if missing:
        st.warning("Complete all required fields: Document ID, Category, Subcategory, Source, and Raw text.")
        return False
    return True


def render_manual_ingestion_view(client: BackendClient) -> None:
    st.subheader("Manual ingestion")

    payload = {
        "doc_id": st.text_input("Document ID"),
        "category": st.text_input("Category"),
        "subcategory_raw": st.text_input("Subcategory (comma-separated)"),
        "source": st.text_input("Source"),
        "url": st.text_input("URL (optional)"),
        "publication_date": st.text_input("Publication date (optional, YYYY-MM-DD)"),
        "raw_text": st.text_area("Raw text", height=180),
    }

    if not st.button("Submit manual document"):
        return

    if not _required_fields_present(payload):
        return

    request_body = {
        "doc_id": payload["doc_id"].strip(),
        "category": payload["category"].strip(),
        "subcategory": build_subcategory_list(payload["subcategory_raw"]),
        "source": payload["source"].strip(),
        "raw_text": payload["raw_text"].strip(),
    }

    if payload["url"].strip():
        request_body["url"] = payload["url"].strip()
    if payload["publication_date"].strip():
        request_body["publication_date"] = payload["publication_date"].strip()

    try:
        created = client.create_document(request_body)
    except BackendApiError as error:
        render_error(error)
        return

    render_created_document_summary("Document created successfully.", created)
