import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils.db import run_query as run, safe_float
from utils.theme import T
from utils.components import page_header, kpi_card, kpi_grid, section, insight, insight_panel, alert_card, footer
from utils.charts import render_chart, SERIES

st.markdown(
    f'<div style="text-align:center; padding:24px 0 6px 0;">'
    f'<span style="font-size:42px; font-weight:800; color:{T["primary"]}; letter-spacing:-1px;">'
    f'Chain<span style="color:{T["text"]};">Truth</span></span>'
    f'</div>',
    unsafe_allow_html=True,
)
page_header("Dashboard", "Supply chain governance and decision intelligence")

# -- sidebar filters -----------------------------------------------------------
suppliers_df = run(
    "SELECT DISTINCT SUPPLIER_ID, SUPPLIER_NAME "
    "FROM CHAINTRUTH_DB.RAW.SUPPLIERS ORDER BY SUPPLIER_ID"
)
regions_df = run("SELECT DISTINCT REGION FROM CHAINTRUTH_DB.RAW.SUPPLIERS ORDER BY REGION")
segments_df = run("SELECT DISTINCT SEGMENT FROM CHAINTRUTH_DB.RAW.CUSTOMERS ORDER BY SEGMENT")
plants_df = run(
    "SELECT DISTINCT PLANT_ID, PLANT_NAME FROM CHAINTRUTH_DB.RAW.PLANTS ORDER BY PLANT_ID"
)

st.sidebar.markdown("**Filters**")
sel_suppliers = st.sidebar.multiselect(
    "Supplier", options=suppliers_df["SUPPLIER_ID"].tolist(),
    format_func=lambda x: f"{x} - {suppliers_df.loc[suppliers_df['SUPPLIER_ID']==x, 'SUPPLIER_NAME'].iloc[0]}",
)
sel_regions = st.sidebar.multiselect("Region", options=regions_df["REGION"].tolist())
sel_segments = st.sidebar.multiselect("Customer Segment", options=segments_df["SEGMENT"].tolist())
sel_plants = st.sidebar.multiselect(
    "Plant", options=plants_df["PLANT_ID"].tolist(),
    format_func=lambda x: f"{x} - {plants_df.loc[plants_df['PLANT_ID']==x, 'PLANT_NAME'].iloc[0]}",
)


def build_where(supplier_col="SUPPLIER_ID", region_col="SUPPLIER_REGION",
                segment_col="CUSTOMER_SEGMENT", plant_col="PLANT_ID"):
    clauses = []
    if sel_suppliers:
        vals = ",".join("'" + s + "'" for s in sel_suppliers)
        clauses.append(supplier_col + " IN (" + vals + ")")
    if sel_regions:
        vals = ",".join("'" + r + "'" for r in sel_regions)
        clauses.append(region_col + " IN (" + vals + ")")
    if sel_segments:
        vals = ",".join("'" + s + "'" for s in sel_segments)
        clauses.append(segment_col + " IN (" + vals + ")")
    if sel_plants:
        vals = ",".join("'" + p + "'" for p in sel_plants)
        clauses.append(plant_col + " IN (" + vals + ")")
    return " AND ".join(clauses)


where = build_where()
where_sql = f"WHERE {where}" if where else ""

# -- KPI data ------------------------------------------------------------------
erp_otif = safe_float(run(
    f"SELECT ROUND(SUM(OTIF_COUNT)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
    f"FROM CHAINTRUTH_DB.ANALYTICS.ERP_OTIF {where_sql}"
)["V"].iloc[0])

log_otif = safe_float(run(
    f"SELECT ROUND(SUM(OTIF_COUNT)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
    f"FROM CHAINTRUTH_DB.ANALYTICS.LOGISTICS_OTIF {where_sql}"
)["V"].iloc[0])

sup_otif = safe_float(run(
    f"SELECT ROUND(SUM(OTIF_COUNT)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
    f"FROM CHAINTRUTH_DB.ANALYTICS.SUPPLIER_OTIF {where_sql}"
)["V"].iloc[0])

