import streamlit as st
import pandas as pd
from utils.db import run_query as run, safe_float
from utils.theme import inject_css, hero, section

st.set_page_config(page_title="Alert Center", layout="wide", page_icon="🔗")
inject_css()

hero("ALERT CENTER", "Threshold-based alerts generated from governed analytics views")

# -- thresholds ----------------------------------------------------------------
st.sidebar.header("Alert Thresholds")
t_conflict = st.sidebar.slider("Conflict Rate Critical (%)", 10, 90, 50)
t_risk = st.sidebar.slider("Revenue Risk Critical (%)", 30, 95, 70)
t_otif_low = st.sidebar.slider("OTIF Warning Below (%)", 10, 80, 40)
t_lead_high = st.sidebar.slider("Lead Time Warning Above (days)", 5, 30, 15)
t_fill_low = st.sidebar.slider("Fill Rate Warning Below (%)", 80, 99, 95)

# -- gather data ---------------------------------------------------------------
erp_otif = safe_float(run(
    "SELECT ROUND(SUM(OTIF_COUNT)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
    "FROM CHAINTRUTH_DB.ANALYTICS.ERP_OTIF"
)["V"].iloc[0])

conflict_rate = safe_float(run(
    "SELECT ROUND(SUM(CONFLICTED_SHIPMENTS)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
    "FROM CHAINTRUTH_DB.ANALYTICS.CHAINTRUTH_OTIF"
)["V"].iloc[0])

rev = run(
    "SELECT SUM(REVENUE_AT_RISK) AS RAR, SUM(TOTAL_ORDER_VALUE) AS TOV "
    "FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS"
).iloc[0]
risk_pct = safe_float(rev["RAR"]) * 100 / safe_float(rev["TOV"]) if safe_float(rev["TOV"]) else 0

fill_rate = safe_float(run(
    "SELECT ROUND(SUM(TOTAL_QTY_SHIPPED)*100.0/NULLIF(SUM(TOTAL_QTY_ORDERED),0),1) AS V "
    "FROM CHAINTRUTH_DB.ANALYTICS.FILL_RATE_ANALYTICS"
)["V"].iloc[0])

lead_time = safe_float(run(
    "SELECT ROUND(SUM(AVG_LEAD_TIME_DAYS*TOTAL_SHIPMENTS)/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
    "FROM CHAINTRUTH_DB.ANALYTICS.LEAD_TIME_ANALYTICS"
)["V"].iloc[0])

# per-supplier OTIF
sup_otif_df = run(
    "SELECT SUPPLIER_NAME, SUPPLIER_REGION, "
    "  ROUND(SUM(OTIF_COUNT)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS OTIF "
    "FROM CHAINTRUTH_DB.ANALYTICS.ERP_OTIF "
    "GROUP BY SUPPLIER_NAME, SUPPLIER_REGION ORDER BY OTIF ASC"
)

# per-region lead time
lt_region = run(
    "SELECT SUPPLIER_REGION, "
    "  ROUND(SUM(AVG_LEAD_TIME_DAYS*TOTAL_SHIPMENTS)/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS AVG_LT "
    "FROM CHAINTRUTH_DB.ANALYTICS.LEAD_TIME_ANALYTICS "
    "GROUP BY SUPPLIER_REGION ORDER BY AVG_LT DESC"
)

# =============================================================================
# BUILD ALERTS
# =============================================================================
alerts = []  # (severity, title, detail, metric, value)

# Conflict rate
if conflict_rate > t_conflict:
    alerts.append(("critical", "Conflict Rate Exceeds Threshold",
        f"At {conflict_rate:.1f}%, the conflict rate exceeds the {t_conflict}% threshold. "
        f"Teams are reporting fundamentally different OTIF numbers.",
        "Conflict Rate", f"{conflict_rate:.1f}%"))
elif conflict_rate > t_conflict * 0.8:
    alerts.append(("warning", "Conflict Rate Approaching Threshold",
        f"At {conflict_rate:.1f}%, the conflict rate is approaching the {t_conflict}% threshold.",
        "Conflict Rate", f"{conflict_rate:.1f}%"))

