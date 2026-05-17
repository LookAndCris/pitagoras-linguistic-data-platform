from __future__ import annotations

import streamlit as st

from apps.frontend.api.client import BackendApiError, BackendClient
from apps.frontend.ui.feedback import render_empty_state, render_error


def _build_table_rows(items: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in items:
        subcategory = item.get("subcategory")
        if isinstance(subcategory, list):
            subcategory_value = ", ".join(str(value) for value in subcategory)
        else:
            subcategory_value = subcategory

        rows.append(
            {
                "doc_id": item.get("doc_id"),
                "category": item.get("category"),
                "subcategory": subcategory_value,
                "source": item.get("source"),
                "word_count": item.get("word_count"),
                "created_at": item.get("created_at"),
            }
        )

    return rows


def render_document_list_view(client: BackendClient) -> None:
    st.subheader("Document list")
    st.button("Refresh list")

    try:
        response = client.list_documents()
    except BackendApiError as error:
        render_error(error)
        return

    items = response.get("items", [])
    if not items:
        render_empty_state("No documents found.")
        return

    table_rows = _build_table_rows(items)
    st.dataframe(table_rows, use_container_width=True, hide_index=True)
