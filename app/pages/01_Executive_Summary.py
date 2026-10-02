import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils.db import run_query as run, safe_float
from utils.theme import inject_css, hero, kpi_card, insight, section, DANGER, WARNING, SUCCESS, PRIMARY

st.set_page_config(page_title="Executive Summary", layout="wide", page_icon="🔗")
inject_css()

hero("EXECUTIVE SUMMARY", "One-minute overview for leadership — problem, status, action")

# -- pull all key metrics in one pass ------------------------------------------
erp_otif = safe_float(run(
    "SELECT ROUND(SUM(OTIF_COUNT)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
    "FROM CHAINTRUTH_DB.ANALYTICS.ERP_OTIF"
)["V"].iloc[0])

sup_otif = safe_float(run(
    "SELECT ROUND(SUM(OTIF_COUNT)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
    "FROM CHAINTRUTH_DB.ANALYTICS.SUPPLIER_OTIF"
)["V"].iloc[0])

conflict_rate = safe_float(run(
    "SELECT ROUND(SUM(CONFLICTED_SHIPMENTS)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
    "FROM CHAINTRUTH_DB.ANALYTICS.CHAINTRUTH_OTIF"
)["V"].iloc[0])

rev_data = run(
    "SELECT SUM(REVENUE_AT_RISK) AS RAR, SUM(TOTAL_ORDER_VALUE) AS TOV "
    "FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS"
).iloc[0]
rev_risk = safe_float(rev_data["RAR"])
total_rev = safe_float(rev_data["TOV"])
risk_pct = rev_risk * 100 / total_rev if total_rev else 0

fill_rate = safe_float(run(
    "SELECT ROUND(SUM(TOTAL_QTY_SHIPPED)*100.0/NULLIF(SUM(TOTAL_QTY_ORDERED),0),1) AS V "
    "FROM CHAINTRUTH_DB.ANALYTICS.FILL_RATE_ANALYTICS"
)["V"].iloc[0])

lead_time = safe_float(run(
    "SELECT ROUND(SUM(AVG_LEAD_TIME_DAYS*TOTAL_SHIPMENTS)/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
    "FROM CHAINTRUTH_DB.ANALYTICS.LEAD_TIME_ANALYTICS"
)["V"].iloc[0])

num_suppliers = int(safe_float(run(
    "SELECT COUNT(*) AS V FROM CHAINTRUTH_DB.RAW.SUPPLIERS"
)["V"].iloc[0]))

num_orders = int(safe_float(run(
    "SELECT COUNT(*) AS V FROM CHAINTRUTH_DB.RAW.ORDERS"
)["V"].iloc[0]))

# =============================================================================
# 1 — THE PROBLEM
# =============================================================================
section("The Problem")
st.markdown(
    "Three teams — **Finance (ERP)**, **Logistics**, and **Procurement** — each measure "
    "On-Time In-Full (OTIF) using a different reference date from the same shipment data. "
    "Leadership receives **three conflicting performance reports** and cannot determine "
    "which number to trust."
)

spread = sup_otif - erp_otif

log_otif = safe_float(run(
    "SELECT ROUND(SUM(OTIF_COUNT)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
    "FROM CHAINTRUTH_DB.ANALYTICS.LOGISTICS_OTIF"
)["V"].iloc[0])

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(kpi_card("📋", f"{erp_otif:.1f}%", "Finance says OTIF is", "critical" if erp_otif < 30 else "warning"), unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card("🚛", f"{log_otif:.1f}%", "Logistics says OTIF is", "warning"), unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card("🏭", f"{sup_otif:.1f}%", "Procurement says OTIF is", "healthy" if sup_otif > 50 else "warning"), unsafe_allow_html=True)

st.markdown(f"> **{spread:.1f} percentage-point spread** between the highest and lowest OTIF — from the same data.")

# =============================================================================
# 2 — GOVERNANCE STATUS
# =============================================================================
section("Governance Status")

metrics_count = int(safe_float(run(
    "SELECT COUNT(*) AS V FROM CHAINTRUTH_DB.ONTOLOGY.METRIC_REGISTRY"
)["V"].iloc[0]))
canonical_count = int(safe_float(run(
    "SELECT COUNT(*) AS V FROM CHAINTRUTH_DB.ONTOLOGY.METRIC_REGISTRY WHERE IS_CANONICAL = TRUE"
)["V"].iloc[0]))
entity_count = int(safe_float(run(
    "SELECT COUNT(*) AS V FROM CHAINTRUTH_DB.ONTOLOGY.ENTITY_TYPE"
)["V"].iloc[0]))
rel_count = int(safe_float(run(
    "SELECT COUNT(*) AS V FROM CHAINTRUTH_DB.ONTOLOGY.RELATIONSHIP_TYPE"
)["V"].iloc[0]))

