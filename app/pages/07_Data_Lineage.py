import streamlit as st
from utils.db import run_query as run, safe_float
from utils.theme import inject_css, hero, section

st.set_page_config(page_title="Data Lineage", layout="wide", page_icon="🔗")
inject_css()

hero("DATA LINEAGE EXPLORER", "Trace data from raw ingestion through ontology governance to analytics and dashboard")

# =============================================================================
# LINEAGE DIAGRAM
# =============================================================================
section("End-to-End Data Flow")

st.markdown("""
```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CHAINTRUTH DATA LINEAGE                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────────┐ │
│   │  RAW     │    │ ONTOLOGY │    │ ANALYTICS│    │   DASHBOARD      │ │
│   │  TABLES  │───▶│  LAYER   │───▶│  VIEWS   │───▶│   & PAGES        │ │
│   │ (Bronze) │    │ (Silver) │    │  (Gold)  │    │  (Presentation)  │ │
│   └──────────┘    └──────────┘    └──────────┘    └──────────────────┘ │
│                                                                         │
│   6 tables         3 tables        7 views         12 pages             │
│   50 suppliers     6 entities      3 OTIF defs     Executive Dashboard  │
│   5000 orders      7 relations     Risk analytics   Ask ChainTruth      │
│   5031 shipments   7 metrics       Lead time        What-If Simulator   │
│                                    Fill rate                             │
│                                    Revenue risk                          │
└─────────────────────────────────────────────────────────────────────────┘
```
""")

# =============================================================================
# RAW LAYER
# =============================================================================
section("Bronze Layer — RAW Tables")
st.caption("Source-of-truth tables loaded from synthetic data generation")

raw_tables = run(
    "SELECT TABLE_NAME, ROW_COUNT, BYTES "
    "FROM CHAINTRUTH_DB.INFORMATION_SCHEMA.TABLES "
    "WHERE TABLE_SCHEMA = 'RAW' AND TABLE_TYPE = 'BASE TABLE' "
    "ORDER BY TABLE_NAME"
)

cols = st.columns(3)
table_info = {
    "CUSTOMERS": ("👤", "Customer master data with segments (Enterprise, Mid-Market, SMB, Government, Startup)"),
    "ORDERS": ("📋", "5000 orders with three date fields: PROMISED_DELIVERY_DATE, SUPPLIER_COMMITMENT_DATE, and ORDER_DATE"),
    "PARTS": ("⚙️", "200 parts across 5 categories (Electronics, Mechanical, Chemical, Raw Material, Packaging)"),
    "PLANTS": ("🏭", "10 manufacturing plants across 5 global regions"),
    "SHIPMENTS": ("🚛", "~5031 shipments including split shipments for complex orders"),
    "SUPPLIERS": ("🏢", "50 suppliers with reliability scores (0.5-0.95) across global regions"),
}

for i, (_, row) in enumerate(raw_tables.iterrows()):
    name = row["TABLE_NAME"]
    icon, desc = table_info.get(name, ("📊", ""))
    rows = int(safe_float(row["ROW_COUNT"]))
    with cols[i % 3]:
        with st.expander(f"{icon} {name} ({rows:,} rows)"):
            st.markdown(desc)
            cols_df = run(
                f"SELECT COLUMN_NAME, DATA_TYPE "
                f"FROM CHAINTRUTH_DB.INFORMATION_SCHEMA.COLUMNS "
                f"WHERE TABLE_SCHEMA = 'RAW' AND TABLE_NAME = '{name}' "
                f"ORDER BY ORDINAL_POSITION"
            )
            st.dataframe(cols_df, hide_index=True, use_container_width=True)

# =============================================================================
# ONTOLOGY LAYER
# =============================================================================
st.markdown("---")
section("Silver Layer — ONTOLOGY Tables")
st.caption("Governance layer defining entities, relationships, and metric definitions")

ont_col1, ont_col2, ont_col3 = st.columns(3)

with ont_col1:
    entities = run("SELECT ENTITY_NAME, DESCRIPTION, SOURCE_TABLE FROM CHAINTRUTH_DB.ONTOLOGY.ENTITY_TYPE")
    with st.expander(f"🔷 ENTITY_TYPE ({len(entities)} records)"):
        st.markdown("Defines the core supply chain objects tracked by the platform.")
        st.dataframe(entities, hide_index=True, use_container_width=True)

