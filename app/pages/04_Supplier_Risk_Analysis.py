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

page_header("Supplier Risk", "Identifying which suppliers put the most revenue at risk and why")
render_tour_banner()

# -- sidebar filters -----------------------------------------------------------
st.sidebar.markdown("**Filters**")
regions = run("SELECT DISTINCT SUPPLIER_REGION AS R FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS ORDER BY R")
segments = run("SELECT DISTINCT CUSTOMER_SEGMENT AS S FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS ORDER BY S")
plants = run("SELECT DISTINCT PLANT_ID AS P FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS ORDER BY P")

sel_regions = st.sidebar.multiselect("Supplier Region", safe_multiselect_options(regions["R"]))
sel_segments = st.sidebar.multiselect("Customer Segment", safe_multiselect_options(segments["S"]))
sel_plants = st.sidebar.multiselect("Plant", safe_multiselect_options(plants["P"]))

clauses = []
if sel_regions:
    clauses.append("SUPPLIER_REGION IN (" + ",".join(f"'{r}'" for r in sel_regions) + ")")
if sel_segments:
    clauses.append("CUSTOMER_SEGMENT IN (" + ",".join(f"'{s}'" for s in sel_segments) + ")")
if sel_plants:
    clauses.append("PLANT_ID IN (" + ",".join(f"'{p}'" for p in sel_plants) + ")")
where = "WHERE " + " AND ".join(clauses) if clauses else ""

# =============================================================================
# LOAD DATA (ALL SQL UNCHANGED)
# =============================================================================
suppliers = run(
    f"SELECT SUPPLIER_ID, SUPPLIER_NAME, SUPPLIER_COUNTRY, SUPPLIER_REGION, "
    f"  SUM(TOTAL_ORDERS) AS TOTAL_ORDERS, "
    f"  SUM(TOTAL_ORDER_VALUE) AS TOTAL_ORDER_VALUE, "
    f"  SUM(AT_RISK_ORDERS) AS AT_RISK_ORDERS, "
    f"  SUM(REVENUE_AT_RISK) AS REVENUE_AT_RISK, "
    f"  SUM(LATE_DELIVERY_ORDERS) AS LATE_ORDERS, "
    f"  SUM(LATE_DELIVERY_REVENUE) AS LATE_REVENUE, "
    f"  SUM(SHORT_SHIPPED_ORDERS) AS SHORT_ORDERS, "
    f"  SUM(SHORT_SHIPPED_REVENUE) AS SHORT_REVENUE, "
    f"  SUM(OVERDUE_OPEN_ORDERS) AS OVERDUE_ORDERS, "
    f"  SUM(OVERDUE_OPEN_REVENUE) AS OVERDUE_REVENUE "
    f"FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS {where} "
    f"GROUP BY SUPPLIER_ID, SUPPLIER_NAME, SUPPLIER_COUNTRY, SUPPLIER_REGION "
    f"ORDER BY REVENUE_AT_RISK DESC"
)

for col in ["TOTAL_ORDERS", "TOTAL_ORDER_VALUE", "AT_RISK_ORDERS", "REVENUE_AT_RISK",
            "LATE_ORDERS", "LATE_REVENUE", "SHORT_ORDERS", "SHORT_REVENUE",
            "OVERDUE_ORDERS", "OVERDUE_REVENUE"]:
    try:
        suppliers[col] = pd.to_numeric(suppliers[col], errors="coerce").fillna(0)
    except (ValueError, TypeError):
        suppliers[col] = suppliers[col].apply(lambda v: float(v) if v is not None else 0.0)

suppliers["RISK_PCT"] = (
    suppliers["REVENUE_AT_RISK"] * 100.0 / suppliers["TOTAL_ORDER_VALUE"].replace(0, pd.NA)
).round(1)
suppliers["SAFE_REVENUE"] = suppliers["TOTAL_ORDER_VALUE"] - suppliers["REVENUE_AT_RISK"]

