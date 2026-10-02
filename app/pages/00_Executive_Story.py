import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils.db import run_query as run, safe_float
from utils.theme import T
from utils.components import page_header, kpi_card, kpi_grid, section, insight, insight_panel, footer, status_chip
from utils.charts import render_chart, SERIES

page_header("Executive Story", "The complete ChainTruth narrative — from problem to business value")

# -- sidebar nav ---------------------------------------------------------------
st.sidebar.markdown("**Story Navigation**")
st.sidebar.markdown(
    "1. The Problem\n"
    "2. The Conflict\n"
    "3. Root Cause\n"
    "4. The Solution\n"
    "5. Ontology Governance\n"
    "6. Business Impact\n"
    "7. AI Copilot\n"
    "8. Executive Outcome"
)

# ==============================================================================
# LOAD ALL DATA (reusing existing queries)
# ==============================================================================
erp_otif = safe_float(run(
    "SELECT ROUND(SUM(OTIF_COUNT)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
    "FROM CHAINTRUTH_DB.ANALYTICS.ERP_OTIF"
)["V"].iloc[0])

log_otif = safe_float(run(
    "SELECT ROUND(SUM(OTIF_COUNT)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
    "FROM CHAINTRUTH_DB.ANALYTICS.LOGISTICS_OTIF"
)["V"].iloc[0])

sup_otif = safe_float(run(
    "SELECT ROUND(SUM(OTIF_COUNT)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
    "FROM CHAINTRUTH_DB.ANALYTICS.SUPPLIER_OTIF"
)["V"].iloc[0])

conflict_data = run(
    "SELECT SUM(CONFLICTED_SHIPMENTS) AS CONFLICTED, "
    "  SUM(TOTAL_SHIPMENTS) AS TOTAL, "
    "  ROUND(SUM(CONFLICTED_SHIPMENTS)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS CONFLICT_RATE "
    "FROM CHAINTRUTH_DB.ANALYTICS.CHAINTRUTH_OTIF"
).iloc[0]
conflict_rate = safe_float(conflict_data["CONFLICT_RATE"])
conflicted = int(safe_float(conflict_data["CONFLICTED"]))
total_shipments = int(safe_float(conflict_data["TOTAL"]))

rev_data = run(
    "SELECT SUM(REVENUE_AT_RISK) AS RAR, SUM(TOTAL_ORDER_VALUE) AS TOV "
    "FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS"
).iloc[0]
rev_risk = safe_float(rev_data["RAR"])
total_rev = safe_float(rev_data["TOV"])
risk_pct = rev_risk * 100 / total_rev if total_rev else 0
spread = sup_otif - erp_otif

fill_rate = safe_float(run(
    "SELECT ROUND(SUM(TOTAL_QTY_SHIPPED)*100.0/NULLIF(SUM(TOTAL_QTY_ORDERED),0),1) AS V "
    "FROM CHAINTRUTH_DB.ANALYTICS.FILL_RATE_ANALYTICS"
)["V"].iloc[0])

lead_time = safe_float(run(
    "SELECT ROUND(SUM(AVG_LEAD_TIME_DAYS*TOTAL_SHIPMENTS)/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
    "FROM CHAINTRUTH_DB.ANALYTICS.LEAD_TIME_ANALYTICS"
)["V"].iloc[0])

top_risk = run(
    "SELECT SUPPLIER_NAME, SUPPLIER_REGION, "
    "  SUM(REVENUE_AT_RISK) AS RAR, "
    "  SUM(TOTAL_ORDER_VALUE) AS TOV, "
    "  ROUND(SUM(REVENUE_AT_RISK)*100.0/NULLIF(SUM(TOTAL_ORDER_VALUE),0),1) AS RISK_PCT "
    "FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS "
    "GROUP BY SUPPLIER_NAME, SUPPLIER_REGION ORDER BY RAR DESC LIMIT 5"
)

