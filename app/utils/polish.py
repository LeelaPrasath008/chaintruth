"""Polish utilities — loading states, empty states, error handling."""
from __future__ import annotations
import streamlit as st
from utils.theme import T


def with_loading(label: str = "Loading data..."):
    """Return a spinner context manager with consistent styling."""
    return st.spinner(label)


def empty_state(title: str, body: str = ""):
    """Render a centered empty-state card."""
    st.markdown(
        f'<div style="text-align:center; padding:48px 24px; color:{T["text_muted"]};">'
        f'<div style="font-size:36px; margin-bottom:12px; opacity:0.3;">:material/inbox:</div>'
        f'<div style="font-size:16px; font-weight:600; color:{T["text"]};">{title}</div>'
        f'<div style="font-size:13px; margin-top:6px;">{body}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def safe_run(query_fn, *args, fallback_msg: str = "Unable to load data.", **kwargs):
    """Run a query function with error handling. Returns DataFrame or shows error."""
    try:
        return query_fn(*args, **kwargs)
    except Exception as e:
        st.error(f"{fallback_msg} ({type(e).__name__}: {e})")
        return None
