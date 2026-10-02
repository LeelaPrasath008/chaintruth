import streamlit as st
import pandas as pd
import re
from utils.db import run_query as run, safe_float
from utils.theme import T
from utils.components import page_header, section, footer, typing_indicator
from utils.tour import render_tour_banner

page_header("Ask ChainTruth", "AI-powered supply chain intelligence grounded in governed analytics views")
render_tour_banner()

# -- quick action buttons ------------------------------------------------------
st.sidebar.markdown("**Quick actions**")
SUGGESTIONS = [
    ("What is OTIF?", "What is OTIF?"),
    ("Compare OTIF definitions", "Why are OTIF definitions different?"),
    ("Top suppliers at risk", "Which suppliers have the highest revenue at risk?"),
    ("Explain conflict rate", "What is the conflict rate?"),
    ("Current fill rate", "What is the fill rate?"),
    ("Delivery lead time", "How long does delivery take?"),
    ("ERP OTIF rate", "What is the current ERP OTIF?"),
]
for label, q in SUGGESTIONS:
    if st.sidebar.button(label, key=f"sq_{q}", use_container_width=True):
        st.session_state["_prefill"] = q

# -- intent detection (UNCHANGED) ---------------------------------------------

INTENTS = [
    ("revenue_at_risk_top",    [r"top.+supplier.+revenue", r"highest.+revenue.+risk",
                                r"supplier.+highest.+risk", r"top.+risk",
                                r"revenue.+risk.+supplier", r"worst.+supplier"]),
    ("revenue_at_risk_total",  [r"total.+revenue.+risk", r"how much.+risk",
                                r"revenue.+at.+risk$", r"^revenue.+risk"]),
    ("erp_otif",               [r"erp.+otif", r"otif.+erp", r"current.+erp",
                                r"what.+erp.+otif"]),
    ("logistics_otif",         [r"logistics.+otif", r"otif.+logistics",
                                r"carrier.+otif"]),
    ("supplier_otif",          [r"supplier.+otif", r"otif.+supplier",
                                r"procurement.+otif"]),
    ("otif_compare",           [r"compare.+otif", r"otif.+compar",
                                r"all.+otif", r"three.+otif", r"otif.+definition",
                                r"different.+otif", r"why.+otif.+different",
                                r"why.+different", r"conflict"]),
    ("fill_rate",              [r"fill.+rate", r"fulfillment.+rate",
                                r"quantity.+shipped", r"shortfall"]),
    ("lead_time",              [r"lead.+time", r"delivery.+time",
                                r"how.+long", r"days.+deliver"]),
    ("otif_explain",           [r"what.+is.+otif", r"explain.+otif",
                                r"define.+otif", r"otif.+mean"]),
]

COMPILED = [
    (name, [re.compile(p, re.IGNORECASE) for p in patterns])
    for name, patterns in INTENTS
]


def detect_intent(text: str) -> str:
    for name, patterns in COMPILED:
        if any(p.search(text) for p in patterns):
            return name
    return "unknown"


# -- handlers (ALL UNCHANGED) --------------------------------------------------

