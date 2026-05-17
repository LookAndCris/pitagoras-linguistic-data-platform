from __future__ import annotations

import streamlit as st

from apps.frontend.api.client import BackendApiError, BackendClient
from apps.frontend.config import get_frontend_config
from apps.frontend.ui.feedback import render_error
from apps.frontend.views.document_list import render_document_list_view
from apps.frontend.views.manual_ingestion import render_manual_ingestion_view
from apps.frontend.views.pdf_upload import render_pdf_upload_view


def get_supported_flows() -> list[str]:
    return ["Manual ingestion", "PDF upload", "Document list"]


def render_shell() -> None:
    config = get_frontend_config()
    client = BackendClient(base_url=config.base_url, timeout_seconds=config.timeout_seconds)

    st.set_page_config(page_title="Pitagoras Ingestion Shell", layout="wide")
    st.title("Pitagoras Ingestion Shell")
    st.caption("Thin frontend boundary over existing backend document APIs")

    flow = st.sidebar.radio("Flow", get_supported_flows())

    if flow == "Document list":
        render_document_list_view(client)
        return

    try:
        metadata_options = client.get_metadata_options()
    except BackendApiError as error:
        render_error(error)
        return

    if flow == "Manual ingestion":
        render_manual_ingestion_view(client, metadata_options)
    else:
        render_pdf_upload_view(client, metadata_options)


if __name__ == "__main__":
    render_shell()
