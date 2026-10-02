"""Guided demo tour — walks users through key pages."""
import streamlit as st
from utils.theme import T

TOUR_STEPS = [
    {
        "page": "Dashboard",
        "title": "Step 1: Executive Dashboard",
        "body": (
            "The dashboard shows **six governance KPIs** at a glance: Canonical OTIF, "
            "Revenue at Risk, Conflict Rate, Active Suppliers, Fill Rate, and Lead Time. "
            "Use the sidebar filters to drill into specific suppliers, regions, or segments."
        ),
    },
    {
        "page": "Conflict Center",
        "title": "Step 2: OTIF Definition Conflicts",
        "body": (
            "This is ChainTruth's core innovation. Three teams (Finance, Logistics, Procurement) "
            "each define OTIF differently. The **conflict rate** shows how often these definitions "
            "disagree on the same shipment. Scroll down to see which suppliers and regions have "
            "the widest definition spread."
        ),
    },
    {
        "page": "Ask ChainTruth",
        "title": "Step 3: Conversational Analytics",
        "body": (
            "Ask questions in natural language. Try: *\"What is the current ERP OTIF?\"* or "
            "*\"Which suppliers have the highest revenue at risk?\"*. Every answer is grounded "
            "in governed analytics views, not raw tables."
        ),
    },
    {
        "page": "Ontology Explorer",
        "title": "Step 4: Business Ontology",
        "body": (
            "Browse the entity-relationship model that governs ChainTruth's data. "
            "Six entity types, seven relationships, and seven metric definitions — "
            "including the three competing OTIF variants with canonical flagging."
        ),
    },
    {
        "page": "Supplier Risk",
        "title": "Step 5: Revenue at Risk",
        "body": (
            "Drill into which suppliers expose the most revenue to late deliveries, "
            "short shipments, and overdue orders. The heatmap shows risk concentration "
            "by region and customer segment."
        ),
    },
    {
        "page": "Business Glossary",
        "title": "Step 6: Governed Metric Definitions",
        "body": (
            "Every metric has a governed definition: the SQL formula, the owning team, "
            "the canonical flag, and the source tables. This is the single source of truth "
            "that resolves ambiguity across teams."
        ),
    },
]


def render_tour_banner():
    """Show the current tour step as a banner if tour is active."""
    if "tour_step" not in st.session_state:
        return

    step_idx = st.session_state["tour_step"]
    if step_idx >= len(TOUR_STEPS):
        del st.session_state["tour_step"]
        return

    step = TOUR_STEPS[step_idx]
    progress = f"Step {step_idx + 1} of {len(TOUR_STEPS)}"

    st.markdown(
        f'<div style="background:linear-gradient(135deg, {T["primary"]}11, {T["accent"]}11); '
        f'border:1px solid {T["primary"]}33; border-radius:{T["radius"]}; '
        f'padding:16px 20px; margin-bottom:16px;">'
        f'<div style="display:flex; justify-content:space-between; align-items:center;">'
        f'<span style="font-size:11px; font-weight:600; color:{T["primary"]}; '
        f'letter-spacing:.5px;">{progress} &middot; GUIDED TOUR</span>'
        f'</div>'
        f'<div style="font-size:16px; font-weight:700; color:{T["text"]}; margin-top:6px;">'
        f'{step["title"]}</div>'
        f'<div style="font-size:13px; color:{T["text_muted"]}; margin-top:6px; line-height:1.6;">'
        f'{step["body"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if step_idx > 0:
            if st.button("Previous", key="tour_prev"):
                st.session_state["tour_step"] = step_idx - 1
                st.rerun()
    with col2:
        if st.button("End Tour", key="tour_end"):
            del st.session_state["tour_step"]
            st.rerun()
    with col3:
        if step_idx < len(TOUR_STEPS) - 1:
            if st.button("Next", key="tour_next", type="primary"):
                st.session_state["tour_step"] = step_idx + 1
                st.rerun()
        else:
            if st.button("Finish", key="tour_finish", type="primary"):
                del st.session_state["tour_step"]
                st.rerun()


def get_current_tour_page() -> str | None:
    """Return the page title the tour expects to be on."""
    if "tour_step" not in st.session_state:
        return None
    idx = st.session_state["tour_step"]
    if idx < len(TOUR_STEPS):
        return TOUR_STEPS[idx]["page"]
    return None