metrics_df = run(
    "SELECT METRIC_NAME, METRIC_VARIANT, OWNER_TEAM, IS_CANONICAL, UNIT, DIRECTION "
    "FROM CHAINTRUTH_DB.ONTOLOGY.METRIC_REGISTRY ORDER BY METRIC_NAME, IS_CANONICAL DESC"
)
metrics_df["IS_CANONICAL"] = metrics_df["IS_CANONICAL"].apply(
    lambda v: bool(v) if isinstance(v, bool) else str(v).lower() == "true"
)
metrics_count = len(metrics_df)
canonical_count = int(metrics_df["IS_CANONICAL"].sum())
entities_count = int(safe_float(run(
    "SELECT COUNT(*) AS V FROM CHAINTRUTH_DB.ONTOLOGY.ENTITY_TYPE"
)["V"].iloc[0]))
rels_count = int(safe_float(run(
    "SELECT COUNT(*) AS V FROM CHAINTRUTH_DB.ONTOLOGY.RELATIONSHIP_TYPE"
)["V"].iloc[0]))

# ==============================================================================
# SECTION 1 — THE PROBLEM
# ==============================================================================
section("The Problem")

st.markdown(
    '<div class="ct-story">'
    '<h3>Three Teams Report Different OTIF Numbers</h3>'
    '<p><b>Finance</b> measures OTIF against the ERP promised delivery date — the strictest standard, '
    'set at order time with tight buffers.</p>'
    '<p><b>Logistics</b> measures against the carrier ETA — set at ship-time, often optimistic, '
    'reflecting what the carrier promised.</p>'
    '<p><b>Procurement</b> measures against the supplier commitment date — the most padded deadline, '
    'measuring dispatch rather than delivery.</p>'
    '<p>The result: leadership receives <b>three conflicting reports</b> from the same shipment data '
    'and cannot determine which number to trust.</p>'
    '</div>',
    unsafe_allow_html=True,
)

kpi_grid([
    kpi_card("Finance (ERP) OTIF", f"{erp_otif:.1f}%",
             status="critical" if erp_otif < 30 else "warning", icon_name="chart"),
    kpi_card("Logistics OTIF", f"{log_otif:.1f}%",
             status="warning", icon_name="chart"),
    kpi_card("Supplier OTIF", f"{sup_otif:.1f}%",
             status="healthy" if sup_otif > 50 else "warning", icon_name="chart"),
])

st.markdown(
    insight(
        f"The Spread: {spread:.1f} Percentage Points",
        f"The same shipments score <b>{sup_otif:.1f}%</b> on-time by the supplier's measure "
        f"but only <b>{erp_otif:.1f}%</b> by the ERP standard. A {spread:.0f}pp gap means two teams see "
        f"completely different realities.",
        "danger",
    ),
    unsafe_allow_html=True,
)

# ==============================================================================
# SECTION 2 — THE CONFLICT
# ==============================================================================
section("The Conflict")

sev = "critical" if conflict_rate > 50 else ("warning" if conflict_rate > 25 else "healthy")
kpi_grid([
    kpi_card("Conflict Rate", f"{conflict_rate:.1f}%", status=sev, icon_name="alert"),
    kpi_card("Total Shipments", f"{total_shipments:,}", status="neutral", icon_name="box"),
    kpi_card("Conflicted", f"{conflicted:,}", status="critical", icon_name="alert"),
])

st.markdown(
    insight(
        "Severity: CRITICAL",
        f"<b>{conflicted:,} of {total_shipments:,} shipments</b> ({conflict_rate:.1f}%) "
        f"produce conflicting OTIF outcomes across systems. When the conflict rate exceeds 50%, "
        f"executive reports are unreliable — teams are making decisions based on numbers that contradict "
        f"each other.",
        "danger",
    ),
    unsafe_allow_html=True,
)

fig_bar = go.Figure()
for name, val, color in [("ERP (Canonical)", erp_otif, SERIES[4]), ("Logistics", log_otif, SERIES[2]), ("Supplier", sup_otif, SERIES[1])]:
    fig_bar.add_trace(go.Bar(
        x=[name], y=[val], marker_color=color, name=name,
        text=[f"<b>{val:.1f}%</b>"], textposition="outside",
        textfont=dict(color=color, size=16),
    ))
