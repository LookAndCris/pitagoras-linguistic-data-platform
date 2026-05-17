from __future__ import annotations

from apps.frontend.api.client import BackendApiError, BackendClient, build_subcategory_list
from apps.frontend.ui.feedback import render_created_document_summary, render_error

import streamlit as st


def _required_fields_present(payload: dict[str, str], has_file: bool) -> bool:
    required_keys = ["doc_id", "category", "subcategory_raw", "source"]
    missing = [key for key in required_keys if not payload.get(key, "").strip()]

    if missing or not has_file:
        st.warning("Complete all required fields and attach one PDF file before submitting.")
        return False
    return True


def render_pdf_upload_view(client: BackendClient) -> None:
    st.subheader("PDF upload")

    payload = {
        "doc_id": st.text_input("Document ID"),
        "category": st.text_input("Category"),
        "subcategory_raw": st.text_input("Subcategory (comma-separated)"),
        "source": st.text_input("Source"),
        "url": st.text_input("URL (optional)"),
        "publication_date": st.text_input("Publication date (optional, YYYY-MM-DD)"),
    }

    uploaded_file = st.file_uploader("PDF file", type=["pdf"])

    if not st.button("Upload PDF document"):
        return

    if uploaded_file is None:
        has_file = False
    else:
        has_file = bool(uploaded_file.name and uploaded_file.type == "application/pdf")

    if not _required_fields_present(payload, has_file=has_file):
        return

    metadata = {
        "doc_id": payload["doc_id"].strip(),
        "category": payload["category"].strip(),
        "subcategory": build_subcategory_list(payload["subcategory_raw"]),
        "source": payload["source"].strip(),
    }

    if payload["url"].strip():
        metadata["url"] = payload["url"].strip()
    if payload["publication_date"].strip():
        metadata["publication_date"] = payload["publication_date"].strip()

    try:
        created = client.upload_pdf_document(
            metadata,
            filename=uploaded_file.name,
            content=uploaded_file.getvalue(),
            content_type=uploaded_file.type,
        )
    except BackendApiError as error:
        render_error(error)
        return

    render_created_document_summary("Document created successfully from PDF upload.", created)
