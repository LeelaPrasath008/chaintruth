import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.db import run_query as run, safe_float
from utils.theme import T
from utils.components import page_header, kpi_card, kpi_grid, section, insight, footer, enhanced_table, render_lineage_flow
from utils.charts import render_chart, SERIES
from utils.tour import render_tour_banner
from utils.data_cleaning import safe_multiselect_options

page_header("Conflict Center", "Quantifying how competing OTIF definitions produce different verdicts from identical data")
render_tour_banner()

# -- sidebar filters -----------------------------------------------------------
st.sidebar.markdown("**Filters**")
regions = run("SELECT DISTINCT SUPPLIER_REGION AS R FROM CHAINTRUTH_DB.ANALYTICS.CHAINTRUTH_OTIF ORDER BY R")
segments = run("SELECT DISTINCT CUSTOMER_SEGMENT AS S FROM CHAINTRUTH_DB.ANALYTICS.CHAINTRUTH_OTIF ORDER BY S")
sel_regions = st.sidebar.multiselect("Supplier Region", safe_multiselect_options(regions["R"]))
sel_segments = st.sidebar.multiselect("Customer Segment", safe_multiselect_options(segments["S"]))

clauses = []
if sel_regions:
    clauses.append("SUPPLIER_REGION IN (" + ",".join(f"'{r}'" for r in sel_regions) + ")")
if sel_segments:
    clauses.append("CUSTOMER_SEGMENT IN (" + ",".join(f"'{s}'" for s in sel_segments) + ")")
where = "WHERE " + " AND ".join(clauses) if clauses else ""

# =============================================================================
# HEADLINE KPIs
# =============================================================================
headline = run(
    f"SELECT "
    f"  ROUND(SUM(CONFLICTED_SHIPMENTS)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS CONFLICT_RATE, "
    f"  SUM(CONFLICTED_SHIPMENTS) AS CONFLICTED, "
    f"  SUM(TOTAL_SHIPMENTS) AS TOTAL, "
    f"  ROUND(SUM(OTIF_RATE_CANONICAL*TOTAL_SHIPMENTS)/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS ERP_OTIF, "
    f"  ROUND(SUM(ON_TIME_RATE_LOGISTICS*TOTAL_SHIPMENTS)/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS LOG_OT, "
    f"  ROUND(SUM(ON_TIME_RATE_SUPPLIER*TOTAL_SHIPMENTS)/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS SUP_OT "
    f"FROM CHAINTRUTH_DB.ANALYTICS.CHAINTRUTH_OTIF {where}"
).iloc[0]

cr = safe_float(headline['CONFLICT_RATE'])
conflicted = int(safe_float(headline['CONFLICTED']))
total = int(safe_float(headline['TOTAL']))
erp_ot = safe_float(headline['ERP_OTIF'])
log_ot = safe_float(headline['LOG_OT'])
sup_ot = safe_float(headline['SUP_OT'])
spread = sup_ot - erp_ot

section("Conflict Severity")
kpi_grid([
    kpi_card("Conflict Rate", f"{cr:.1f}%",
             status="critical" if cr > 50 else "warning", icon_name="alert"),
    kpi_card("Conflicted Shipments", f"{conflicted:,}",
             status="critical" if cr > 50 else "warning", icon_name="chart"),
    kpi_card("ERP OTIF (Canonical)", f"{erp_ot:.1f}%",
             status="critical" if erp_ot < 30 else "warning", icon_name="chart"),
    kpi_card("Logistics On-Time", f"{log_ot:.1f}%",
             status="warning", icon_name="chart"),
    kpi_card("Supplier On-Time", f"{sup_ot:.1f}%",
             status="healthy" if sup_ot > 50 else "warning", icon_name="chart"),
])

st.markdown(
    insight(
        f"Definition Spread: {spread:.1f} percentage points",
        f"The same shipments score <b>{sup_ot:.1f}%</b> on-time by the supplier's "
        f"measure but only <b>{erp_ot:.1f}%</b> by the ERP standard. This {spread:.0f}pp gap creates "
        f"fundamentally different narratives about supply chain performance.",
        "danger",
    ),
    unsafe_allow_html=True,
)

