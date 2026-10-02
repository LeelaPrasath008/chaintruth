import streamlit as st
import pandas as pd
from utils.db import run_query

st.set_page_config(page_title="Business Glossary", layout="wide")
st.title("Business Glossary")
st.caption("Governed metric definitions from ONTOLOGY.METRIC_REGISTRY")

st.markdown(
    "In any supply chain, the same metric can be defined differently by different "
    "teams. Finance measures OTIF against the ERP promised date. Logistics measures "
    "against the carrier ETA. Procurement measures against the supplier's own "
    "commitment. All three are valid within their context, but when reported side "
    "by side without governance, they create confusion: the same shipment appears "
    "\"on time\" to one team and \"late\" to another.\n\n"
    "The **Metric Registry** solves this by recording every definition explicitly "
    "— its SQL formula, its owner, and whether it is the **canonical** definition "
    "used for executive reporting and Revenue At Risk calculations. "
    "When stakeholders disagree on a number, the registry provides a single source "
    "of truth about *what was measured and by whom*."
)

st.markdown("---")

df = run_query(
    "SELECT METRIC_ID, METRIC_NAME, METRIC_VARIANT, DESCRIPTION, "
    "  METRIC_SQL, UNIT, DIRECTION, OWNER_TEAM, SOURCE_TABLES, "
    "  SOURCE_COLUMNS, IS_CANONICAL "
    "FROM CHAINTRUTH_DB.ONTOLOGY.METRIC_REGISTRY "
    "ORDER BY METRIC_NAME, IS_CANONICAL DESC"
)

# -- ensure IS_CANONICAL is proper bool (Snowflake may return string) ----------
df["IS_CANONICAL"] = df["IS_CANONICAL"].apply(
    lambda v: bool(v) if isinstance(v, bool) else str(v).lower() == "true"
)

# -- summary cards -------------------------------------------------------------
canonical_count = int(df["IS_CANONICAL"].sum())
total_count = len(df)
owner_count = df["OWNER_TEAM"].nunique()

c1, c2, c3 = st.columns(3)
c1.metric("Total Metrics", total_count)
c2.metric("Canonical Definitions", canonical_count)
c3.metric("Owner Teams", owner_count)

st.markdown("---")

# -- metric table --------------------------------------------------------------
st.subheader("Metric Definitions")

display = df.copy()
display["CANONICAL"] = display["IS_CANONICAL"].map({True: "Yes", False: ""})
display["DIRECTION"] = display["DIRECTION"].str.replace("_", " ").str.title()

st.dataframe(
    display[["METRIC_ID", "METRIC_NAME", "METRIC_VARIANT", "OWNER_TEAM",
             "UNIT", "DIRECTION", "CANONICAL", "DESCRIPTION"]].rename(columns={
        "METRIC_ID": "ID",
        "METRIC_NAME": "Metric",
        "METRIC_VARIANT": "Variant",
        "OWNER_TEAM": "Owner",
        "UNIT": "Unit",
        "DIRECTION": "Direction",
        "CANONICAL": "Canonical",
        "DESCRIPTION": "Description",
    }),
    use_container_width=True,
    hide_index=True,
    height=320,
)

# -- expandable detail per metric ----------------------------------------------
st.markdown("---")
st.subheader("Metric Details")

for _, row in df.iterrows():
    label = row["METRIC_NAME"]
    if pd.notna(row["METRIC_VARIANT"]) and row["METRIC_VARIANT"]:
        label += f" — {row['METRIC_VARIANT']}"
    if row["IS_CANONICAL"]:
        label += "  (Canonical)"

    with st.expander(label):
        col_l, col_r = st.columns(2)
        col_l.markdown(f"**Owner:** {row['OWNER_TEAM']}")
        col_r.markdown(f"**Unit:** {row['UNIT']}  |  **Direction:** {row['DIRECTION']}")
        st.markdown(f"**Description:** {row['DESCRIPTION']}")
        st.code(row["METRIC_SQL"], language="sql")
        st.markdown(
            f"**Source tables:** `{row['SOURCE_TABLES']}`  \n"
            f"**Source columns:** `{row['SOURCE_COLUMNS']}`"
        )
