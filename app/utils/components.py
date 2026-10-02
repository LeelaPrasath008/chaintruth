"""Shared UI components. Every page uses these instead of raw HTML."""

from __future__ import annotations
import html as html_mod
import streamlit as st
import pandas as pd
from utils.theme import T

# ---------------------------------------------------------------------------
# SVG icon library  (18px, stroke=currentColor, line style)
# ---------------------------------------------------------------------------
_ICONS: dict[str, str] = {
    "chart": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 3v18h18"/><path d="M7 16l4-8 4 4 5-9"/></svg>',
    "dollar": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>',
    "alert": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    "factory": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M2 20h20"/><path d="M5 20V8l5 4V8l5 4V4h3v16"/></svg>',
    "box": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>',
    "clock": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    "shield": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    "search": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
    "graph": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="5" cy="6" r="2"/><circle cx="19" cy="6" r="2"/><circle cx="12" cy="18" r="2"/><line x1="5" y1="8" x2="12" y2="16"/><line x1="19" y1="8" x2="12" y2="16"/></svg>',
    "book": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/></svg>',
    "sparkle": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 2l2.09 6.26L20 10l-5.91 1.74L12 18l-2.09-6.26L4 10l5.91-1.74L12 2z"/></svg>',
    "link": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/></svg>',
    "check": '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>',
    "x": '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
    "minus": '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><line x1="5" y1="12" x2="19" y2="12"/></svg>',
    "truck": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M1 3h15v13H1z"/><path d="M16 8h4l3 3v5h-7V8z"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>',
    "users": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>',
    "download": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>',
}


def icon(name: str) -> str:
    return _ICONS.get(name, "")


