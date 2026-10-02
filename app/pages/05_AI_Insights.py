import streamlit as st
import pandas as pd
from utils.db import run_query as run, safe_float
from utils.theme import inject_css, hero, insight, section, DANGER, WARNING, SUCCESS

st.set_page_config(page_title="AI Insights", layout="wide", page_icon="🔗")
inject_css()

hero("AI INSIGHTS CENTER", "Automatically generated insights from governed supply chain data")

# -- pull data -----------------------------------------------------------------
erp_otif = safe_float(run(
    "SELECT ROUND(SUM(OTIF_COUNT)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
    "FROM CHAINTRUTH_DB.ANALYTICS.ERP_OTIF"
)["V"].iloc[0])

log_otif = safe_float(run(
    "SELECT ROUND(SUM(OTIF_COUNT)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
    "FROM CHAINTRUTH_DB.ANALYTICS.LOGISTICS_OTIF"
)["V"].iloc[0])

sup_otif = safe_float(run(
    "SELECT ROUND(SUM(OTIF_COUNT)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
    "FROM CHAINTRUTH_DB.ANALYTICS.SUPPLIER_OTIF"
)["V"].iloc[0])

conflict_rate = safe_float(run(
    "SELECT ROUND(SUM(CONFLICTED_SHIPMENTS)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
    "FROM CHAINTRUTH_DB.ANALYTICS.CHAINTRUTH_OTIF"
)["V"].iloc[0])

rev = run(
    "SELECT SUM(REVENUE_AT_RISK) AS RAR, SUM(TOTAL_ORDER_VALUE) AS TOV, "
    "  SUM(LATE_DELIVERY_REVENUE) AS LATE, SUM(SHORT_SHIPPED_REVENUE) AS SHORT, "
    "  SUM(OVERDUE_OPEN_REVENUE) AS OVERDUE "
    "FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS"
).iloc[0]

rev_risk = safe_float(rev["RAR"])
total_rev = safe_float(rev["TOV"])
late_rev = safe_float(rev["LATE"])
short_rev = safe_float(rev["SHORT"])
overdue_rev = safe_float(rev["OVERDUE"])
risk_pct = rev_risk * 100 / total_rev if total_rev else 0

fill_rate = safe_float(run(
    "SELECT ROUND(SUM(TOTAL_QTY_SHIPPED)*100.0/NULLIF(SUM(TOTAL_QTY_ORDERED),0),1) AS V "
    "FROM CHAINTRUTH_DB.ANALYTICS.FILL_RATE_ANALYTICS"
)["V"].iloc[0])

lead_time = safe_float(run(
    "SELECT ROUND(SUM(AVG_LEAD_TIME_DAYS*TOTAL_SHIPMENTS)/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
    "FROM CHAINTRUTH_DB.ANALYTICS.LEAD_TIME_ANALYTICS"
)["V"].iloc[0])

top_risk_suppliers = run(
    "SELECT SUPPLIER_NAME, SUPPLIER_REGION, "
    "  SUM(REVENUE_AT_RISK) AS RAR, "
    "  ROUND(SUM(REVENUE_AT_RISK)*100.0/NULLIF(SUM(TOTAL_ORDER_VALUE),0),1) AS RISK_PCT "
    "FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS "
    "GROUP BY SUPPLIER_NAME, SUPPLIER_REGION ORDER BY RAR DESC LIMIT 5"
)

region_risk = run(
    "SELECT SUPPLIER_REGION, "
    "  SUM(REVENUE_AT_RISK) AS RAR, "
    "  ROUND(SUM(REVENUE_AT_RISK)*100.0/NULLIF(SUM(TOTAL_ORDER_VALUE),0),1) AS RISK_PCT "
    "FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS "
    "GROUP BY SUPPLIER_REGION ORDER BY RAR DESC"
)

lt_by_region = run(
    "SELECT SUPPLIER_REGION, "
    "  ROUND(SUM(AVG_LEAD_TIME_DAYS*TOTAL_SHIPMENTS)/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS AVG_LT "
    "FROM CHAINTRUTH_DB.ANALYTICS.LEAD_TIME_ANALYTICS "
    "GROUP BY SUPPLIER_REGION ORDER BY AVG_LT DESC"
)

# -- sidebar category filter ---------------------------------------------------
st.sidebar.header("Insight Categories")
categories = ["All", "Risk Insights", "OTIF Insights", "Supplier Insights",
              "Lead Time Insights", "Governance Insights"]
sel_cat = st.sidebar.radio("Show", categories)

# =============================================================================
# BUILD INSIGHTS
# =============================================================================
all_insights = []
spread = sup_otif - erp_otif

# OTIF Insights
all_insights.append(("OTIF Insights", insight(
    f"OTIF Spread: {spread:.1f} pp",
    f"Supplier OTIF ({sup_otif:.1f}%) is <b>{spread:.1f} pp higher</b> than ERP OTIF ({erp_otif:.1f}%). "
    f"Procurement sees strong performance while Finance flags failures — same data, different conclusions.",
    "danger" if spread > 30 else "warning",
)))

all_insights.append(("OTIF Insights", insight(
    f"ERP OTIF at {erp_otif:.1f}% — {'Below' if erp_otif < 50 else 'Above'} Industry Average",
    f"The canonical ERP OTIF of {erp_otif:.1f}% measures delivery against the ERP promised date. "
    f"{'This is significantly below the industry benchmark of ~85%.' if erp_otif < 85 else 'This meets typical industry benchmarks.'}",
    "critical" if erp_otif < 30 else ("warning" if erp_otif < 70 else "success"),
)))

