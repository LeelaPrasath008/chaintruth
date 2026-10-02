import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils.db import run_query as run, safe_float
from utils.theme import inject_css, hero, kpi_card, section, DANGER, WARNING, SUCCESS, PRIMARY

st.set_page_config(page_title="What-If Analysis", layout="wide", page_icon="🔗")
inject_css()

hero("WHAT-IF ANALYSIS", "Interactive simulator — project impact of supply chain improvements")

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

# =============================================================================
# SCENARIO INPUTS
# =============================================================================
section("Scenario Parameters")
st.caption("Adjust the sliders to model improvements. The simulator projects impact on key metrics.")

col_l, col_r = st.columns(2)

with col_l:
    otif_improvement = st.slider(
        "OTIF Improvement (pp)", 0, 50, 10,
        help="How many percentage points could OTIF improve with better delivery management?"
    )
    lead_time_reduction = st.slider(
        "Lead Time Reduction (%)", 0, 50, 15,
        help="What percentage reduction in average lead time is achievable?"
    )

with col_r:
    conflict_reduction = st.slider(
        "Conflict Rate Reduction (pp)", 0, 50, 20,
        help="How much could conflict rate decrease if teams align on definitions?"
    )
    fill_improvement = st.slider(
        "Fill Rate Improvement (pp)", 0.0, 5.0, 1.0, step=0.5,
        help="How much could fill rate improve with better inventory management?"
    )

# =============================================================================
# PROJECTED METRICS
# =============================================================================
projected = {}
projected["erp_otif"] = min(baseline["erp_otif"] + otif_improvement, 100)
projected["conflict_rate"] = max(baseline["conflict_rate"] - conflict_reduction, 0)
projected["lead_time"] = baseline["lead_time"] * (1 - lead_time_reduction / 100)
projected["fill_rate"] = min(baseline["fill_rate"] + fill_improvement, 100)

# Revenue risk reduction: model as proportional to OTIF improvement
otif_factor = (100 - projected["erp_otif"]) / (100 - baseline["erp_otif"]) if baseline["erp_otif"] < 100 else 0
projected["rev_risk"] = baseline["rev_risk"] * otif_factor
projected["risk_pct"] = projected["rev_risk"] * 100 / baseline["total_rev"] if baseline["total_rev"] else 0
rev_saved = baseline["rev_risk"] - projected["rev_risk"]

st.markdown("---")
section("Projected Impact")

# KPI comparison cards
c1, c2, c3, c4, c5 = st.columns(5)

def delta_str(new, old, suffix="%", invert=False):
    d = new - old
    sign = "+" if d > 0 else ""
    color = SUCCESS if (d < 0 if invert else d > 0) else DANGER
    return f'<span style="color:{color}; font-weight:600">{sign}{d:.1f}{suffix}</span>'

with c1:
    d = delta_str(projected["erp_otif"], baseline["erp_otif"])
    st.markdown(kpi_card("📊", f"{projected['erp_otif']:.1f}%", "Projected OTIF",
                          "healthy" if projected["erp_otif"] > 50 else "warning"), unsafe_allow_html=True)
    st.markdown(f"<div style='text-align:center; font-size:0.85rem'>was {baseline['erp_otif']:.1f}% → {d}</div>", unsafe_allow_html=True)

with c2:
    d = delta_str(projected["conflict_rate"], baseline["conflict_rate"], invert=True)
    st.markdown(kpi_card("⚡", f"{projected['conflict_rate']:.1f}%", "Projected Conflict",
                          "healthy" if projected["conflict_rate"] < 30 else "warning"), unsafe_allow_html=True)
    st.markdown(f"<div style='text-align:center; font-size:0.85rem'>was {baseline['conflict_rate']:.1f}% → {d}</div>", unsafe_allow_html=True)