conflict_rate = safe_float(run(
    f"SELECT ROUND(SUM(CONFLICTED_SHIPMENTS)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
    f"FROM CHAINTRUTH_DB.ANALYTICS.CHAINTRUTH_OTIF {where_sql}"
)["V"].iloc[0])

fill_rate = safe_float(run(
    f"SELECT ROUND(SUM(TOTAL_QTY_SHIPPED)*100.0/NULLIF(SUM(TOTAL_QTY_ORDERED),0),1) AS V "
    f"FROM CHAINTRUTH_DB.ANALYTICS.FILL_RATE_ANALYTICS {where_sql}"
)["V"].iloc[0])

lead_time = safe_float(run(
    f"SELECT ROUND(SUM(AVG_LEAD_TIME_DAYS*TOTAL_SHIPMENTS)/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
    f"FROM CHAINTRUTH_DB.ANALYTICS.LEAD_TIME_ANALYTICS {where_sql}"
)["V"].iloc[0])

rev_risk = safe_float(run(
    f"SELECT SUM(REVENUE_AT_RISK) AS V "
    f"FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS {where_sql}"
)["V"].iloc[0])

total_rev = safe_float(run(
    f"SELECT SUM(TOTAL_ORDER_VALUE) AS V "
    f"FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS {where_sql}"
)["V"].iloc[0])

risk_pct = rev_risk * 100.0 / total_rev if total_rev else 0

active_suppliers = int(safe_float(run(
    f"SELECT COUNT(DISTINCT SUPPLIER_ID) AS V "
    f"FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS {where_sql}"
)["V"].iloc[0]))

# -- helpers -------------------------------------------------------------------
def otif_status(v): return "critical" if v < 30 else ("warning" if v < 70 else "healthy")
def conflict_status(v): return "critical" if v > 50 else ("warning" if v > 25 else "healthy")
def risk_status(v): return "critical" if v > 70 else ("warning" if v > 40 else "healthy")

# -- KPI cards -----------------------------------------------------------------
kpi_grid([
    kpi_card("Canonical OTIF", f"{erp_otif:.1f}%", status=otif_status(erp_otif), icon_name="chart"),
    kpi_card("Revenue at risk", f"${rev_risk/1e6:.1f}M", status=risk_status(risk_pct), icon_name="dollar"),
    kpi_card("Conflict rate", f"{conflict_rate:.1f}%", status=conflict_status(conflict_rate), icon_name="alert"),
    kpi_card("Active suppliers", f"{active_suppliers}", icon_name="factory"),
    kpi_card("Fill rate", f"{fill_rate:.1f}%", status="healthy" if fill_rate > 95 else "warning", icon_name="box"),
    kpi_card("Avg lead time", f"{lead_time:.1f} days", status="healthy" if lead_time < 15 else "warning", icon_name="clock"),
])

# -- alerts --------------------------------------------------------------------
section("Active alerts")
alerts_html = ""
if conflict_rate > 50:
    alerts_html += alert_card(
        "Conflict rate exceeds 50% governance threshold",
        "Teams are reporting fundamentally different performance numbers from identical data.",
        "danger",
    )
if risk_pct > 70:
    alerts_html += alert_card(
        "Revenue at risk exceeds 70%",
        f"${rev_risk/1e6:.1f}M of ${total_rev/1e6:.1f}M total order value is exposed.",
        "danger",
    )

worst_sup = run(
    f"SELECT SUPPLIER_NAME, SUM(REVENUE_AT_RISK) AS RAR "
    f"FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS {where_sql} "
    f"GROUP BY SUPPLIER_NAME ORDER BY RAR DESC LIMIT 1"
)
if not worst_sup.empty:
    ws = worst_sup.iloc[0]
    alerts_html += alert_card(
        f"{ws['SUPPLIER_NAME']} requires immediate review",
        f"${safe_float(ws['RAR'])/1e6:.2f}M revenue at risk — highest exposure in portfolio.",
        "warning",
    )
if erp_otif < 30:
    alerts_html += alert_card(
        f"Canonical OTIF at {erp_otif:.1f}%",
        "Well below acceptable threshold.",
        "warning",
    )
st.markdown(alerts_html, unsafe_allow_html=True)