monthly = run(
    f"SELECT ORDER_MONTH, "
    f"  SUM(REVENUE_AT_RISK) AS REVENUE_AT_RISK, "
    f"  SUM(LATE_DELIVERY_REVENUE) AS LATE_REVENUE, "
    f"  SUM(SHORT_SHIPPED_REVENUE) AS SHORT_REVENUE, "
    f"  SUM(OVERDUE_OPEN_REVENUE) AS OVERDUE_REVENUE, "
    f"  SUM(TOTAL_ORDER_VALUE) AS TOTAL_ORDER_VALUE "
    f"FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS {where} "
    f"GROUP BY ORDER_MONTH ORDER BY ORDER_MONTH"
)

by_region = run(
    f"SELECT SUPPLIER_REGION, "
    f"  SUM(TOTAL_ORDERS) AS TOTAL_ORDERS, "
    f"  SUM(REVENUE_AT_RISK) AS REVENUE_AT_RISK, "
    f"  SUM(TOTAL_ORDER_VALUE) AS TOTAL_ORDER_VALUE, "
    f"  SUM(LATE_DELIVERY_ORDERS) AS LATE_ORDERS, "
    f"  SUM(SHORT_SHIPPED_ORDERS) AS SHORT_ORDERS, "
    f"  SUM(OVERDUE_OPEN_ORDERS) AS OVERDUE_ORDERS "
    f"FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS {where} "
    f"GROUP BY SUPPLIER_REGION ORDER BY REVENUE_AT_RISK DESC"
)
for col in ["TOTAL_ORDERS", "REVENUE_AT_RISK", "TOTAL_ORDER_VALUE",
            "LATE_ORDERS", "SHORT_ORDERS", "OVERDUE_ORDERS"]:
    try:
        by_region[col] = pd.to_numeric(by_region[col], errors="coerce").fillna(0)
    except (ValueError, TypeError):
        by_region[col] = by_region[col].apply(lambda v: float(v) if v is not None else 0.0)
by_region["RISK_PCT"] = (
    by_region["REVENUE_AT_RISK"] * 100.0 / by_region["TOTAL_ORDER_VALUE"].replace(0, pd.NA)
).round(1)

# =============================================================================
# KPIs
# =============================================================================
totals = suppliers.agg({
    "TOTAL_ORDERS": "sum", "AT_RISK_ORDERS": "sum",
    "TOTAL_ORDER_VALUE": "sum", "REVENUE_AT_RISK": "sum",
    "LATE_ORDERS": "sum", "SHORT_ORDERS": "sum", "OVERDUE_ORDERS": "sum",
})
risk_pct = float(totals["REVENUE_AT_RISK"]) * 100.0 / float(totals["TOTAL_ORDER_VALUE"]) if totals["TOTAL_ORDER_VALUE"] else 0

section("Risk command center")
kpi_grid([
    kpi_card("Total Revenue", f"${float(totals['TOTAL_ORDER_VALUE'])/1e6:.1f}M", icon_name="dollar"),
    kpi_card("Revenue At Risk", f"${float(totals['REVENUE_AT_RISK'])/1e6:.1f}M",
             status="critical" if risk_pct > 70 else "warning", icon_name="alert"),
    kpi_card("Risk Rate", f"{risk_pct:.1f}%",
             status="critical" if risk_pct > 70 else "warning", icon_name="chart"),
    kpi_card("Late Delivery", f"{int(totals['LATE_ORDERS']):,}", status="critical", icon_name="clock"),
    kpi_card("Short Shipped", f"{int(totals['SHORT_ORDERS']):,}", status="warning", icon_name="box"),
    kpi_card("Overdue Open", f"{int(totals['OVERDUE_ORDERS']):,}", status="warning", icon_name="clock"),
])