def handle_revenue_at_risk_top(_q: str) -> str:
    df = run(
        "SELECT SUPPLIER_ID, SUPPLIER_NAME, SUPPLIER_COUNTRY, SUPPLIER_REGION, "
        "  SUM(REVENUE_AT_RISK) AS REVENUE_AT_RISK, "
        "  SUM(TOTAL_ORDER_VALUE) AS TOTAL_ORDER_VALUE, "
        "  ROUND(SUM(REVENUE_AT_RISK)*100.0/NULLIF(SUM(TOTAL_ORDER_VALUE),0),1) AS RISK_PCT, "
        "  SUM(LATE_DELIVERY_ORDERS) AS LATE, "
        "  SUM(SHORT_SHIPPED_ORDERS) AS SHORT, "
        "  SUM(OVERDUE_OPEN_ORDERS) AS OVERDUE "
        "FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS "
        "GROUP BY SUPPLIER_ID, SUPPLIER_NAME, SUPPLIER_COUNTRY, SUPPLIER_REGION "
        "ORDER BY REVENUE_AT_RISK DESC LIMIT 10"
    )
    total = float(df["REVENUE_AT_RISK"].sum())
    lines = ["**Top 10 Suppliers by Revenue At Risk**\n"]
    lines.append(f"Combined revenue at risk: **${total/1e6:.1f}M**\n")
    lines.append("| Rank | Supplier | Country | Revenue At Risk | Risk % | Late | Short | Overdue |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for i, r in df.iterrows():
        lines.append(
            f"| {i+1} | {r['SUPPLIER_NAME']} | {r['SUPPLIER_COUNTRY']} | "
            f"${float(r['REVENUE_AT_RISK'])/1e6:.2f}M | {float(r['RISK_PCT']):.1f}% | "
            f"{int(r['LATE'])} | {int(r['SHORT'])} | {int(r['OVERDUE'])} |"
        )
    lines.append("\n*Late deliveries are the dominant risk driver across all top suppliers.*")
    return "\n".join(lines)


def handle_revenue_at_risk_total(_q: str) -> str:
    df = run(
        "SELECT SUM(REVENUE_AT_RISK) AS RAR, SUM(TOTAL_ORDER_VALUE) AS TOV, "
        "  ROUND(SUM(REVENUE_AT_RISK)*100.0/NULLIF(SUM(TOTAL_ORDER_VALUE),0),1) AS PCT, "
        "  SUM(AT_RISK_ORDERS) AS ORD, SUM(TOTAL_ORDERS) AS TOTAL_ORD "
        "FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS"
    )
    r = df.iloc[0]
    rar, tov, pct = safe_float(r['RAR']), safe_float(r['TOV']), safe_float(r['PCT'])
    ord_cnt, total_ord = int(safe_float(r['ORD'])), int(safe_float(r['TOTAL_ORD']))
    return (
        f"**Total Revenue At Risk: ${rar/1e6:.1f}M** "
        f"out of ${tov/1e6:.1f}M total order value ({pct:.1f}%).\n\n"
        f"{ord_cnt:,} of {total_ord:,} orders are at risk "
        f"(late delivery, short-shipped, or overdue-open).\n\n"
        f"This uses the **canonical ERP OTIF definition** "
        f"(delivery on or before the ERP promised date)."
    )


def handle_erp_otif(_q: str) -> str:
    df = run(
        "SELECT ROUND(SUM(OTIF_COUNT)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),2) AS RATE, "
        "  SUM(OTIF_COUNT) AS PASS, SUM(TOTAL_SHIPMENTS) AS TOTAL "
        "FROM CHAINTRUTH_DB.ANALYTICS.ERP_OTIF"
    )
    r = df.iloc[0]
    rate, passed, total = safe_float(r['RATE']), int(safe_float(r['PASS'])), int(safe_float(r['TOTAL']))
    return (
        f"**ERP OTIF Rate: {rate:.1f}%**\n\n"
        f"{passed:,} of {total:,} delivered shipments met both conditions:\n"
        f"- Delivered on or before the **ERP promised date**\n"
        f"- Shipped the **full ordered quantity**\n\n"
        f"This is the **strictest** of the three OTIF definitions because "
        f"ERP promises are set early with tight buffers."
    )


def handle_logistics_otif(_q: str) -> str:
    df = run(
        "SELECT ROUND(SUM(OTIF_COUNT)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),2) AS RATE, "
        "  SUM(OTIF_COUNT) AS PASS, SUM(TOTAL_SHIPMENTS) AS TOTAL "
        "FROM CHAINTRUTH_DB.ANALYTICS.LOGISTICS_OTIF"
    )
    r = df.iloc[0]
    rate, passed, total = safe_float(r['RATE']), int(safe_float(r['PASS'])), int(safe_float(r['TOTAL']))
    return (
        f"**Logistics OTIF Rate: {rate:.1f}%**\n\n"
        f"{passed:,} of {total:,} delivered shipments met both conditions:\n"
        f"- Delivered on or before the **carrier ETA**\n"
        f"- Shipped the **full ordered quantity**\n\n"
        f"The carrier ETA is set at ship-time and is often optimistic, "
        f"so this rate can be lower than expected."
    )


def handle_supplier_otif(_q: str) -> str:
    df = run(
        "SELECT ROUND(SUM(OTIF_COUNT)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),2) AS RATE, "
        "  SUM(OTIF_COUNT) AS PASS, SUM(TOTAL_SHIPMENTS) AS TOTAL "
        "FROM CHAINTRUTH_DB.ANALYTICS.SUPPLIER_OTIF"
    )
    r = df.iloc[0]
    rate, passed, total = safe_float(r['RATE']), int(safe_float(r['PASS'])), int(safe_float(r['TOTAL']))
    return (
        f"**Supplier OTIF Rate: {rate:.1f}%**\n\n"
        f"{passed:,} of {total:,} shipments met both conditions:\n"
        f"- Shipped on or before the **supplier commitment date**\n"
        f"- Shipped the **full ordered quantity**\n\n"
        f"This is the **most generous** definition because suppliers pad their commitments. "
        f"It measures dispatch timeliness, not delivery."
    )


def handle_otif_compare(_q: str) -> str:
    erp = safe_float(run(
        "SELECT ROUND(SUM(OTIF_COUNT)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
        "FROM CHAINTRUTH_DB.ANALYTICS.ERP_OTIF"
    )["V"].iloc[0])
    log = safe_float(run(
        "SELECT ROUND(SUM(OTIF_COUNT)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
        "FROM CHAINTRUTH_DB.ANALYTICS.LOGISTICS_OTIF"
    )["V"].iloc[0])
    sup = safe_float(run(
        "SELECT ROUND(SUM(OTIF_COUNT)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
        "FROM CHAINTRUTH_DB.ANALYTICS.SUPPLIER_OTIF"
    )["V"].iloc[0])
    conflict = safe_float(run(
        "SELECT ROUND(SUM(CONFLICTED_SHIPMENTS)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
        "FROM CHAINTRUTH_DB.ANALYTICS.CHAINTRUTH_OTIF"
    )["V"].iloc[0])
    return (
        "**Three teams, three OTIF numbers, one dataset.**\n\n"
        "| Definition | Rate | Measured By | Date Compared |\n"
        "|---|---|---|---|\n"
        f"| ERP (Canonical) | **{erp}%** | Finance | delivery vs. ERP promised date |\n"
        f"| Logistics | **{log}%** | Logistics | delivery vs. carrier ETA |\n"
        f"| Supplier | **{sup}%** | Procurement | ship date vs. supplier commitment |\n\n"
        "**Why they differ:**\n"
        "- **ERP** uses the tightest deadline set at order time with minimal buffer.\n"
        "- **Logistics** uses the carrier's ETA set at ship-time, which is often optimistic.\n"
        "- **Supplier** uses the supplier's own commitment date, which is the most padded.\n"
        "- Supplier measures *ship* date (what they control), not *delivery* date.\n\n"
        f"**Conflict rate: {conflict}%** of shipments get a different on-time verdict "
        f"depending on which definition you use.\n\n"
        "*ChainTruth uses the ERP definition as canonical because it reflects "
        "the promise made to the customer.*"
    )


def handle_fill_rate(_q: str) -> str:
    df = run(
        "SELECT ROUND(SUM(TOTAL_QTY_SHIPPED)*100.0/NULLIF(SUM(TOTAL_QTY_ORDERED),0),2) AS RATE, "
        "  SUM(TOTAL_QTY_ORDERED) AS ORD, SUM(TOTAL_QTY_SHIPPED) AS SHIP, "
        "  ROUND(SUM(IS_FULLY_FILLED)*100.0/NULLIF(SUM(TOTAL_ORDERS),0),1) AS PERFECT "
        "FROM CHAINTRUTH_DB.ANALYTICS.FILL_RATE_ANALYTICS"
    )
    r = df.iloc[0]
    rate = safe_float(r['RATE'])
    ord_qty, ship_qty = int(safe_float(r['ORD'])), int(safe_float(r['SHIP']))
    perfect = safe_float(r['PERFECT'])
    return (
        f"**Fill Rate: {rate:.1f}%**\n\n"
        f"- {ship_qty:,} units shipped of {ord_qty:,} ordered\n"
        f"- Perfect order rate (100% of quantity shipped): **{perfect:.1f}%**\n\n"
        f"Fill rate measures inventory availability — what percentage of "
        f"ordered quantity was actually shipped."
    )


def handle_lead_time(_q: str) -> str:
    summary = run(
        "SELECT ROUND(SUM(AVG_LEAD_TIME_DAYS*TOTAL_SHIPMENTS)/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS AVG_LT, "
        "  MIN(MIN_LEAD_TIME_DAYS) AS MIN_LT, MAX(MAX_LEAD_TIME_DAYS) AS MAX_LT "
        "FROM CHAINTRUTH_DB.ANALYTICS.LEAD_TIME_ANALYTICS"
    ).iloc[0]
    avg_lt = safe_float(summary['AVG_LT'])
    min_lt, max_lt = int(safe_float(summary['MIN_LT'])), int(safe_float(summary['MAX_LT']))
    by_region = run(
        "SELECT SUPPLIER_REGION, "
        "  ROUND(SUM(AVG_LEAD_TIME_DAYS*TOTAL_SHIPMENTS)/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS AVG_LT "
        "FROM CHAINTRUTH_DB.ANALYTICS.LEAD_TIME_ANALYTICS "
        "GROUP BY SUPPLIER_REGION ORDER BY AVG_LT DESC"
    )
    lines = [
        f"**Average Lead Time: {avg_lt:.1f} days**\n",
        f"Range: {min_lt} to {max_lt} days\n",
        "**By Supplier Region:**\n",
        "| Region | Avg Lead Time |",
        "|---|---|",
    ]
    for _, r in by_region.iterrows():
        lines.append(f"| {r['SUPPLIER_REGION']} | {float(r['AVG_LT']):.1f} days |")
    lines.append("\n*Lead time = days from order placement to actual delivery.*")
    return "\n".join(lines)


def handle_otif_explain(_q: str) -> str:
    return (
        "**OTIF (On-Time In-Full)** is the gold-standard fulfillment KPI.\n\n"
        "A shipment is OTIF when **both** conditions are met:\n"
        "1. **On-Time** — delivered by the agreed date\n"
        "2. **In-Full** — the complete ordered quantity was shipped\n\n"
        "ChainTruth tracks **three competing definitions** because different "
        "teams use different \"agreed dates\":\n\n"
        "| Team | Date Used | Typical Strictness |\n"
        "|---|---|---|\n"
        "| Finance (ERP) | ERP promised delivery date | Strictest |\n"
        "| Logistics | Carrier ETA at ship-time | Medium |\n"
        "| Procurement | Supplier commitment date | Most lenient |\n\n"
        "The **conflict rate** measures how often these three definitions "
        "disagree on whether the same shipment was on-time. A high conflict "
        "rate means teams are reporting different performance numbers from "
        "identical data — the core problem ChainTruth solves."
    )


HANDLERS = {
    "revenue_at_risk_top":   handle_revenue_at_risk_top,
    "revenue_at_risk_total": handle_revenue_at_risk_total,
    "erp_otif":              handle_erp_otif,
    "logistics_otif":        handle_logistics_otif,
    "supplier_otif":         handle_supplier_otif,
    "otif_compare":          handle_otif_compare,
    "fill_rate":             handle_fill_rate,
    "lead_time":             handle_lead_time,
    "otif_explain":          handle_otif_explain,
}


def handle_unknown(_q: str) -> str:
    return (
        "I can answer questions about:\n\n"
        "- **OTIF rates** — ERP, Logistics, Supplier, or comparison\n"
        "- **Revenue at risk** — total or by supplier\n"
        "- **Fill rate** and **lead time**\n"
        "- **Conflict rate** between OTIF definitions\n"
        "- **What is OTIF?** — definitions and why they differ\n\n"
        "Try asking:\n"
        "- *Which suppliers have the highest revenue at risk?*\n"
        "- *What is the current ERP OTIF?*\n"
        "- *Why are OTIF definitions different?*\n"
        "- *What is the fill rate?*\n"
        "- *How long does delivery take?*"
    )


# -- chat UI -------------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": (
            "Welcome to **Ask ChainTruth**. I can answer questions about "
            "OTIF performance, revenue at risk, fill rates, lead times, "
            "and the conflict between competing metric definitions.\n\n"
            "What would you like to know?"
        )}
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := (st.session_state.pop("_prefill", None) or st.chat_input("Ask a supply-chain question...")):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        ph = st.empty()
        with ph.container():
            typing_indicator()
        intent = detect_intent(prompt)
        handler = HANDLERS.get(intent, handle_unknown)
        response = handler(prompt)
        ph.empty()
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})

    # Track query history
    if "ct_ui_history" not in st.session_state:
        st.session_state["ct_ui_history"] = []
    st.session_state["ct_ui_history"].insert(0, prompt)
