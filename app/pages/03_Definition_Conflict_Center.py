import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.db import run_query as run, safe_float

st.set_page_config(page_title="Definition Conflict Center", layout="wide")
st.title("Definition Conflict Center")
st.caption(
    "Quantifying how competing OTIF definitions produce different performance "
    "numbers from the same underlying data."
)

# -- sidebar filters -----------------------------------------------------------
st.sidebar.header("Filters")

regions = run(
    "SELECT DISTINCT SUPPLIER_REGION AS R "
    "FROM CHAINTRUTH_DB.ANALYTICS.CHAINTRUTH_OTIF ORDER BY R"
)
segments = run(
    "SELECT DISTINCT CUSTOMER_SEGMENT AS S "
    "FROM CHAINTRUTH_DB.ANALYTICS.CHAINTRUTH_OTIF ORDER BY S"
)

sel_regions = st.sidebar.multiselect("Supplier Region", regions["R"].tolist())
sel_segments = st.sidebar.multiselect("Customer Segment", segments["S"].tolist())

clauses = []
if sel_regions:
    clauses.append("SUPPLIER_REGION IN (" + ",".join(f"'{r}'" for r in sel_regions) + ")")
if sel_segments:
    clauses.append("CUSTOMER_SEGMENT IN (" + ",".join(f"'{s}'" for s in sel_segments) + ")")
where = "WHERE " + " AND ".join(clauses) if clauses else ""

# =============================================================================
# ROW 1 — headline KPIs
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

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Conflict Rate", f"{safe_float(headline['CONFLICT_RATE'])}%")
c2.metric("Conflicted Shipments", f"{int(safe_float(headline['CONFLICTED'])):,} / {int(safe_float(headline['TOTAL'])):,}")
c3.metric("ERP OTIF (Canonical)", f"{safe_float(headline['ERP_OTIF'])}%")
c4.metric("Logistics On-Time", f"{safe_float(headline['LOG_OT'])}%")
c5.metric("Supplier On-Time", f"{safe_float(headline['SUP_OT'])}%")

spread = safe_float(headline["SUP_OT"]) - safe_float(headline["ERP_OTIF"])
st.markdown(
    f"> **Definition spread: {spread:.1f} percentage points.** "
    f"The same shipments score {headline['SUP_OT']}% on-time by the supplier's "
    f"measure but only {headline['ERP_OTIF']}% by the ERP standard."
)

st.markdown("---")

# =============================================================================
# ROW 2 — conflict rate trend + OTIF comparison over time
# =============================================================================
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
    fig_conflict = px.area(
        trend, x="ORDER_MONTH", y="CONFLICT_RATE",
        title="Conflict Rate Over Time",
        labels={"ORDER_MONTH": "Month", "CONFLICT_RATE": "Conflict Rate (%)"},
    )
    fig_conflict.update_traces(line_color="#EF553B", fillcolor="rgba(239,85,59,0.15)")
    fig_conflict.update_layout(yaxis_range=[0, 100])
    st.plotly_chart(fig_conflict, use_container_width=True)

with col_r:
    otif_long = trend.melt(
        id_vars="ORDER_MONTH",
        value_vars=["ERP_OT", "LOG_OT", "SUP_OT"],
        var_name="Definition", value_name="On-Time Rate (%)",
    )
    otif_long["Definition"] = otif_long["Definition"].map({
        "ERP_OT": "ERP", "LOG_OT": "Logistics", "SUP_OT": "Supplier",
    })
    fig_otif = px.line(
        otif_long, x="ORDER_MONTH", y="On-Time Rate (%)",
        color="Definition", markers=True,
        title="On-Time Rate by Definition Over Time",
        labels={"ORDER_MONTH": "Month"},
        color_discrete_map={"ERP": "#EF553B", "Logistics": "#FFA15A", "Supplier": "#00CC96"},
    )
    fig_otif.update_layout(yaxis_range=[0, 100])
    st.plotly_chart(fig_otif, use_container_width=True)

st.markdown("---")