# =============================================================================
# TREND CHARTS
# =============================================================================
section("Conflict Trends")
trend = run(
    f"SELECT ORDER_MONTH, "
    f"  ROUND(SUM(CONFLICTED_SHIPMENTS)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS CONFLICT_RATE, "
    f"  ROUND(SUM(ON_TIME_RATE_ERP*TOTAL_SHIPMENTS)/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS ERP_OT, "
    f"  ROUND(SUM(ON_TIME_RATE_LOGISTICS*TOTAL_SHIPMENTS)/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS LOG_OT, "
    f"  ROUND(SUM(ON_TIME_RATE_SUPPLIER*TOTAL_SHIPMENTS)/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS SUP_OT "
    f"FROM CHAINTRUTH_DB.ANALYTICS.CHAINTRUTH_OTIF {where} "
    f"GROUP BY ORDER_MONTH ORDER BY ORDER_MONTH"
)

col_l, col_r = st.columns(2)
with col_l:
    fig_conflict = px.area(trend, x="ORDER_MONTH", y="CONFLICT_RATE",
                           labels={"ORDER_MONTH": "Month", "CONFLICT_RATE": "Conflict Rate (%)"})
    fig_conflict.update_traces(line_color=SERIES[4], fillcolor="rgba(209,73,91,0.12)")
    fig_conflict.update_layout(yaxis_range=[0, 100])
    render_chart(fig_conflict, "area", "Conflict Rate Over Time")

with col_r:
    otif_long = trend.melt(id_vars="ORDER_MONTH", value_vars=["ERP_OT", "LOG_OT", "SUP_OT"],
                           var_name="Definition", value_name="On-Time Rate (%)")
    otif_long["Definition"] = otif_long["Definition"].map({"ERP_OT": "ERP", "LOG_OT": "Logistics", "SUP_OT": "Supplier"})
    fig_otif = px.line(otif_long, x="ORDER_MONTH", y="On-Time Rate (%)", color="Definition",
                       markers=True,
                       labels={"ORDER_MONTH": "Month"},
                       color_discrete_map={"ERP": SERIES[4], "Logistics": SERIES[2], "Supplier": SERIES[1]})
    fig_otif.update_layout(yaxis_range=[0, 100])
    render_chart(fig_otif, "line", "On-Time Rate by Definition Over Time")

# =============================================================================
# WHERE CONFLICTS ARE WORST
# =============================================================================
section("Where Conflicts Are Worst")

by_supplier = run(
    f"SELECT SUPPLIER_ID, SUPPLIER_NAME, SUPPLIER_REGION, RELIABILITY_SCORE, "
    f"  SUM(TOTAL_SHIPMENTS) AS SHIPMENTS, "
    f"  SUM(CONFLICTED_SHIPMENTS) AS CONFLICTED, "
    f"  ROUND(SUM(CONFLICTED_SHIPMENTS)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS CONFLICT_RATE, "
    f"  ROUND(SUM(ON_TIME_RATE_ERP*TOTAL_SHIPMENTS)/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS ERP_OT, "
    f"  ROUND(SUM(ON_TIME_RATE_SUPPLIER*TOTAL_SHIPMENTS)/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS SUP_OT "
    f"FROM CHAINTRUTH_DB.ANALYTICS.CHAINTRUTH_OTIF {where} "
    f"GROUP BY SUPPLIER_ID, SUPPLIER_NAME, SUPPLIER_REGION, RELIABILITY_SCORE "
    f"ORDER BY CONFLICT_RATE DESC"
)
by_supplier["SPREAD"] = by_supplier["SUP_OT"] - by_supplier["ERP_OT"]

by_region = run(
    f"SELECT SUPPLIER_REGION, "
    f"  SUM(TOTAL_SHIPMENTS) AS SHIPMENTS, "
    f"  SUM(CONFLICTED_SHIPMENTS) AS CONFLICTED, "
    f"  ROUND(SUM(CONFLICTED_SHIPMENTS)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS CONFLICT_RATE, "
    f"  ROUND(SUM(ON_TIME_RATE_ERP*TOTAL_SHIPMENTS)/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS ERP_OT, "
    f"  ROUND(SUM(ON_TIME_RATE_SUPPLIER*TOTAL_SHIPMENTS)/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS SUP_OT "
    f"FROM CHAINTRUTH_DB.ANALYTICS.CHAINTRUTH_OTIF {where} "
    f"GROUP BY SUPPLIER_REGION ORDER BY CONFLICT_RATE DESC"
)
by_region["SPREAD"] = by_region["SUP_OT"] - by_region["ERP_OT"]