# Revenue risk
if risk_pct > t_risk:
    alerts.append(("critical", "Revenue Risk Exceeds Threshold",
        f"Revenue at risk is {risk_pct:.1f}% (${safe_float(rev['RAR'])/1e6:.1f}M), "
        f"exceeding the {t_risk}% critical threshold.",
        "Revenue Risk", f"{risk_pct:.1f}%"))
elif risk_pct > t_risk * 0.8:
    alerts.append(("warning", "Revenue Risk Approaching Threshold",
        f"Revenue at risk is {risk_pct:.1f}%, approaching the {t_risk}% threshold.",
        "Revenue Risk", f"{risk_pct:.1f}%"))

# ERP OTIF
if erp_otif < t_otif_low:
    alerts.append(("critical", "ERP OTIF Below Minimum",
        f"Canonical ERP OTIF is {erp_otif:.1f}%, well below the {t_otif_low}% warning threshold.",
        "ERP OTIF", f"{erp_otif:.1f}%"))

# Lead time
if lead_time > t_lead_high:
    alerts.append(("warning", "Lead Time Above Threshold",
        f"Average lead time is {lead_time:.1f} days, above the {t_lead_high}-day threshold.",
        "Lead Time", f"{lead_time:.1f}d"))

# Fill rate
if fill_rate < t_fill_low:
    alerts.append(("warning", "Fill Rate Below Threshold",
        f"Fill rate is {fill_rate:.1f}%, below the {t_fill_low}% target.",
        "Fill Rate", f"{fill_rate:.1f}%"))
else:
    alerts.append(("info", "Fill Rate Healthy",
        f"Fill rate is {fill_rate:.1f}%, above the {t_fill_low}% target.",
        "Fill Rate", f"{fill_rate:.1f}%"))

# Per-supplier OTIF alerts
low_otif_suppliers = sup_otif_df[sup_otif_df["OTIF"] < t_otif_low]
if not low_otif_suppliers.empty:
    count = len(low_otif_suppliers)
    worst = low_otif_suppliers.iloc[0]
    alerts.append(("warning", f"{count} Suppliers Below OTIF Threshold",
        f"{count} suppliers have ERP OTIF below {t_otif_low}%. "
        f"Worst: {worst['SUPPLIER_NAME']} ({worst['SUPPLIER_REGION']}) at {safe_float(worst['OTIF']):.1f}%.",
        "Supplier OTIF", f"{count} suppliers"))

# Per-region lead time
slow_regions = lt_region[lt_region["AVG_LT"] > t_lead_high]
if not slow_regions.empty:
    for _, r in slow_regions.iterrows():
        alerts.append(("info", f"{r['SUPPLIER_REGION']} Lead Time: {safe_float(r['AVG_LT']):.1f}d",
            f"The {r['SUPPLIER_REGION']} region exceeds the {t_lead_high}-day lead time threshold.",
            "Regional Lead Time", f"{safe_float(r['AVG_LT']):.1f}d"))

# =============================================================================
# RENDER ALERTS
# =============================================================================
critical = [a for a in alerts if a[0] == "critical"]
warning = [a for a in alerts if a[0] == "warning"]
info = [a for a in alerts if a[0] == "info"]

c1, c2, c3 = st.columns(3)
c1.metric("🔴 Critical", len(critical))
c2.metric("🟡 Warning", len(warning))
c3.metric("🔵 Info", len(info))

st.markdown("---")

def render_alert(severity, title, detail, metric, value):
    css_class = f"alert-{severity}"
    icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}[severity]
    st.markdown(
        f'<div class="{css_class}">'
        f'<strong>{icon} {title}</strong><br>'
        f'<span style="font-size:0.9rem">{detail}</span><br>'
        f'<span style="font-size:0.8rem; color:#64748B">Metric: {metric} | Value: {value}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

if critical:
    section("Critical Alerts")
    for a in critical:
        render_alert(*a)

if warning:
    section("Warnings")
    for a in warning:
        render_alert(*a)

if info:
    section("Informational")
    for a in info:
        render_alert(*a)

if not alerts:
    st.success("All metrics within thresholds. No alerts.")