g1, g2, g3, g4 = st.columns(4)
with g1:
    st.markdown(kpi_card("📐", str(metrics_count), "Governed Metrics", "healthy"), unsafe_allow_html=True)
with g2:
    st.markdown(kpi_card("✅", str(canonical_count), "Canonical Definitions", "healthy"), unsafe_allow_html=True)
with g3:
    st.markdown(kpi_card("🔷", str(entity_count), "Entity Types", "healthy"), unsafe_allow_html=True)
with g4:
    st.markdown(kpi_card("🔗", str(rel_count), "Relationships", "healthy"), unsafe_allow_html=True)

# =============================================================================
# 3 — RISK STATUS
# =============================================================================
section("Risk Status")

r1, r2, r3, r4 = st.columns(4)
with r1:
    st.markdown(kpi_card("💰", f"${rev_risk/1e6:.1f}M", "Revenue At Risk", "critical" if risk_pct > 70 else "warning"), unsafe_allow_html=True)
with r2:
    st.markdown(kpi_card("⚡", f"{conflict_rate:.1f}%", "Conflict Rate", "critical" if conflict_rate > 50 else "warning"), unsafe_allow_html=True)
with r3:
    st.markdown(kpi_card("📦", f"{fill_rate:.1f}%", "Fill Rate", "healthy" if fill_rate > 95 else "warning"), unsafe_allow_html=True)
with r4:
    st.markdown(kpi_card("🕐", f"{lead_time:.1f}d", "Avg Lead Time", "healthy" if lead_time < 15 else "warning"), unsafe_allow_html=True)

# =============================================================================
# 4 — TOP INSIGHTS
# =============================================================================
section("Key Insights")

insights_html = ""
insights_html += insight(
    "Definition Conflict is the #1 Governance Risk",
    f"{conflict_rate:.0f}% of shipments get a different on-time verdict depending on which team you ask. "
    f"This creates confusion in executive reporting and undermines trust in supply chain KPIs.",
    "danger",
)

worst_sup = run(
    "SELECT SUPPLIER_NAME, SUM(REVENUE_AT_RISK) AS RAR "
    "FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS "
    "GROUP BY SUPPLIER_NAME ORDER BY RAR DESC LIMIT 1"
).iloc[0]
insights_html += insight(
    f"Highest Exposure: {worst_sup['SUPPLIER_NAME']}",
    f"This supplier contributes <b>${safe_float(worst_sup['RAR'])/1e6:.2f}M</b> in revenue at risk — "
    f"driven primarily by late deliveries against the ERP promised date.",
    "warning",
)

insights_html += insight(
    "Fill Rate is Not the Problem",
    f"At {fill_rate:.1f}%, inventory fulfillment is healthy. "
    f"The risk is in <b>timing</b> (late delivery), not <b>stock</b> (quantity shortfalls).",
    "success",
)

st.markdown(insights_html, unsafe_allow_html=True)

# =============================================================================
# 5 — RECOMMENDATIONS
# =============================================================================
section("Recommendations")

st.markdown("""
| Priority | Action | Expected Impact |
|:--------:|--------|-----------------|
| 🔴 | **Adopt ERP OTIF as canonical** — align all teams to one definition | Eliminates conflicting reports |
| 🔴 | **Investigate top-5 at-risk suppliers** — review commitment dates and carrier selection | Reduce revenue exposure by 20-30% |
| 🟡 | **Tighten supplier commitment dates** — close the gap between supplier and ERP definitions | Reduce OTIF spread and conflict rate |
| 🟡 | **Add governance SLAs** — set thresholds for conflict rate and risk percentage | Automated alerting when governance degrades |
| 🟢 | **Extend ontology** — add cost, quality, and sustainability metrics | Broader governed decision-making |
""")

# -- footer
st.markdown("---")
st.markdown(
    '<div style="text-align:center; color:#94A3B8; font-size:0.8rem;">'
    'ChainTruth Executive Summary &mdash; Auto-generated from governed analytics views'
    '</div>',
    unsafe_allow_html=True,
)
