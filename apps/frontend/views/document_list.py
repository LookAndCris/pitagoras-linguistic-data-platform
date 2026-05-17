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


def _build_category_summary_rows(categories: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for category_item in categories:
        percentage = category_item.get("percentage", 0)
        if isinstance(percentage, int | float):
            percentage_label = f"{percentage:.2f}%"
        else:
            percentage_label = str(percentage)

        rows.append(
            {
                "category": category_item.get("category"),
                "total_words": category_item.get("total_words"),
                "percentage": percentage_label,
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

    summary = response.get("summary", {})
    summary_sample_count = summary.get("sample_count", len(items))
    summary_total_words = summary.get("total_words", 0)
    category_rows = _build_category_summary_rows(summary.get("categories", []))

    metric_columns = st.columns(2)
    metric_columns[0].metric("Samples", summary_sample_count)
    metric_columns[1].metric("Total words", summary_total_words)

    table_rows = _build_table_rows(items)
    st.dataframe(table_rows, use_container_width=True, hide_index=True)
    st.dataframe(category_rows, use_container_width=True, hide_index=True)