# -- dynamic executive insights ------------------------------------------------
if not suppliers.empty:
    top1 = suppliers.iloc[0]
    top1_pct = float(top1["REVENUE_AT_RISK"]) * 100.0 / float(totals["REVENUE_AT_RISK"]) if totals["REVENUE_AT_RISK"] else 0
    st.markdown(
        insight(f"{top1['SUPPLIER_NAME']} contributes {top1_pct:.0f}% of total revenue at risk",
                f"With <b>${float(top1['REVENUE_AT_RISK'])/1e6:.2f}M</b> at risk in {top1['SUPPLIER_REGION']}, "
                f"this supplier is the single largest source of exposure. "
                f"Late deliveries: {int(top1['LATE_ORDERS'])}, Short shipped: {int(top1['SHORT_ORDERS'])}.",
                "danger"),
        unsafe_allow_html=True,
    )

# =============================================================================
# CHARTS
# =============================================================================
section("Revenue at risk trend")
col_l, col_r = st.columns(2)

with col_l:
    trend_long = monthly.melt(id_vars="ORDER_MONTH",
                              value_vars=["LATE_REVENUE", "SHORT_REVENUE", "OVERDUE_REVENUE"],
                              var_name="Risk Type", value_name="Revenue")
    trend_long["Risk Type"] = trend_long["Risk Type"].map({
        "LATE_REVENUE": "Late Delivery", "SHORT_REVENUE": "Short Shipped", "OVERDUE_REVENUE": "Overdue Open"})
    fig_trend = px.area(trend_long, x="ORDER_MONTH", y="Revenue", color="Risk Type",
                        labels={"ORDER_MONTH": "Month", "Revenue": "Revenue ($)"},
                        color_discrete_map={"Late Delivery": T["danger"], "Short Shipped": T["warning"], "Overdue Open": SERIES[5]})
    fig_trend.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    render_chart(fig_trend, "area", "Revenue At Risk by Type (Monthly)")

with col_r:
    rev_totals = pd.DataFrame({
        "Risk Type": ["Late Delivery", "Short Shipped", "Overdue Open"],
        "Revenue": [float(suppliers["LATE_REVENUE"].sum()), float(suppliers["SHORT_REVENUE"].sum()),
                    float(suppliers["OVERDUE_REVENUE"].sum())]})
    fig_donut = px.pie(rev_totals, names="Risk Type", values="Revenue",
                       color="Risk Type",
                       color_discrete_map={"Late Delivery": T["danger"], "Short Shipped": T["warning"], "Overdue Open": SERIES[5]},
                       hole=0.5)
    fig_donut.update_traces(textinfo="percent+label", textposition="outside", textfont_color=T["text_muted"])
    render_chart(fig_donut, "donut", "Risk Breakdown by Type")

section("Supplier and region breakdown")
col_l2, col_r2 = st.columns(2)