with ont_col2:
    rels = run("SELECT RELATIONSHIP_NAME, FROM_ENTITY_TYPE_ID, TO_ENTITY_TYPE_ID, CARDINALITY FROM CHAINTRUTH_DB.ONTOLOGY.RELATIONSHIP_TYPE")
    with st.expander(f"🔗 RELATIONSHIP_TYPE ({len(rels)} records)"):
        st.markdown("Directed edges connecting entities in the supply chain graph.")
        st.dataframe(rels, hide_index=True, use_container_width=True)

with ont_col3:
    metrics = run("SELECT METRIC_NAME, METRIC_VARIANT, OWNER_TEAM, IS_CANONICAL FROM CHAINTRUTH_DB.ONTOLOGY.METRIC_REGISTRY")
    with st.expander(f"📐 METRIC_REGISTRY ({len(metrics)} records)"):
        st.markdown("Governed metric definitions with canonical flagging.")
        st.dataframe(metrics, hide_index=True, use_container_width=True)

# =============================================================================
# ANALYTICS LAYER
# =============================================================================
st.markdown("---")
section("Gold Layer — ANALYTICS Views")
st.caption("Pre-computed analytics views consumed by the dashboard")

view_info = [
    ("ERP_OTIF", "OTIF measured against ERP promised delivery date (canonical)", "ORDERS ⟕ SHIPMENTS", "Strictest definition — set at order time"),
    ("LOGISTICS_OTIF", "OTIF measured against carrier ETA", "ORDERS ⟕ SHIPMENTS", "Carrier ETA set at ship time, often optimistic"),
    ("SUPPLIER_OTIF", "OTIF measured against supplier commitment date", "ORDERS ⟕ SHIPMENTS", "Most lenient — suppliers pad commitments"),
    ("CHAINTRUTH_OTIF", "Unified view comparing all 3 definitions + conflict detection", "ERP_OTIF ∪ LOGISTICS_OTIF ∪ SUPPLIER_OTIF", "Detects when definitions disagree"),
    ("LEAD_TIME_ANALYTICS", "Days from order placement to delivery", "ORDERS ⟕ SHIPMENTS", "Min, avg, max lead time by grain"),
    ("FILL_RATE_ANALYTICS", "Percentage of ordered quantity shipped", "ORDERS ⟕ SHIPMENTS", "Measures inventory availability"),
    ("REVENUE_AT_RISK_ANALYTICS", "Revenue exposed to late, short, or overdue orders", "ORDERS ⟕ SHIPMENTS", "Order-grain aggregation prevents double-counting"),
]

for name, desc, sources, note in view_info:
    with st.expander(f"📊 ANALYTICS.{name}"):
        st.markdown(f"**Description:** {desc}")
        st.markdown(f"**Source Tables:** {sources}")
        st.markdown(f"**Note:** {note}")
        sample = run(f"SELECT * FROM CHAINTRUTH_DB.ANALYTICS.{name} LIMIT 3")
        st.dataframe(sample, hide_index=True, use_container_width=True)

# =============================================================================
# KEY LINEAGE PATHS
# =============================================================================
st.markdown("---")
section("Key Lineage Paths")

st.markdown("""
| Metric | Path | Grain |
|--------|------|-------|
| **ERP OTIF** | `ORDERS.PROMISED_DELIVERY_DATE` → `SHIPMENTS.ACTUAL_DELIVERY_DATE` → `ERP_OTIF` view | Month × Supplier × Plant × Segment |
| **Logistics OTIF** | `SHIPMENTS.CARRIER_ETA` → `SHIPMENTS.ACTUAL_DELIVERY_DATE` → `LOGISTICS_OTIF` view | Month × Supplier × Plant × Segment |
| **Supplier OTIF** | `ORDERS.SUPPLIER_COMMITMENT_DATE` → `SHIPMENTS.SHIP_DATE` → `SUPPLIER_OTIF` view | Month × Supplier × Plant × Segment |
| **Conflict Rate** | All 3 OTIF views → `CHAINTRUTH_OTIF` (detects disagreement) | Month × Supplier × Plant × Segment |
| **Revenue At Risk** | `ORDERS.ORDER_VALUE` + OTIF flags → `REVENUE_AT_RISK_ANALYTICS` (order-grain CTE) | Month × Supplier × Plant × Segment |
| **Lead Time** | `ORDERS.ORDER_DATE` → `SHIPMENTS.ACTUAL_DELIVERY_DATE` → `LEAD_TIME_ANALYTICS` | Month × Supplier × Plant × Segment |
| **Fill Rate** | `ORDERS.QUANTITY` → `SHIPMENTS.QUANTITY_SHIPPED` → `FILL_RATE_ANALYTICS` | Month × Supplier × Plant × Segment |
""")