fig_bar.update_layout(
    showlegend=False, yaxis_range=[0, 100], yaxis_title="OTIF Rate (%)",
)
render_chart(fig_bar, "bar", "Same data, three answers", legend="none")

# ==============================================================================
# SECTION 3 — ROOT CAUSE
# ==============================================================================
section("The Root Cause")

st.markdown(
    '<div class="ct-story">'
    '<h3>Each Team Uses a Different Date as "On-Time"</h3>'
    '<p>The root cause is not bad data — it is <b>unresolved semantic ambiguity</b>. '
    'Three valid but <b>ungoverned</b> definitions produce three different answers.</p>'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="ct-flow">'
    '<div class="ct-flow-step">'
    '  <div class="ct-fs-title">ERP Definition</div>'
    '  <div class="ct-fs-desc">Delivery vs. promised date</div>'
    '</div>'
    '<span class="ct-flow-arrow">&rarr;</span>'
    '<div class="ct-flow-step">'
    '  <div class="ct-fs-title">Logistics Definition</div>'
    '  <div class="ct-fs-desc">Delivery vs. carrier ETA</div>'
    '</div>'
    '<span class="ct-flow-arrow">&rarr;</span>'
    '<div class="ct-flow-step">'
    '  <div class="ct-fs-title">Supplier Definition</div>'
    '  <div class="ct-fs-desc">Ship date vs. commitment</div>'
    '</div>'
    '<span class="ct-flow-arrow">&rarr;</span>'
    f'<div class="ct-flow-step" style="border-color:{T["danger"]};">'
    f'  <div class="ct-fs-title" style="color:{T["danger"]};">CONFLICT</div>'
    '  <div class="ct-fs-desc">Different verdicts, same data</div>'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

# ==============================================================================
# SECTION 4 — THE SOLUTION
# ==============================================================================
section("The ChainTruth Solution")

st.markdown(
    '<div class="ct-story">'
    '<h3>Ontology-Driven Governance on Snowflake</h3>'
    '<p>ChainTruth does not choose a winner. It <b>governs every definition</b> and makes differences '
    'transparent. Every metric is registered with an owner, SQL formula, lineage, and canonical flag.</p>'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="ct-flow">'
    '<div class="ct-flow-step">'
    '  <div class="ct-fs-title">Source Systems</div>'
    '  <div class="ct-fs-desc">ERP / Logistics / Procurement</div>'
    '</div>'
    '<span class="ct-flow-arrow">&rarr;</span>'
    '<div class="ct-flow-step">'
    '  <div class="ct-fs-title">Snowflake</div>'
    '  <div class="ct-fs-desc">Bronze (RAW) tables</div>'
    '</div>'
    '<span class="ct-flow-arrow">&rarr;</span>'
    f'<div class="ct-flow-step" style="border-color:{T["success"]};">'
    f'  <div class="ct-fs-title" style="color:{T["success"]};">Ontology Layer</div>'
    '  <div class="ct-fs-desc">Entities + Metric Registry</div>'
    '</div>'
    '<span class="ct-flow-arrow">&rarr;</span>'
    '<div class="ct-flow-step">'
    '  <div class="ct-fs-title">Analytics Views</div>'
    '  <div class="ct-fs-desc">Gold layer (7 views)</div>'
    '</div>'
    '<span class="ct-flow-arrow">&rarr;</span>'
    '<div class="ct-flow-step">'
    '  <div class="ct-fs-title">Dashboard</div>'
    '  <div class="ct-fs-desc">Executive + AI Copilot</div>'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

# ==============================================================================
# SECTION 5 — ONTOLOGY GOVERNANCE
# ==============================================================================
section("Ontology Governance")

kpi_grid([
    kpi_card("Governed Metrics", str(metrics_count), status="healthy", icon_name="chart"),
    kpi_card("Canonical", str(canonical_count), status="healthy", icon_name="check"),
    kpi_card("Entity Types", str(entities_count), status="healthy", icon_name="graph"),
    kpi_card("Relationships", str(rels_count), status="healthy", icon_name="link"),
])

st.markdown(
    insight(
        "Every metric has an owner, SQL definition, lineage, and governance status",
        "The ontology layer ensures no metric can enter executive reporting without "
        "explicit registration, canonical flagging, and owner accountability.",
        "success",
    ),
    unsafe_allow_html=True,
)

for _, row in metrics_df.iterrows():
    name = row["METRIC_NAME"]
    variant = row["METRIC_VARIANT"] if pd.notna(row["METRIC_VARIANT"]) else ""
    is_can = row["IS_CANONICAL"]
    badge_cls = "canonical" if is_can else "variant"
    badge_text = "CANONICAL" if is_can else "VARIANT"
    display_name = f"{name}" + (f" ({variant})" if variant else "")
    badge_bg = T["success_tint"] if is_can else "#E8F1FB"
    badge_color = T["success"] if is_can else T["primary"]
    st.markdown(
        f'<div class="ct-mrow">'
        f'<div class="ct-mrow-name">{display_name}</div>'
        f'<div class="ct-mrow-owner">{row["OWNER_TEAM"]}</div>'
        f'<span style="padding:2px 10px;border-radius:20px;font-size:0.68rem;font-weight:700;'
        f'background:{badge_bg};color:{badge_color};">{badge_text}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ==============================================================================
# SECTION 6 — BUSINESS IMPACT
# ==============================================================================
section("Business Impact")

kpi_grid([
    kpi_card("Revenue At Risk", f"${rev_risk/1e6:.1f}M",
             status="critical" if risk_pct > 70 else "warning", icon_name="dollar"),
    kpi_card("Risk Rate", f"{risk_pct:.1f}%", status="warning", icon_name="alert"),
    kpi_card("Fill Rate", f"{fill_rate:.1f}%",
             status="healthy" if fill_rate > 95 else "warning", icon_name="box"),
    kpi_card("Avg Lead Time", f"{lead_time:.1f}d", status="neutral", icon_name="clock"),
])

insights_html = ""
if not top_risk.empty:
    ws = top_risk.iloc[0]
    ws_pct = safe_float(ws["RAR"]) * 100 / rev_risk if rev_risk else 0
    insights_html += insight(
        f"Highest Exposure: {ws['SUPPLIER_NAME']}",
        f"<b>${safe_float(ws['RAR'])/1e6:.2f}M</b> at risk in {ws['SUPPLIER_REGION']} "
        f"({ws_pct:.0f}% of total portfolio exposure). Risk rate: <b>{safe_float(ws['RISK_PCT']):.1f}%</b>.",
        "danger",
    )
    if len(top_risk) >= 3:
        top3_total = float(top_risk.head(3)["RAR"].sum())
        top3_pct = top3_total * 100 / rev_risk if rev_risk else 0
        insights_html += insight(
            f"Top 3 suppliers account for {top3_pct:.0f}% of revenue at risk",
            f"Concentrated exposure of <b>${top3_total/1e6:.1f}M</b> across "
            f"{top_risk.iloc[0]['SUPPLIER_NAME']}, {top_risk.iloc[1]['SUPPLIER_NAME']}, "
            f"and {top_risk.iloc[2]['SUPPLIER_NAME']}.",
            "warning",
        )

insights_html += insight(
    "Fill rate is not the problem",
    f"At <b>{fill_rate:.1f}%</b>, inventory fulfillment is healthy. Risk is driven by "
    f"<b>timing</b> (late delivery), not <b>stock</b> (quantity shortfalls).",
    "success",
)
st.markdown(insights_html, unsafe_allow_html=True)

# ==============================================================================
# SECTION 7 — AI COPILOT
# ==============================================================================
section("AI Copilot")

st.markdown(
    '<div class="ct-story">'
    '<h3>Natural Language Access to Governed Data</h3>'
    '<p>ChainTruth includes a conversational AI copilot that answers supply chain questions '
    'grounded in the governed analytics layer — no SQL required.</p>'
    '</div>',
    unsafe_allow_html=True,
)

def mock_msg(avatar_type, text):
    avatar_label = "U" if avatar_type == "user" else "AI"
    return (
        f'<div class="ct-cpmsg">'
        f'<div class="ct-cp-avatar {avatar_type}">{avatar_label}</div>'
        f'<div class="ct-cp-text">{text}</div>'
        f'</div>'
    )

copilot_html = ""
copilot_html += mock_msg("user", "What is OTIF?")
copilot_html += mock_msg("ai",
    "<b>OTIF (On-Time In-Full)</b> is the gold-standard fulfillment KPI. "
    "A shipment is OTIF when both conditions are met: delivered by the agreed date, "
    "and the complete ordered quantity was shipped. "
    "ChainTruth tracks <b>three competing definitions</b> because different teams "
    "use different agreed dates."
)
copilot_html += mock_msg("user", "Why are OTIF definitions different?")
copilot_html += mock_msg("ai",
    f"<b>Three teams, three OTIF numbers, one dataset.</b><br/>"
    f"ERP (Canonical): <b>{erp_otif:.1f}%</b> — Finance, delivery vs. ERP promised date<br/>"
    f"Logistics: <b>{log_otif:.1f}%</b> — carrier ETA at ship-time<br/>"
    f"Supplier: <b>{sup_otif:.1f}%</b> — supplier commitment date<br/><br/>"
    f"Conflict rate: <b>{conflict_rate:.1f}%</b> of shipments get a different verdict."
)
copilot_html += mock_msg("user", "Which suppliers have highest revenue at risk?")
copilot_html += mock_msg("ai",
    f"#1 <b>{top_risk.iloc[0]['SUPPLIER_NAME']}</b> — ${safe_float(top_risk.iloc[0]['RAR'])/1e6:.2f}M "
    f"({top_risk.iloc[0]['SUPPLIER_REGION']})<br/>"
    f"#2 <b>{top_risk.iloc[1]['SUPPLIER_NAME']}</b> — ${safe_float(top_risk.iloc[1]['RAR'])/1e6:.2f}M<br/>"
    f"#3 <b>{top_risk.iloc[2]['SUPPLIER_NAME']}</b> — ${safe_float(top_risk.iloc[2]['RAR'])/1e6:.2f}M"
    if len(top_risk) >= 3 else "Loading supplier data..."
)
st.markdown(copilot_html, unsafe_allow_html=True)

# ==============================================================================
# SECTION 8 — EXECUTIVE OUTCOME
# ==============================================================================
section("Executive Outcome")

outcomes = [
    ("Single Source of Truth", "One canonical OTIF definition for executive reporting"),
    ("Governed Metrics", "Every metric registered with owner, SQL, and lineage"),
    ("Ontology-Driven Analytics", "Entities, relationships, and semantic governance"),
    ("Natural Language Access", "AI copilot grounded in governed analytics"),
    ("Revenue Risk Visibility", f"${rev_risk/1e6:.1f}M exposure identified and tracked"),
    ("Supply Chain Transparency", f"{conflict_rate:.0f}% conflict rate exposed and quantified"),
]

cols = st.columns(3)
for i, (title, desc) in enumerate(outcomes):
    with cols[i % 3]:
        st.markdown(
            f'<div class="ct-outcome">'
            f'<div class="ct-oc-title">{title}</div>'
            f'<div class="ct-oc-desc">{desc}</div>'
            f'</div><br/>',
            unsafe_allow_html=True,
        )

st.markdown(
    insight(
        "Key Takeaway",
        'ChainTruth doesn\'t pick a winner among conflicting definitions — it <b>exposes the conflict</b>, '
        '<b>governs each definition</b> through an ontology, and lets stakeholders make <b>informed decisions</b> '
        'based on one trusted, canonical number.',
        "success",
    ),
    unsafe_allow_html=True,
)

footer()
