import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.db import run_query as run, safe_float

st.set_page_config(page_title="Supplier Risk Analysis", layout="wide")
st.title("Supplier Risk Analysis")
st.caption(
    "Identifying which suppliers put the most revenue at risk and why — "
    "late delivery, short shipments, or overdue open orders."
)

# -- sidebar filters -----------------------------------------------------------
st.sidebar.header("Filters")

regions = run(
    "SELECT DISTINCT SUPPLIER_REGION AS R "
    "FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS ORDER BY R"
)
segments = run(
    "SELECT DISTINCT CUSTOMER_SEGMENT AS S "
    "FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS ORDER BY S"
)
plants = run(
    "SELECT DISTINCT PLANT_ID AS P "
    "FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS ORDER BY P"
)

sel_regions = st.sidebar.multiselect("Supplier Region", regions["R"].tolist())
sel_segments = st.sidebar.multiselect("Customer Segment", segments["S"].tolist())
sel_plants = st.sidebar.multiselect("Plant", plants["P"].tolist())

clauses = []
if sel_regions:
    clauses.append("SUPPLIER_REGION IN (" + ",".join(f"'{r}'" for r in sel_regions) + ")")
if sel_segments:
    clauses.append("CUSTOMER_SEGMENT IN (" + ",".join(f"'{s}'" for s in sel_segments) + ")")
if sel_plants:
    clauses.append("PLANT_ID IN (" + ",".join(f"'{p}'" for p in sel_plants) + ")")
where = "WHERE " + " AND ".join(clauses) if clauses else ""

# =============================================================================
# load supplier-level aggregates
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

# monthly trend
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

# region aggregates
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
# ROW 1 — headline KPIs
# =============================================================================
totals = suppliers.agg({
    "TOTAL_ORDERS": "sum", "AT_RISK_ORDERS": "sum",
    "TOTAL_ORDER_VALUE": "sum", "REVENUE_AT_RISK": "sum",
    "LATE_ORDERS": "sum", "SHORT_ORDERS": "sum", "OVERDUE_ORDERS": "sum",
})
risk_pct = float(totals["REVENUE_AT_RISK"]) * 100.0 / float(totals["TOTAL_ORDER_VALUE"]) if totals["TOTAL_ORDER_VALUE"] else 0

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Revenue", f"${float(totals['TOTAL_ORDER_VALUE'])/1e6:.1f}M")
c2.metric("Revenue At Risk", f"${float(totals['REVENUE_AT_RISK'])/1e6:.1f}M")
c3.metric("Risk Rate", f"{risk_pct:.1f}%")
c4.metric("Late Delivery", f"{int(totals['LATE_ORDERS']):,} orders")
c5.metric("Short Shipped", f"{int(totals['SHORT_ORDERS']):,} orders")
c6.metric("Overdue Open", f"{int(totals['OVERDUE_ORDERS']):,} orders")

st.markdown("---")

# =============================================================================
# ROW 2 — revenue at risk trend + risk breakdown by type
# =============================================================================
col_l, col_r = st.columns(2)

with col_l:
    trend_long = monthly.melt(
        id_vars="ORDER_MONTH",
        value_vars=["LATE_REVENUE", "SHORT_REVENUE", "OVERDUE_REVENUE"],
        var_name="Risk Type", value_name="Revenue",
    )
    trend_long["Risk Type"] = trend_long["Risk Type"].map({
        "LATE_REVENUE": "Late Delivery",
        "SHORT_REVENUE": "Short Shipped",
        "OVERDUE_REVENUE": "Overdue Open",
    })
    fig_trend = px.area(
        trend_long, x="ORDER_MONTH", y="Revenue", color="Risk Type",
        title="Revenue At Risk by Type (Monthly)",
        labels={"ORDER_MONTH": "Month", "Revenue": "Revenue ($)"},
        color_discrete_map={
            "Late Delivery": "#EF553B",
            "Short Shipped": "#FFA15A",
            "Overdue Open": "#636EFA",
        },
    )
    fig_trend.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_trend, use_container_width=True)

with col_r:
    rev_totals = pd.DataFrame({
        "Risk Type": ["Late Delivery", "Short Shipped", "Overdue Open"],
        "Revenue": [
            float(suppliers["LATE_REVENUE"].sum()),
            float(suppliers["SHORT_REVENUE"].sum()),
            float(suppliers["OVERDUE_REVENUE"].sum()),
        ],
    })
    fig_donut = px.pie(
        rev_totals, names="Risk Type", values="Revenue",
        title="Risk Breakdown by Type (Revenue)",
        color="Risk Type",
        color_discrete_map={
            "Late Delivery": "#EF553B",
            "Short Shipped": "#FFA15A",
            "Overdue Open": "#636EFA",
        },
        hole=0.45,
    )
    fig_donut.update_traces(textinfo="percent+label", textposition="outside")
    st.plotly_chart(fig_donut, use_container_width=True)

st.markdown("---")

# =============================================================================
# ROW 3 — top suppliers bar + region comparison
# =============================================================================
st.subheader("Supplier & Region Breakdown")

col_l2, col_r2 = st.columns(2)

