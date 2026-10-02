import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils.db import run_query as run, safe_float
from utils.theme import T
from utils.components import page_header, kpi_card, kpi_grid, section, footer
from utils.charts import render_chart, SERIES

page_header("What-If Analysis", "Interactive simulator — project impact of supply chain improvements")

# -- baseline data -------------------------------------------------------------
baseline = {}
baseline["erp_otif"] = safe_float(run(
    "SELECT ROUND(SUM(OTIF_COUNT)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
    "FROM CHAINTRUTH_DB.ANALYTICS.ERP_OTIF"
)["V"].iloc[0])

baseline["conflict_rate"] = safe_float(run(
    "SELECT ROUND(SUM(CONFLICTED_SHIPMENTS)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
    "FROM CHAINTRUTH_DB.ANALYTICS.CHAINTRUTH_OTIF"
)["V"].iloc[0])

rev = run(
    "SELECT SUM(REVENUE_AT_RISK) AS RAR, SUM(TOTAL_ORDER_VALUE) AS TOV "
    "FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS"
).iloc[0]
baseline["rev_risk"] = safe_float(rev["RAR"])
baseline["total_rev"] = safe_float(rev["TOV"])
baseline["risk_pct"] = baseline["rev_risk"] * 100 / baseline["total_rev"] if baseline["total_rev"] else 0

baseline["fill_rate"] = safe_float(run(
    "SELECT ROUND(SUM(TOTAL_QTY_SHIPPED)*100.0/NULLIF(SUM(TOTAL_QTY_ORDERED),0),1) AS V "
    "FROM CHAINTRUTH_DB.ANALYTICS.FILL_RATE_ANALYTICS"
)["V"].iloc[0])

baseline["lead_time"] = safe_float(run(
    "SELECT ROUND(SUM(AVG_LEAD_TIME_DAYS*TOTAL_SHIPMENTS)/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
    "FROM CHAINTRUTH_DB.ANALYTICS.LEAD_TIME_ANALYTICS"
)["V"].iloc[0])

# -- scenario inputs -----------------------------------------------------------
section("Scenario parameters")
st.caption("Adjust the sliders to model improvements. The simulator projects impact on key metrics.")

col_l, col_r = st.columns(2)
with col_l:
    otif_improvement = st.slider("OTIF improvement (pp)", 0, 50, 10,
        help="How many percentage points could OTIF improve with better delivery management?")
    lead_time_reduction = st.slider("Lead time reduction (%)", 0, 50, 15,
        help="What percentage reduction in average lead time is achievable?")
with col_r:
    conflict_reduction = st.slider("Conflict rate reduction (pp)", 0, 50, 20,
        help="How much could conflict rate decrease if teams align on definitions?")
    fill_improvement = st.slider("Fill rate improvement (pp)", 0.0, 5.0, 1.0, step=0.5,
        help="How much could fill rate improve with better inventory management?")

# -- projected metrics ---------------------------------------------------------
projected = {}
projected["erp_otif"] = min(baseline["erp_otif"] + otif_improvement, 100)
projected["conflict_rate"] = max(baseline["conflict_rate"] - conflict_reduction, 0)
projected["lead_time"] = baseline["lead_time"] * (1 - lead_time_reduction / 100)
projected["fill_rate"] = min(baseline["fill_rate"] + fill_improvement, 100)

otif_factor = (100 - projected["erp_otif"]) / (100 - baseline["erp_otif"]) if baseline["erp_otif"] < 100 else 0
projected["rev_risk"] = baseline["rev_risk"] * otif_factor
projected["risk_pct"] = projected["rev_risk"] * 100 / baseline["total_rev"] if baseline["total_rev"] else 0
rev_saved = baseline["rev_risk"] - projected["rev_risk"]

section("Projected impact")

