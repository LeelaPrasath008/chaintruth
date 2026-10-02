import streamlit as st
import pandas as pd
from utils.db import run_query
from utils.theme import T
from utils.components import page_header, section, kpi_card, kpi_grid, insight, footer, enhanced_table, render_lineage_flow
from utils.tour import render_tour_banner

page_header("Business Glossary", "Governed metric definitions from the ontology metric registry")
render_tour_banner()

st.markdown(
    insight(
        "Why this matters",
        "In any supply chain, the same metric can be defined differently by different teams. "
        "Finance measures OTIF against the ERP promised date. Logistics measures against the carrier ETA. "
        "Procurement measures against the supplier's own commitment. The <b>Metric Registry</b> records "
        "every definition explicitly — its SQL formula, its owner, and whether it is the <b>canonical</b> "
        "definition used for executive reporting.",
    ),
    unsafe_allow_html=True,
)

df = run_query(
    "SELECT METRIC_ID, METRIC_NAME, METRIC_VARIANT, DESCRIPTION, "
    "  METRIC_SQL, UNIT, DIRECTION, OWNER_TEAM, SOURCE_TABLES, "
    "  SOURCE_COLUMNS, IS_CANONICAL "
    "FROM CHAINTRUTH_DB.ONTOLOGY.METRIC_REGISTRY "
    "ORDER BY METRIC_NAME, IS_CANONICAL DESC"
)

df["IS_CANONICAL"] = df["IS_CANONICAL"].apply(
    lambda v: bool(v) if isinstance(v, bool) else str(v).lower() == "true"
)

canonical_count = int(df["IS_CANONICAL"].sum())
total_count = len(df)
owner_count = df["OWNER_TEAM"].nunique()

section("Summary")
kpi_grid([
    kpi_card("Total Metrics", str(total_count), icon_name="book"),
    kpi_card("Canonical Definitions", str(canonical_count), icon_name="shield"),
    kpi_card("Owner Teams", str(owner_count), icon_name="users"),
])

section("Metric Definitions")
display = df.copy()
display["CANONICAL"] = display["IS_CANONICAL"].map({True: "Yes", False: ""})
display["DIRECTION"] = display["DIRECTION"].str.replace("_", " ").str.title()

enhanced_table(
    display[["METRIC_ID", "METRIC_NAME", "METRIC_VARIANT", "OWNER_TEAM",
             "UNIT", "DIRECTION", "CANONICAL", "DESCRIPTION"]].rename(columns={
        "METRIC_ID": "ID", "METRIC_NAME": "Metric", "METRIC_VARIANT": "Variant",
        "OWNER_TEAM": "Owner", "UNIT": "Unit", "DIRECTION": "Direction",
        "CANONICAL": "Canonical", "DESCRIPTION": "Description",
    }),
    key="glossary_metrics", height=320,
)

section("Metric Details")
for _, row in df.iterrows():
    label = row["METRIC_NAME"]
    if pd.notna(row["METRIC_VARIANT"]) and row["METRIC_VARIANT"]:
        label += f" -- {row['METRIC_VARIANT']}"
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

footer()