with c3:
    d = delta_str(projected["risk_pct"], baseline["risk_pct"], invert=True)
    st.markdown(kpi_card("💰", f"${projected['rev_risk']/1e6:.1f}M", "Projected Risk",
                          "healthy" if projected["risk_pct"] < 50 else "warning"), unsafe_allow_html=True)
    st.markdown(f"<div style='text-align:center; font-size:0.85rem'>was ${baseline['rev_risk']/1e6:.1f}M → {d}</div>", unsafe_allow_html=True)

with c4:
    d = delta_str(projected["lead_time"], baseline["lead_time"], suffix="d", invert=True)
    st.markdown(kpi_card("🕐", f"{projected['lead_time']:.1f}d", "Projected Lead Time",
                          "healthy" if projected["lead_time"] < 12 else "warning"), unsafe_allow_html=True)
    st.markdown(f"<div style='text-align:center; font-size:0.85rem'>was {baseline['lead_time']:.1f}d → {d}</div>", unsafe_allow_html=True)

with c5:
    d = delta_str(projected["fill_rate"], baseline["fill_rate"])
    st.markdown(kpi_card("📦", f"{projected['fill_rate']:.1f}%", "Projected Fill Rate",
                          "healthy" if projected["fill_rate"] > 97 else "warning"), unsafe_allow_html=True)
    st.markdown(f"<div style='text-align:center; font-size:0.85rem'>was {baseline['fill_rate']:.1f}% → {d}</div>", unsafe_allow_html=True)

# =============================================================================
# BEFORE / AFTER CHARTS
# =============================================================================
st.markdown("---")
section("Before vs After Comparison")

col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    metrics = ["ERP OTIF", "Fill Rate"]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=metrics, y=[baseline["erp_otif"], baseline["fill_rate"]],
        name="Current", marker_color="#94A3B8",
        text=[f"{baseline['erp_otif']:.1f}%", f"{baseline['fill_rate']:.1f}%"],
        textposition="outside",
    ))
    fig.add_trace(go.Bar(
        x=metrics, y=[projected["erp_otif"], projected["fill_rate"]],
        name="Projected", marker_color=SUCCESS,
        text=[f"{projected['erp_otif']:.1f}%", f"{projected['fill_rate']:.1f}%"],
        textposition="outside",
    ))
    fig.update_layout(
        title="Performance Improvement", barmode="group",
        yaxis_range=[0, 110], plot_bgcolor="white", height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)

with col_chart2:
    metrics2 = ["Conflict Rate", "Revenue Risk %", "Lead Time (d)"]
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=metrics2, y=[baseline["conflict_rate"], baseline["risk_pct"], baseline["lead_time"]],
        name="Current", marker_color="#94A3B8",
    ))
    fig2.add_trace(go.Bar(
        x=metrics2, y=[projected["conflict_rate"], projected["risk_pct"], projected["lead_time"]],
        name="Projected", marker_color=PRIMARY,
    ))
    fig2.update_layout(
        title="Risk Reduction", barmode="group",
        plot_bgcolor="white", height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig2, use_container_width=True)

# =============================================================================
# REVENUE IMPACT
# =============================================================================
section("Revenue Impact Summary")

if rev_saved > 0:
    st.markdown(
        f'<div style="background: linear-gradient(135deg, #D1FAE5 0%, #ECFDF5 100%); '
        f'border-radius: 12px; padding: 2rem; text-align: center; margin-bottom: 1rem;">'
        f'<div style="font-size: 2.5rem; font-weight: 700; color: #065F46;">'
        f'${rev_saved/1e6:.1f}M</div>'
        f'<div style="font-size: 1rem; color: #047857;">Projected Revenue Saved</div>'
        f'<div style="font-size: 0.9rem; color: #64748B; margin-top: 0.5rem;">'
        f'By improving OTIF by {otif_improvement}pp, reducing conflict by {conflict_reduction}pp, '
        f'and cutting lead time by {lead_time_reduction}%</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
else:
    st.info("Adjust the sliders above to model improvement scenarios.")
