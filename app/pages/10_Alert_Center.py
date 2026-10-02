import streamlit as st
import pandas as pd
from utils.db import run_query as run, safe_float
from utils.theme import T
from utils.components import page_header, kpi_card, kpi_grid, section, alert_card, footer

page_header("Alert Center", "Threshold-based alerts generated from governed analytics views")

# -- thresholds ----------------------------------------------------------------
st.sidebar.markdown("**Alert thresholds**")
t_conflict = st.sidebar.slider("Conflict rate critical (%)", 10, 90, 50)
t_risk = st.sidebar.slider("Revenue risk critical (%)", 30, 95, 70)
t_otif_low = st.sidebar.slider("OTIF warning below (%)", 10, 80, 40)
t_lead_high = st.sidebar.slider("Lead time warning above (days)", 5, 30, 15)
t_fill_low = st.sidebar.slider("Fill rate warning below (%)", 80, 99, 95)

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

sup_otif_df = run(
    "SELECT SUPPLIER_NAME, SUPPLIER_REGION, "
    "  ROUND(SUM(OTIF_COUNT)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS OTIF "
    "FROM CHAINTRUTH_DB.ANALYTICS.ERP_OTIF "
    "GROUP BY SUPPLIER_NAME, SUPPLIER_REGION ORDER BY OTIF ASC"
)

lt_region = run(
    "SELECT SUPPLIER_REGION, "
    "  ROUND(SUM(AVG_LEAD_TIME_DAYS*TOTAL_SHIPMENTS)/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS AVG_LT "
    "FROM CHAINTRUTH_DB.ANALYTICS.LEAD_TIME_ANALYTICS "
    "GROUP BY SUPPLIER_REGION ORDER BY AVG_LT DESC"
)

# -- build alerts --------------------------------------------------------------
alerts = []

if conflict_rate > t_conflict:
    alerts.append(("danger", "Conflict rate exceeds threshold",
        f"At {conflict_rate:.1f}%, the conflict rate exceeds the {t_conflict}% threshold. "
        f"Teams are reporting fundamentally different OTIF numbers.",
        "Conflict Rate", f"{conflict_rate:.1f}%"))
elif conflict_rate > t_conflict * 0.8:
    alerts.append(("warning", "Conflict rate approaching threshold",
        f"At {conflict_rate:.1f}%, the conflict rate is approaching the {t_conflict}% threshold.",
        "Conflict Rate", f"{conflict_rate:.1f}%"))

if risk_pct > t_risk:
    alerts.append(("danger", "Revenue risk exceeds threshold",
        f"Revenue at risk is {risk_pct:.1f}% (${safe_float(rev['RAR'])/1e6:.1f}M), "
        f"exceeding the {t_risk}% critical threshold.",
        "Revenue Risk", f"{risk_pct:.1f}%"))
elif risk_pct > t_risk * 0.8:
    alerts.append(("warning", "Revenue risk approaching threshold",
        f"Revenue at risk is {risk_pct:.1f}%, approaching the {t_risk}% threshold.",
        "Revenue Risk", f"{risk_pct:.1f}%"))

if erp_otif < t_otif_low:
    alerts.append(("danger", "ERP OTIF below minimum",
        f"Canonical ERP OTIF is {erp_otif:.1f}%, well below the {t_otif_low}% warning threshold.",
        "ERP OTIF", f"{erp_otif:.1f}%"))

if lead_time > t_lead_high:
    alerts.append(("warning", "Lead time above threshold",
        f"Average lead time is {lead_time:.1f} days, above the {t_lead_high}-day threshold.",
        "Lead Time", f"{lead_time:.1f}d"))

if fill_rate < t_fill_low:
    alerts.append(("warning", "Fill rate below threshold",
        f"Fill rate is {fill_rate:.1f}%, below the {t_fill_low}% target.",
        "Fill Rate", f"{fill_rate:.1f}%"))
else:
    alerts.append(("info", "Fill rate healthy",
        f"Fill rate is {fill_rate:.1f}%, above the {t_fill_low}% target.",
        "Fill Rate", f"{fill_rate:.1f}%"))

low_otif_suppliers = sup_otif_df[sup_otif_df["OTIF"] < t_otif_low]
if not low_otif_suppliers.empty:
    count = len(low_otif_suppliers)
    worst = low_otif_suppliers.iloc[0]
    alerts.append(("warning", f"{count} suppliers below OTIF threshold",
        f"{count} suppliers have ERP OTIF below {t_otif_low}%. "
        f"Worst: {worst['SUPPLIER_NAME']} ({worst['SUPPLIER_REGION']}) at {safe_float(worst['OTIF']):.1f}%.",
        "Supplier OTIF", f"{count} suppliers"))

slow_regions = lt_region[lt_region["AVG_LT"] > t_lead_high]
if not slow_regions.empty:
    for _, r in slow_regions.iterrows():
        alerts.append(("info", f"{r['SUPPLIER_REGION']} lead time: {safe_float(r['AVG_LT']):.1f}d",
            f"The {r['SUPPLIER_REGION']} region exceeds the {t_lead_high}-day lead time threshold.",
            "Regional Lead Time", f"{safe_float(r['AVG_LT']):.1f}d"))

# -- render --------------------------------------------------------------------
critical = [a for a in alerts if a[0] == "danger"]
warning = [a for a in alerts if a[0] == "warning"]
info = [a for a in alerts if a[0] == "info"]

kpi_grid([
    kpi_card("Critical", str(len(critical)), status="critical" if critical else "healthy", icon_name="alert"),
    kpi_card("Warning", str(len(warning)), status="warning" if warning else "healthy", icon_name="alert"),
    kpi_card("Informational", str(len(info)), icon_name="shield"),
])

if critical:
    section("Critical alerts")
    for sev, title, detail, metric, value in critical:
        st.markdown(
            alert_card(title, f"<br>{detail}<br><small style='color:{T['text_muted']}'>Metric: {metric} | Value: {value}</small>", "danger"),
            unsafe_allow_html=True,
        )

if warning:
    section("Warnings")
    for sev, title, detail, metric, value in warning:
        st.markdown(
            alert_card(title, f"<br>{detail}<br><small style='color:{T['text_muted']}'>Metric: {metric} | Value: {value}</small>", "warning"),
            unsafe_allow_html=True,
        )

if info:
    section("Informational")
    for sev, title, detail, metric, value in info:
        st.markdown(
            alert_card(title, f"<br>{detail}<br><small style='color:{T['text_muted']}'>Metric: {metric} | Value: {value}</small>", "info"),
            unsafe_allow_html=True,
        )

if not alerts:
    st.success("All metrics within thresholds. No alerts.")

footer()