# =============================================================================
# ROW 3 — conflict by supplier + conflict by region
# =============================================================================
st.subheader("Where Conflicts Are Worst")

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
    fig_sup = px.bar(
        top_n, y="SUPPLIER_NAME", x="CONFLICT_RATE",
        orientation="h",
        title="Top 10 Suppliers by Conflict Rate",
        labels={"CONFLICT_RATE": "Conflict Rate (%)", "SUPPLIER_NAME": ""},
        color="CONFLICT_RATE",
        color_continuous_scale="OrRd",
        text=top_n["CONFLICT_RATE"].apply(lambda v: f"{v:.0f}%"),
    )
    fig_sup.update_layout(
        yaxis=dict(autorange="reversed"),
        coloraxis_showscale=False,
        xaxis_range=[0, 100],
    )
    st.plotly_chart(fig_sup, use_container_width=True)

with col_r2:
    fig_reg = go.Figure()
    fig_reg.add_trace(go.Bar(
        y=by_region["SUPPLIER_REGION"], x=by_region["ERP_OT"],
        name="ERP On-Time", orientation="h", marker_color="#EF553B",
    ))
    fig_reg.add_trace(go.Bar(
        y=by_region["SUPPLIER_REGION"], x=by_region["SUP_OT"],
        name="Supplier On-Time", orientation="h", marker_color="#00CC96",
    ))
    fig_reg.update_layout(
        title="ERP vs Supplier On-Time Rate by Region",
        barmode="group",
        xaxis_title="On-Time Rate (%)",
        yaxis=dict(autorange="reversed"),
        xaxis_range=[0, 100],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_reg, use_container_width=True)

st.markdown("---")

# =============================================================================
# ROW 4 — spread scatter + detailed table
# =============================================================================
st.subheader("Definition Spread Analysis")
st.caption(
    "The spread is the gap between the supplier's on-time rate and the ERP on-time "
    "rate for the same shipments. A large spread means the supplier believes "
    "performance is good while Finance flags it as poor."
)

col_l3, col_r3 = st.columns(2)

with col_l3:
    fig_scatter = px.scatter(
        by_supplier, x="RELIABILITY_SCORE", y="SPREAD",
        size="SHIPMENTS", color="SUPPLIER_REGION",
        hover_name="SUPPLIER_NAME",
        title="Reliability Score vs Definition Spread",
        labels={
            "RELIABILITY_SCORE": "Reliability Score",
            "SPREAD": "Spread (Supplier OT - ERP OT, pp)",
            "SUPPLIER_REGION": "Region",
        },
    )
    fig_scatter.add_hline(y=0, line_dash="dash", line_color="gray",
                          annotation_text="No spread")
    st.plotly_chart(fig_scatter, use_container_width=True)

with col_r3:
    fig_box = px.box(
        by_supplier, x="SUPPLIER_REGION", y="SPREAD",
        color="SUPPLIER_REGION",
        title="Spread Distribution by Region",
        labels={"SUPPLIER_REGION": "Region", "SPREAD": "Spread (pp)"},
    )
    fig_box.update_layout(showlegend=False)
    st.plotly_chart(fig_box, use_container_width=True)

# =============================================================================
# ROW 5 — full supplier table
# =============================================================================
st.markdown("---")
st.subheader("Supplier Detail")

display = by_supplier.rename(columns={
    "SUPPLIER_ID": "ID",
    "SUPPLIER_NAME": "Supplier",
    "SUPPLIER_REGION": "Region",
    "RELIABILITY_SCORE": "Reliability",
    "SHIPMENTS": "Shipments",
    "CONFLICTED": "Conflicted",
    "CONFLICT_RATE": "Conflict %",
    "ERP_OT": "ERP OT %",
    "SUP_OT": "Supplier OT %",
    "SPREAD": "Spread (pp)",
})
st.dataframe(
    display[["ID", "Supplier", "Region", "Reliability", "Shipments",
             "Conflicted", "Conflict %", "ERP OT %", "Supplier OT %", "Spread (pp)"]],
    use_container_width=True,
    hide_index=True,
    height=400,
)
