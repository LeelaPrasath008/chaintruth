"""Shared UI components. Every page uses these instead of raw HTML."""

from __future__ import annotations
import streamlit as st
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


# ---------------------------------------------------------------------------
# Page header  (replaces hero banner)
# ---------------------------------------------------------------------------
def page_header(title: str, subtitle: str = "", freshness: str = "Governed data"):
    right = f'<span>{freshness}</span>'
    sub_html = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f'<div class="ct-page-header">'
        f'<div class="ct-ph-left"><h1>{title}</h1>{sub_html}</div>'
        f'<div class="ct-ph-right">{right}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Section header
# ---------------------------------------------------------------------------
def section(title: str):
    st.markdown(f'<div class="ct-section">{title}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# KPI card (single card HTML)
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
        icon_html = f'<span style="color:{T["text_muted"]}">{_ICONS[icon_name]}</span>'

    cap = f'<div class="ct-kpi-caption">{caption}</div>' if caption else ""

    return (
        f'<div class="ct-kpi">'
        f'<div class="ct-kpi-top">'
        f'<span class="ct-kpi-label" title="{label}">{label}</span>'
        f'{chip}{icon_html}'
        f'</div>'
        f'<div class="ct-kpi-value">{value}</div>'
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
    return f'<span class="ct-chip ct-chip-{kind}">{svg_html} {text}</span>'


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
        f'<strong>{title}</strong>'
        f'{body}'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------
def empty_state(msg: str):
    st.markdown(
        f'<div style="text-align:center; padding:40px 20px; color:{T["text_muted"]};">'
        f'{icon("search")}<br>{msg}</div>',
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