with col_l2:
    top10 = suppliers.head(10)
    fig_sup = go.Figure()
    fig_sup.add_trace(go.Bar(y=top10["SUPPLIER_NAME"], x=top10["REVENUE_AT_RISK"],
                             name="At Risk", orientation="h", marker_color=T["danger"],
                             text=top10["REVENUE_AT_RISK"].apply(lambda v: f"${float(v)/1e6:.2f}M"),
                             textposition="auto", textfont_color=T["text"]))
    fig_sup.add_trace(go.Bar(y=top10["SUPPLIER_NAME"], x=top10["SAFE_REVENUE"],
                             name="Safe", orientation="h", marker_color=T["success"]))
    fig_sup.update_layout(barmode="stack",
                          yaxis=dict(autorange="reversed"), xaxis_title="Revenue ($)",
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    render_chart(fig_sup, "bar", "Top 10 Suppliers: At Risk vs Safe Revenue")

with col_r2:
    fig_reg = go.Figure()
    fig_reg.add_trace(go.Bar(x=by_region["SUPPLIER_REGION"], y=by_region["LATE_ORDERS"],
                             name="Late", marker_color=T["danger"]))
    fig_reg.add_trace(go.Bar(x=by_region["SUPPLIER_REGION"], y=by_region["SHORT_ORDERS"],
                             name="Short", marker_color=T["warning"]))
    fig_reg.add_trace(go.Bar(x=by_region["SUPPLIER_REGION"], y=by_region["OVERDUE_ORDERS"],
                             name="Overdue", marker_color=SERIES[5]))
    fig_reg.update_layout(barmode="stack", yaxis_title="Orders",
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    render_chart(fig_reg, "bar", "Risk Type by Region")

# =============================================================================
# RISK CONCENTRATION
# =============================================================================
section("Risk concentration")
col_l3, col_r3 = st.columns(2)

with col_l3:
    fig_scatter = px.scatter(suppliers, x="TOTAL_ORDER_VALUE", y="RISK_PCT",
                             size="AT_RISK_ORDERS", color="SUPPLIER_REGION",
                             hover_name="SUPPLIER_NAME",
                             labels={"TOTAL_ORDER_VALUE": "Total Order Value ($)", "RISK_PCT": "Risk Rate (%)",
                                     "SUPPLIER_REGION": "Region"})
    fig_scatter.add_hline(y=float(risk_pct), line_dash="dash", line_color=T["text_muted"],
                          annotation_text=f"Avg {float(risk_pct):.0f}%", annotation_font_color=T["text_muted"])
    fig_scatter.update_layout(yaxis_range=[0, 105])
    render_chart(fig_scatter, "scatter", "Order Volume vs Risk Rate")

with col_r3:
    heatmap_sql = (
        f"SELECT SUPPLIER_REGION, CUSTOMER_SEGMENT, "
        f"  ROUND(SUM(REVENUE_AT_RISK)*100.0/NULLIF(SUM(TOTAL_ORDER_VALUE),0),1) AS RISK_PCT "
        f"FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS {where} "
        f"GROUP BY SUPPLIER_REGION, CUSTOMER_SEGMENT"
    )
    hm = run(heatmap_sql)
    if not hm.empty:
        hm_pivot = hm.pivot(index="SUPPLIER_REGION", columns="CUSTOMER_SEGMENT", values="RISK_PCT")
        fig_hm = px.imshow(hm_pivot, text_auto=".0f",
                           labels=dict(x="Customer Segment", y="Supplier Region", color="Risk %"),
                           color_continuous_scale=[[0, T["surface"]], [0.5, "#C77700"], [1, T["danger"]]],
                           aspect="auto")
        render_chart(fig_hm, "heatmap", "Risk Rate: Region x Segment (%)", legend="none")
    else:
        st.info("No data for heatmap with current filters.")

# =============================================================================
# SUPPLIER TABLE
# =============================================================================
section("Supplier detail")
display = suppliers.rename(columns={
    "SUPPLIER_ID": "ID", "SUPPLIER_NAME": "Supplier", "SUPPLIER_COUNTRY": "Country",
    "SUPPLIER_REGION": "Region", "TOTAL_ORDERS": "Orders", "TOTAL_ORDER_VALUE": "Order Value",
    "AT_RISK_ORDERS": "At Risk", "REVENUE_AT_RISK": "Risk $", "RISK_PCT": "Risk %",
    "LATE_ORDERS": "Late", "SHORT_ORDERS": "Short", "OVERDUE_ORDERS": "Overdue",
})
enhanced_table(
    display[["ID", "Supplier", "Country", "Region", "Orders", "Order Value",
             "At Risk", "Risk $", "Risk %", "Late", "Short", "Overdue"]],
    key="supplier_risk_detail", height=450,
)

# =============================================================================
# DATA LINEAGE
# =============================================================================
section("Data Lineage")
render_lineage_flow([
    {"icon": "factory", "title": "Source System", "detail": "ORDERS + SHIPMENTS"},
    {"icon": "graph", "title": "Ontology Layer", "detail": "ENTITY_TYPE"},
    {"icon": "book", "title": "Metric Registry", "detail": "Revenue At Risk"},
    {"icon": "chart", "title": "Analytics View", "detail": "REVENUE_AT_RISK_ANALYTICS"},
    {"icon": "sparkle", "title": "Supplier Risk", "detail": "This page"},
])

footer()