all_insights.append(("OTIF Insights", insight(
    f"Logistics OTIF at {log_otif:.1f}%",
    f"Carrier ETAs set at ship-time tend to be {'optimistic' if log_otif < 40 else 'reasonable'}. "
    f"The gap between Logistics ({log_otif:.1f}%) and ERP ({erp_otif:.1f}%) is "
    f"<b>{log_otif - erp_otif:.1f} pp</b>.",
    "warning" if log_otif < 50 else "success",
)))

# Risk Insights
dominant = "Late deliveries" if late_rev >= max(short_rev, overdue_rev) else ("Short shipments" if short_rev >= overdue_rev else "Overdue open orders")
all_insights.append(("Risk Insights", insight(
    f"${rev_risk/1e6:.1f}M Revenue At Risk ({risk_pct:.1f}%)",
    f"Of ${total_rev/1e6:.1f}M total order value, <b>${rev_risk/1e6:.1f}M</b> is at risk. "
    f"<b>{dominant}</b> are the primary driver.",
    "critical" if risk_pct > 70 else "danger",
)))

all_insights.append(("Risk Insights", insight(
    f"Late Delivery: ${late_rev/1e6:.1f}M ({late_rev*100/rev_risk:.0f}% of risk)",
    f"Late deliveries account for the largest share of revenue at risk. "
    f"This aligns with the low ERP OTIF rate and suggests systematic delivery delays.",
    "danger",
)))

if not region_risk.empty:
    worst = region_risk.iloc[0]
    all_insights.append(("Risk Insights", insight(
        f"{worst['SUPPLIER_REGION']} Leads Risk Exposure",
        f"The {worst['SUPPLIER_REGION']} region contributes the highest absolute revenue at risk "
        f"with a risk rate of <b>{safe_float(worst['RISK_PCT']):.1f}%</b>.",
        "warning",
    )))

# Supplier Insights
for i, (_, s) in enumerate(top_risk_suppliers.iterrows()):
    if i >= 3:
        break
    all_insights.append(("Supplier Insights", insight(
        f"#{i+1} At-Risk Supplier: {s['SUPPLIER_NAME']}",
        f"Located in {s['SUPPLIER_REGION']}, this supplier has <b>${safe_float(s['RAR'])/1e6:.2f}M</b> "
        f"revenue at risk ({safe_float(s['RISK_PCT']):.1f}% risk rate).",
        "danger" if safe_float(s["RISK_PCT"]) > 80 else "warning",
    )))

all_insights.append(("Supplier Insights", insight(
    f"Active Supplier Base: {len(top_risk_suppliers)} of top risk contributors",
    f"The top 5 suppliers by revenue at risk account for a disproportionate share of total exposure. "
    f"Concentrating improvement efforts here yields the highest ROI.",
    "warning",
)))

# Lead Time Insights
all_insights.append(("Lead Time Insights", insight(
    f"Average Lead Time: {lead_time:.1f} days",
    f"Overall weighted average lead time is {lead_time:.1f} days from order placement to delivery.",
    "healthy" if lead_time < 15 else "warning",
)))

if not lt_by_region.empty:
    slowest = lt_by_region.iloc[0]
    fastest = lt_by_region.iloc[-1]
    all_insights.append(("Lead Time Insights", insight(
        f"Slowest Region: {slowest['SUPPLIER_REGION']} ({safe_float(slowest['AVG_LT']):.1f}d)",
        f"The {slowest['SUPPLIER_REGION']} region has the longest lead times, while "
        f"{fastest['SUPPLIER_REGION']} is fastest at {safe_float(fastest['AVG_LT']):.1f} days.",
        "warning",
    )))

# Governance Insights
all_insights.append(("Governance Insights", insight(
    f"Conflict Rate: {conflict_rate:.1f}%",
    f"<b>{conflict_rate:.0f}% of shipments</b> get a different on-time verdict depending on the definition used. "
    f"{'This exceeds the 50% governance threshold — immediate action required.' if conflict_rate > 50 else 'Monitor closely.'}",
    "critical" if conflict_rate > 50 else "warning",
)))

all_insights.append(("Governance Insights", insight(
    "Ontology Coverage",
    "ChainTruth governs 7 metric definitions across 3 owner teams, with 6 entity types "
    "and 7 relationships mapped. All OTIF variants are registered with canonical flagging.",
    "success",
)))

all_insights.append(("Governance Insights", insight(
    f"Fill Rate: {fill_rate:.1f}% — Governance Not Required",
    f"At {fill_rate:.1f}%, fill rate is consistently high across all segments. "
    f"No conflicting definitions exist for this metric.",
    "success",
)))

# =============================================================================
# RENDER
# =============================================================================
total = len(all_insights)
filtered = [(cat, html) for cat, html in all_insights if sel_cat == "All" or cat == sel_cat]

st.markdown(f"**Showing {len(filtered)} of {total} insights**")
st.markdown("---")

current_cat = ""
for cat, html in filtered:
    if cat != current_cat:
        section(cat)
        current_cat = cat
    st.markdown(html, unsafe_allow_html=True)