col_l2, col_r2 = st.columns(2)
with col_l2:
    top_n = by_supplier.head(10)
    fig_sup = px.bar(top_n, y="SUPPLIER_NAME", x="CONFLICT_RATE", orientation="h",
                     labels={"CONFLICT_RATE": "Conflict Rate (%)", "SUPPLIER_NAME": ""},
                     text=top_n["CONFLICT_RATE"].apply(lambda v: f"{v:.0f}%"))
    fig_sup.update_traces(marker_color=SERIES[4], textfont_color=T["text_muted"], textposition="outside")
    fig_sup.update_layout(yaxis=dict(autorange="reversed"), xaxis_range=[0, 100])
    render_chart(fig_sup, "bar", "Top 10 Suppliers by Conflict Rate", legend="none")

with col_r2:
    fig_reg = go.Figure()
    fig_reg.add_trace(go.Bar(y=by_region["SUPPLIER_REGION"], x=by_region["ERP_OT"],
                             name="ERP On-Time", orientation="h", marker_color=SERIES[4]))
    fig_reg.add_trace(go.Bar(y=by_region["SUPPLIER_REGION"], x=by_region["SUP_OT"],
                             name="Supplier On-Time", orientation="h", marker_color=SERIES[1]))
    fig_reg.update_layout(barmode="group",
                          xaxis_title="On-Time Rate (%)", yaxis=dict(autorange="reversed"),
                          xaxis_range=[0, 100],
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    render_chart(fig_reg, "bar", "ERP vs Supplier On-Time Rate by Region")

# =============================================================================
# SPREAD ANALYSIS
# =============================================================================
section("Definition Spread Analysis")

col_l3, col_r3 = st.columns(2)
with col_l3:
    fig_scatter = px.scatter(by_supplier, x="RELIABILITY_SCORE", y="SPREAD",
                             size="SHIPMENTS", color="SUPPLIER_REGION",
                             hover_name="SUPPLIER_NAME",
                             labels={"RELIABILITY_SCORE": "Reliability Score",
                                     "SPREAD": "Spread (Supplier OT - ERP OT, pp)",
                                     "SUPPLIER_REGION": "Region"})
    fig_scatter.add_hline(y=0, line_dash="dash", line_color=T["text_muted"], annotation_text="No spread",
                          annotation_font_color=T["text_muted"])
    render_chart(fig_scatter, "scatter", "Reliability Score vs Definition Spread")

with col_r3:
    fig_box = px.box(by_supplier, x="SUPPLIER_REGION", y="SPREAD", color="SUPPLIER_REGION",
                     labels={"SUPPLIER_REGION": "Region", "SPREAD": "Spread (pp)"})
    fig_box.update_layout(showlegend=False)
    render_chart(fig_box, "box", "Spread Distribution by Region", legend="none")

# =============================================================================
# SUPPLIER DETAIL
# =============================================================================
section("Supplier Detail")
display = by_supplier.rename(columns={
    "SUPPLIER_ID": "ID", "SUPPLIER_NAME": "Supplier", "SUPPLIER_REGION": "Region",
    "RELIABILITY_SCORE": "Reliability", "SHIPMENTS": "Shipments", "CONFLICTED": "Conflicted",
    "CONFLICT_RATE": "Conflict %", "ERP_OT": "ERP OT %", "SUP_OT": "Supplier OT %", "SPREAD": "Spread (pp)",
})
enhanced_table(
    display[["ID", "Supplier", "Region", "Reliability", "Shipments",
             "Conflicted", "Conflict %", "ERP OT %", "Supplier OT %", "Spread (pp)"]],
    key="conflict_suppliers",
)

# =============================================================================
# DATA LINEAGE
# =============================================================================
section("Data Lineage")
render_lineage_flow([
    {"icon": "factory", "title": "Source System", "detail": "ORDERS + SHIPMENTS"},
    {"icon": "graph", "title": "Ontology Layer", "detail": "ENTITY_TYPE + RELATIONSHIP_TYPE"},
    {"icon": "book", "title": "Metric Registry", "detail": "3 OTIF definitions"},
    {"icon": "chart", "title": "Analytics View", "detail": "CHAINTRUTH_OTIF"},
    {"icon": "sparkle", "title": "Conflict Center", "detail": "This page"},
])

footer()