with col_l2:
    top10 = suppliers.head(10)
    fig_sup = go.Figure()
    fig_sup.add_trace(go.Bar(
        y=top10["SUPPLIER_NAME"], x=top10["REVENUE_AT_RISK"],
        name="At Risk", orientation="h", marker_color="#EF553B",
        text=top10["REVENUE_AT_RISK"].apply(lambda v: f"${float(v)/1e6:.2f}M"),
        textposition="auto",
    ))
    fig_sup.add_trace(go.Bar(
        y=top10["SUPPLIER_NAME"], x=top10["SAFE_REVENUE"],
        name="Safe", orientation="h", marker_color="#00CC96",
    ))
    fig_sup.update_layout(
        title="Top 10 Suppliers: At Risk vs Safe Revenue",
        barmode="stack",
        yaxis=dict(autorange="reversed"),
        xaxis_title="Revenue ($)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_sup, use_container_width=True)

with col_r2:
    fig_reg = go.Figure()
    fig_reg.add_trace(go.Bar(
        x=by_region["SUPPLIER_REGION"], y=by_region["LATE_ORDERS"],
        name="Late", marker_color="#EF553B",
    ))
    fig_reg.add_trace(go.Bar(
        x=by_region["SUPPLIER_REGION"], y=by_region["SHORT_ORDERS"],
        name="Short", marker_color="#FFA15A",
    ))
    fig_reg.add_trace(go.Bar(
        x=by_region["SUPPLIER_REGION"], y=by_region["OVERDUE_ORDERS"],
        name="Overdue", marker_color="#636EFA",
    ))
    fig_reg.update_layout(
        title="Risk Type by Region (Order Count)",
        barmode="stack",
        yaxis_title="Orders",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_reg, use_container_width=True)

st.markdown("---")

# =============================================================================
# ROW 4 — risk-volume scatter + risk heatmap
# =============================================================================
st.subheader("Risk Concentration")

col_l3, col_r3 = st.columns(2)

with col_l3:
    fig_scatter = px.scatter(
        suppliers, x="TOTAL_ORDER_VALUE", y="RISK_PCT",
        size="AT_RISK_ORDERS", color="SUPPLIER_REGION",
        hover_name="SUPPLIER_NAME",
        title="Order Volume vs Risk Rate",
        labels={
            "TOTAL_ORDER_VALUE": "Total Order Value ($)",
            "RISK_PCT": "Risk Rate (%)",
            "SUPPLIER_REGION": "Region",
        },
    )
    fig_scatter.add_hline(y=float(risk_pct), line_dash="dash", line_color="gray",
                          annotation_text=f"Avg {float(risk_pct):.0f}%")
    fig_scatter.update_layout(yaxis_range=[0, 105])
    st.plotly_chart(fig_scatter, use_container_width=True)

with col_r3:
    # risk rate per region x segment
    heatmap_sql = (
        f"SELECT SUPPLIER_REGION, CUSTOMER_SEGMENT, "
        f"  ROUND(SUM(REVENUE_AT_RISK)*100.0/NULLIF(SUM(TOTAL_ORDER_VALUE),0),1) AS RISK_PCT "
        f"FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS {where} "
        f"GROUP BY SUPPLIER_REGION, CUSTOMER_SEGMENT"
    )
    hm = run(heatmap_sql)
    if not hm.empty:
        hm_pivot = hm.pivot(index="SUPPLIER_REGION", columns="CUSTOMER_SEGMENT", values="RISK_PCT")
        fig_hm = px.imshow(
            hm_pivot, text_auto=".0f",
            title="Risk Rate: Region x Customer Segment (%)",
            labels=dict(x="Customer Segment", y="Supplier Region", color="Risk %"),
            color_continuous_scale="OrRd",
            aspect="auto",
        )
        st.plotly_chart(fig_hm, use_container_width=True)
    else:
        st.info("No data for heatmap with current filters.")

st.markdown("---")

# =============================================================================
# ROW 5 — full supplier table
# =============================================================================
st.subheader("Supplier Detail")

display = suppliers.rename(columns={
    "SUPPLIER_ID": "ID",
    "SUPPLIER_NAME": "Supplier",
    "SUPPLIER_COUNTRY": "Country",
    "SUPPLIER_REGION": "Region",
    "TOTAL_ORDERS": "Orders",
    "TOTAL_ORDER_VALUE": "Order Value",
    "AT_RISK_ORDERS": "At Risk",
    "REVENUE_AT_RISK": "Risk $",
    "RISK_PCT": "Risk %",
    "LATE_ORDERS": "Late",
    "SHORT_ORDERS": "Short",
    "OVERDUE_ORDERS": "Overdue",
})

st.dataframe(
    display[["ID", "Supplier", "Country", "Region", "Orders",
             "Order Value", "At Risk", "Risk $", "Risk %",
             "Late", "Short", "Overdue"]],
    use_container_width=True,
    hide_index=True,
    height=450,
    column_config={
        "Order Value": st.column_config.NumberColumn(format="$%.0f"),
        "Risk $": st.column_config.NumberColumn(format="$%.0f"),
        "Risk %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
    },
)