# ---------------------------------------------------------------------------
# Sidebar brand
# ---------------------------------------------------------------------------
def sidebar_brand():
    st.sidebar.markdown(
        '<div class="ct-sidebar-brand">'
        '<div class="ct-logo">Chain<span>Truth</span></div>'
        '<span class="ct-env">ENTERPRISE ANALYTICS</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        '<div class="ct-sidebar-footer">Powered by Snowflake &middot; Streamlit</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Page header with badges
# ---------------------------------------------------------------------------
_DEFAULT_BADGES = ["Governed Metrics", "Ontology Enabled", "Demo Ready"]


def page_header(title: str, subtitle: str = "", freshness: str = "Governed data",
                badges: list[str] | None = None):
    right = f'<span>{html_mod.escape(freshness)}</span>'
    sub_html = f"<p>{html_mod.escape(subtitle)}</p>" if subtitle else ""
    badge_list = badges if badges is not None else _DEFAULT_BADGES
    badges_html = ""
    if badge_list:
        pills = "".join(
            f'<span class="ct-badge"><span class="ct-badge-dot"></span>{html_mod.escape(b)}</span>'
            for b in badge_list
        )
        badges_html = f'<div class="ct-badge-row">{pills}</div>'
    st.markdown(
        f'<div class="ct-page-header">'
        f'<div class="ct-ph-left"><h1>{html_mod.escape(title)}</h1>{sub_html}{badges_html}</div>'
        f'<div class="ct-ph-right">{right}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Section header
# ---------------------------------------------------------------------------
def section(title: str):
    st.markdown(f'<div class="ct-section">{html_mod.escape(title)}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# KPI card with icon circle
# ---------------------------------------------------------------------------
def kpi_card(
    label: str,
    value: str,
    *,
    status: str | None = None,
    caption: str | None = None,
    icon_name: str | None = None,
) -> str:
    chip = ""
    if status == "healthy":
        chip = f'<span class="ct-chip ct-chip-success">{_ICONS["check"]} Healthy</span>'
    elif status == "warning":
        chip = f'<span class="ct-chip ct-chip-warning">{_ICONS["minus"]} Warning</span>'
    elif status == "critical":
        chip = f'<span class="ct-chip ct-chip-danger">{_ICONS["x"]} Critical</span>'
    elif status == "neutral":
        chip = '<span class="ct-chip ct-chip-neutral">-</span>'

    icon_html = ""
    if icon_name and icon_name in _ICONS:
        icon_html = f'<span class="ct-kpi-icon">{_ICONS[icon_name]}</span>'

    cap = f'<div class="ct-kpi-caption">{html_mod.escape(caption)}</div>' if caption else ""

    return (
        f'<div class="ct-kpi">'
        f'<div class="ct-kpi-top">'
        f'{icon_html}'
        f'<span class="ct-kpi-label" title="{html_mod.escape(label)}">{html_mod.escape(label)}</span>'
        f'{chip}'
        f'</div>'
        f'<div class="ct-kpi-value">{html_mod.escape(value)}</div>'
        f'{cap}'
        f'</div>'
    )


def kpi_grid(cards: list[str]):
    inner = "\n".join(cards)
    st.markdown(f'<div class="ct-kpi-grid">{inner}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Status chip (standalone)
# ---------------------------------------------------------------------------
def status_chip(text: str, kind: str = "neutral") -> str:
    svg = {"success": "check", "warning": "minus", "danger": "x"}.get(kind, "")
    svg_html = _ICONS.get(svg, "")
    return f'<span class="ct-chip ct-chip-{kind}">{svg_html} {html_mod.escape(text)}</span>'


# ---------------------------------------------------------------------------
# Insight panel
# ---------------------------------------------------------------------------
def insight(title: str, body: str, level: str = "") -> str:
    cls = f"ct-insight ct-insight-{level}" if level else "ct-insight"
    return (
        f'<div class="{cls}">'
        f'<div class="ct-it">{title}</div>'
        f'<div class="ct-ib">{body}</div>'
        f'</div>'
    )


def insight_panel(items: list[str]):
    st.markdown("\n".join(items), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Alert
# ---------------------------------------------------------------------------
def alert_card(title: str, body: str, kind: str = "info") -> str:
    return (
        f'<div class="ct-alert ct-alert-{kind}">'
        f'<strong>{html_mod.escape(title)}</strong>'
        f'{body}'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Enhanced table
# ---------------------------------------------------------------------------
def enhanced_table(df: pd.DataFrame, key: str, *, title: str | None = None,
                   searchable: bool = True, downloadable: bool = True,
                   height: int = 420, hide_index: bool = True):
    """Searchable, downloadable dataframe with row count."""
    total = len(df)
    df_view = df.copy()

    toolbar_cols = st.columns([3, 1, 1] if downloadable else [4, 1])

    if searchable:
        with toolbar_cols[0]:
            q = st.text_input(
                "Search", key=f"ct_ui_{key}_q",
                placeholder="Search...", label_visibility="collapsed",
            )
            if q:
                mask = df_view.astype(str).apply(
                    lambda c: c.str.contains(q, case=False, na=False)
                ).any(axis=1)
                df_view = df_view[mask]

    if downloadable:
        with toolbar_cols[-1]:
            st.download_button(
                f"{icon('download')} CSV", df_view.to_csv(index=False).encode(),
                file_name=f"{key}.csv", mime="text/csv",
                key=f"ct_ui_{key}_dl", use_container_width=True,
            )

    st.dataframe(df_view, use_container_width=True, hide_index=hide_index, height=height)
    showing = len(df_view)
    st.markdown(
        f'<div style="font-size:12px; color:{T["text_muted"]}; margin-top:-8px; margin-bottom:12px;">'
        f'Showing {showing:,} of {total:,} rows</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Typing indicator
# ---------------------------------------------------------------------------
def typing_indicator():
    st.markdown(
        '<div class="ct-typing"><span></span><span></span><span></span></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Skeleton loaders
# ---------------------------------------------------------------------------
def skeleton(kind: str = "text", n: int = 1):
    cls_map = {"kpi": "ct-skel ct-skel-kpi", "chart": "ct-skel ct-skel-chart",
               "text": "ct-skel ct-skel-text"}
    cls = cls_map.get(kind, "ct-skel ct-skel-text")
    for _ in range(n):
        st.markdown(f'<div class="{cls}"></div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------
def empty_state(msg: str, hint: str = ""):
    hint_html = f'<div style="font-size:12px; margin-top:6px;">{html_mod.escape(hint)}</div>' if hint else ""
    st.markdown(
        f'<div style="text-align:center; padding:48px 20px; color:{T["text_muted"]};">'
        f'<div style="font-size:36px; opacity:.3; margin-bottom:12px;">{icon("search")}</div>'
        f'<div style="font-size:16px; font-weight:600; color:{T["text"]};">{html_mod.escape(msg)}</div>'
        f'{hint_html}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Error state
# ---------------------------------------------------------------------------
def error_state(message: str, exception: Exception | None = None):
    st.error(message)
    if exception:
        with st.expander("Technical details"):
            st.code(repr(exception), language="text")


# ---------------------------------------------------------------------------
# Lineage card flow
# ---------------------------------------------------------------------------
def render_lineage_flow(stages: list[dict] | None = None):
    """Render a 5-stage horizontal card flow. Each stage: {icon, title, detail}."""
    default_stages = [
        {"icon": "factory", "title": "Source System", "detail": "RAW tables"},
        {"icon": "graph", "title": "Ontology Layer", "detail": "Entities & relationships"},
        {"icon": "book", "title": "Metric Registry", "detail": "Governed definitions"},
        {"icon": "chart", "title": "Analytics View", "detail": "Gold-layer views"},
        {"icon": "sparkle", "title": "Dashboard", "detail": "Presentation"},
    ]
    stages = stages or default_stages
    parts = []
    for i, s in enumerate(stages):
        final = " ct-flow-final" if i == len(stages) - 1 else ""
        ic = icon(s.get("icon", ""))
        title = html_mod.escape(s.get("title", ""))
        detail = html_mod.escape(s.get("detail", ""))
        parts.append(
            f'<div class="ct-flow-step{final}" title="{title}: {detail}">'
            f'<div class="ct-fs-icon">{ic}</div>'
            f'<div class="ct-fs-title">{title}</div>'
            f'<div class="ct-fs-desc">{detail}</div>'
            f'</div>'
        )
        if i < len(stages) - 1:
            parts.append('<div class="ct-flow-arrow">&rarr;</div>')
    st.markdown(
        f'<ol class="ct-flow" aria-label="Data lineage" style="list-style:none; padding:0; margin:0;">{"".join(parts)}</ol>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
def footer():
    st.markdown(
        '<div class="ct-footer">'
        'ChainTruth &middot; Supply Chain Governance Platform'
        '</div>',
        unsafe_allow_html=True,
    )