# -- OTIF comparison -----------------------------------------------------------
section("OTIF by definition")
col_l, col_r = st.columns([3, 2])

with col_l:
    fig_otif = go.Figure()
    for name, val, color in [("ERP (Canonical)", erp_otif, SERIES[4]),
                              ("Logistics", log_otif, SERIES[2]),
                              ("Supplier", sup_otif, SERIES[1])]:
        fig_otif.add_trace(go.Bar(
            x=[name], y=[val], marker_color=color, name=name,
            text=[f"{val:.1f}%"], textposition="outside",
        ))
    fig_otif.update_layout(showlegend=False, yaxis_range=[0, 100], yaxis_title="OTIF Rate (%)")
    render_chart(fig_otif, "bar", "OTIF by Definition", subtitle="Same underlying shipment data produces three different OTIF numbers.", legend="none")

with col_r:
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=conflict_rate,
        title={"text": "Conflict rate", "font": {"size": 14, "color": T["text_muted"]}},
        number={"font": {"size": 36, "color": T["text"]}, "suffix": "%"},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": T["text_muted"], "dtick": 25},
            "bar": {"color": T["danger"] if conflict_rate > 50 else T["warning"]},
            "bgcolor": T["bg"],
            "steps": [
                {"range": [0, 25], "color": T["success_tint"]},
                {"range": [25, 50], "color": T["warning_tint"]},
                {"range": [50, 100], "color": T["danger_tint"]},
            ],
            "threshold": {"line": {"color": T["danger"], "width": 2}, "thickness": 0.8, "value": 50},
        },
    ))
    render_chart(fig_gauge, "gauge", "Conflict Rate", legend="none")

# -- risk analytics ------------------------------------------------------------
section("Risk analytics")
col_l2, col_r2 = st.columns(2)

with col_l2:
    rev_by_sup = run(
        f"SELECT SUPPLIER_NAME, SUM(REVENUE_AT_RISK) AS REVENUE_AT_RISK, "
        f"  SUM(TOTAL_ORDER_VALUE) AS TOTAL_ORDER_VALUE "
        f"FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS {where_sql} "
        f"GROUP BY SUPPLIER_NAME ORDER BY REVENUE_AT_RISK DESC LIMIT 10"
    )
    if not rev_by_sup.empty:
        fig_rev = px.bar(
            rev_by_sup, x="REVENUE_AT_RISK", y="SUPPLIER_NAME", orientation="h",
            labels={"REVENUE_AT_RISK": "Revenue at risk ($)", "SUPPLIER_NAME": ""},
            text=rev_by_sup["REVENUE_AT_RISK"].apply(lambda x: f"${float(x)/1e6:.2f}M"),
        )
        fig_rev.update_traces(marker_color=SERIES[4], textposition="outside")
        fig_rev.update_layout(yaxis=dict(autorange="reversed"))
        render_chart(fig_rev, "bar", "Revenue at Risk by Supplier", subtitle="Top 10 suppliers ranked by absolute revenue exposure.", legend="none")
    else:
        st.info("No revenue at risk data for current filters.")

with col_r2:
    risk_breakdown = run(
        f"SELECT SUM(LATE_DELIVERY_REVENUE) AS LATE, "
        f"  SUM(SHORT_SHIPPED_REVENUE) AS SHORT, "
        f"  SUM(OVERDUE_OPEN_REVENUE) AS OVERDUE "
        f"FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS {where_sql}"
    ).iloc[0]
    rev_totals = pd.DataFrame({
        "Risk Type": ["Late Delivery", "Short Shipped", "Overdue Open"],
        "Revenue": [safe_float(risk_breakdown["LATE"]), safe_float(risk_breakdown["SHORT"]),
                    safe_float(risk_breakdown["OVERDUE"])],
    })
    fig_donut = px.pie(
        rev_totals, names="Risk Type", values="Revenue",
        color="Risk Type",
        color_discrete_map={"Late Delivery": SERIES[4], "Short Shipped": SERIES[2], "Overdue Open": SERIES[0]},
        hole=0.5,
    )
    fig_donut.update_traces(textinfo="percent+label", textposition="outside")
    render_chart(fig_donut, "donut", "Risk Breakdown by Type", subtitle="Risk breakdown by type — late delivery is the dominant driver.")