def delta_caption(new, old, suffix="%", invert=False):
    d = new - old
    sign = "+" if d > 0 else ""
    good = (d < 0) if invert else (d > 0)
    label = "improvement" if good else "decline"
    return f"was {old:.1f}{suffix}, {sign}{d:.1f}{suffix} ({label})"

kpi_grid([
    kpi_card("Projected OTIF", f"{projected['erp_otif']:.1f}%",
             status="healthy" if projected["erp_otif"] > 50 else "warning",
             caption=delta_caption(projected["erp_otif"], baseline["erp_otif"])),
    kpi_card("Projected conflict", f"{projected['conflict_rate']:.1f}%",
             status="healthy" if projected["conflict_rate"] < 30 else "warning",
             caption=delta_caption(projected["conflict_rate"], baseline["conflict_rate"], invert=True)),
    kpi_card("Projected risk", f"${projected['rev_risk']/1e6:.1f}M",
             status="healthy" if projected["risk_pct"] < 50 else "warning",
             caption=f"was ${baseline['rev_risk']/1e6:.1f}M"),
    kpi_card("Projected lead time", f"{projected['lead_time']:.1f}d",
             status="healthy" if projected["lead_time"] < 12 else "warning",
             caption=delta_caption(projected["lead_time"], baseline["lead_time"], suffix="d", invert=True)),
    kpi_card("Projected fill rate", f"{projected['fill_rate']:.1f}%",
             status="healthy" if projected["fill_rate"] > 97 else "warning",
             caption=delta_caption(projected["fill_rate"], baseline["fill_rate"])),
])

# -- before/after charts -------------------------------------------------------
section("Before vs after comparison")
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    metrics = ["ERP OTIF", "Fill Rate"]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=metrics, y=[baseline["erp_otif"], baseline["fill_rate"]],
        name="Current", marker_color=SERIES[5],
        text=[f"{baseline['erp_otif']:.1f}%", f"{baseline['fill_rate']:.1f}%"],
        textposition="outside",
    ))
    fig.add_trace(go.Bar(
        x=metrics, y=[projected["erp_otif"], projected["fill_rate"]],
        name="Projected", marker_color=SERIES[1],
        text=[f"{projected['erp_otif']:.1f}%", f"{projected['fill_rate']:.1f}%"],
        textposition="outside",
    ))
    fig.update_layout(barmode="group", yaxis_range=[0, 110])
    render_chart(fig, "bar", "Performance improvement",
                 subtitle="Current baseline vs projected after improvements.")

with col_chart2:
    metrics2 = ["Conflict Rate", "Revenue Risk %", "Lead Time (d)"]
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=metrics2, y=[baseline["conflict_rate"], baseline["risk_pct"], baseline["lead_time"]],
        name="Current", marker_color=SERIES[5],
    ))
    fig2.add_trace(go.Bar(
        x=metrics2, y=[projected["conflict_rate"], projected["risk_pct"], projected["lead_time"]],
        name="Projected", marker_color=SERIES[0],
    ))
    fig2.update_layout(barmode="group")
    render_chart(fig2, "bar", "Risk reduction",
                 subtitle="Lower conflict, revenue risk, and lead time.")

# -- revenue impact ------------------------------------------------------------
section("Revenue impact summary")

if rev_saved > 0:
    st.markdown(
        f'<div style="background:{T["success_tint"]}; border:1px solid {T["border"]}; '
        f'border-radius:8px; padding:24px; text-align:center; margin-bottom:16px;">'
        f'<div style="font-size:32px; font-weight:700; color:{T["success"]};">'
        f'${rev_saved/1e6:.1f}M</div>'
        f'<div style="font-size:14px; color:{T["success"]};">Projected revenue saved</div>'
        f'<div style="font-size:13px; color:{T["text_muted"]}; margin-top:8px;">'
        f'By improving OTIF by {otif_improvement}pp, reducing conflict by {conflict_reduction}pp, '
        f'and cutting lead time by {lead_time_reduction}%</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
else:
    st.info("Adjust the sliders above to model improvement scenarios.")

footer()