# -- trend charts --------------------------------------------------------------
section("Trends")
col_l3, col_r3 = st.columns(2)

with col_l3:
    lt_trend = run(
        f"SELECT ORDER_MONTH, "
        f"  ROUND(SUM(AVG_LEAD_TIME_DAYS*TOTAL_SHIPMENTS)/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS AVG_LEAD_TIME "
        f"FROM CHAINTRUTH_DB.ANALYTICS.LEAD_TIME_ANALYTICS {where_sql} "
        f"GROUP BY ORDER_MONTH ORDER BY ORDER_MONTH"
    )
    fig_lt = px.line(lt_trend, x="ORDER_MONTH", y="AVG_LEAD_TIME",
                     markers=True, labels={"ORDER_MONTH": "Month", "AVG_LEAD_TIME": "Avg lead time (days)"})
    fig_lt.update_traces(line_color=SERIES[0])
    render_chart(fig_lt, "line", "Average Lead Time", subtitle="Monthly weighted-average lead time from order placement to delivery.")

with col_r3:
    conflict_trend = run(
        f"SELECT ORDER_MONTH, "
        f"  ROUND(SUM(CONFLICTED_SHIPMENTS)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS CONFLICT_RATE "
        f"FROM CHAINTRUTH_DB.ANALYTICS.CHAINTRUTH_OTIF {where_sql} "
        f"GROUP BY ORDER_MONTH ORDER BY ORDER_MONTH"
    )
    fig_conflict = px.area(conflict_trend, x="ORDER_MONTH", y="CONFLICT_RATE",
                           labels={"ORDER_MONTH": "Month", "CONFLICT_RATE": "Conflict rate (%)"})
    fig_conflict.update_traces(line_color=SERIES[4], fillcolor="rgba(209,73,91,0.08)")
    fig_conflict.update_layout(yaxis_range=[0, 100])
    render_chart(fig_conflict, "area", "Conflict Rate Over Time", subtitle="Percentage of shipments receiving conflicting on-time verdicts each month.")

# -- executive insights --------------------------------------------------------
section("Executive insights")

spread = sup_otif - erp_otif
items = [
    insight(
        "OTIF definition spread",
        f"Supplier OTIF ({sup_otif:.1f}%) is <b>{spread:.1f} pp higher</b> than ERP OTIF ({erp_otif:.1f}%). "
        f"Procurement sees strong performance while Finance flags failures.",
        "danger" if spread > 30 else "warning",
    ),
    insight(
        "Conflict rate exceeds governance threshold",
        f"At <b>{conflict_rate:.1f}%</b>, the majority of shipments receive conflicting on-time verdicts.",
        "danger" if conflict_rate > 50 else "warning",
    ),
    insight(
        "Revenue exposure",
        f"<b>${rev_risk/1e6:.1f}M</b> of <b>${total_rev/1e6:.1f}M</b> total revenue ({risk_pct:.1f}%) "
        f"is at risk due to late deliveries, short shipments, or overdue open orders.",
        "danger" if risk_pct > 70 else "warning",
    ),
]

worst_region = run(
    f"SELECT SUPPLIER_REGION, "
    f"  ROUND(SUM(REVENUE_AT_RISK)*100.0/NULLIF(SUM(TOTAL_ORDER_VALUE),0),1) AS RISK_PCT "
    f"FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS {where_sql} "
    f"GROUP BY SUPPLIER_REGION ORDER BY SUM(REVENUE_AT_RISK) DESC LIMIT 1"
)
if not worst_region.empty:
    wr = worst_region.iloc[0]
    items.append(insight(
        f"{wr['SUPPLIER_REGION']} leads revenue risk",
        f"Highest absolute revenue at risk with a rate of <b>{safe_float(wr['RISK_PCT']):.1f}%</b>.",
        "warning",
    ))

items.append(insight(
    "Fill rate healthy",
    f"At <b>{fill_rate:.1f}%</b>, inventory availability is strong. Risk is driven by timing, not stock.",
    "success",
))

insight_panel(items)

footer()
