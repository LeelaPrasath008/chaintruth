"""Lineage data model for the Data Lineage page.

Provides node/edge definitions for the Sankey diagram and impact metadata,
sourced live from SNOWFLAKE.ACCOUNT_USAGE.OBJECT_DEPENDENCIES when available,
with a curated fallback that matches the ChainTruth medallion architecture.
"""
from __future__ import annotations

LAYER_COLORS = {
    "Bronze": "#C77700",
    "Silver": "#5B6B7B",
    "Gold": "#0B6BCB",
    "Presentation": "#2A9D8F",
}

LAYER_TINTS = {
    "Bronze": "rgba(199,119,0,0.12)",
    "Silver": "rgba(91,107,123,0.12)",
    "Gold": "rgba(11,107,203,0.12)",
    "Presentation": "rgba(42,157,143,0.12)",
}

NODES: list[dict] = [
    # Bronze (RAW)
    {"id": "SUPPLIERS", "label": "SUPPLIERS", "layer": "Bronze", "schema": "RAW", "rows": 50},
    {"id": "PARTS", "label": "PARTS", "layer": "Bronze", "schema": "RAW", "rows": 200},
    {"id": "PLANTS", "label": "PLANTS", "layer": "Bronze", "schema": "RAW", "rows": 10},
    {"id": "CUSTOMERS", "label": "CUSTOMERS", "layer": "Bronze", "schema": "RAW", "rows": 50},
    {"id": "ORDERS", "label": "ORDERS", "layer": "Bronze", "schema": "RAW", "rows": 5000},
    {"id": "SHIPMENTS", "label": "SHIPMENTS", "layer": "Bronze", "schema": "RAW", "rows": 5031},
    # Silver (ONTOLOGY)
    {"id": "ENTITY_TYPE", "label": "ENTITY_TYPE", "layer": "Silver", "schema": "ONTOLOGY", "rows": 6},
    {"id": "RELATIONSHIP_TYPE", "label": "RELATIONSHIP_TYPE", "layer": "Silver", "schema": "ONTOLOGY", "rows": 7},
    {"id": "METRIC_REGISTRY", "label": "METRIC_REGISTRY", "layer": "Silver", "schema": "ONTOLOGY", "rows": 7},
    # Gold (ANALYTICS)
    {"id": "ERP_OTIF", "label": "ERP_OTIF", "layer": "Gold", "schema": "ANALYTICS"},
    {"id": "LOGISTICS_OTIF", "label": "LOGISTICS_OTIF", "layer": "Gold", "schema": "ANALYTICS"},
    {"id": "SUPPLIER_OTIF", "label": "SUPPLIER_OTIF", "layer": "Gold", "schema": "ANALYTICS"},
    {"id": "CHAINTRUTH_OTIF", "label": "CHAINTRUTH_OTIF", "layer": "Gold", "schema": "ANALYTICS"},
    {"id": "LEAD_TIME_ANALYTICS", "label": "LEAD_TIME", "layer": "Gold", "schema": "ANALYTICS"},
    {"id": "FILL_RATE_ANALYTICS", "label": "FILL_RATE", "layer": "Gold", "schema": "ANALYTICS"},
    {"id": "REVENUE_AT_RISK_ANALYTICS", "label": "REV_AT_RISK", "layer": "Gold", "schema": "ANALYTICS"},
    # Presentation
    {"id": "DASHBOARD", "label": "Dashboard", "layer": "Presentation"},
    {"id": "CONFLICT_CENTER", "label": "Conflict Center", "layer": "Presentation"},
    {"id": "SUPPLIER_RISK", "label": "Supplier Risk", "layer": "Presentation"},
]

# Edges: source → target with a weight for the Sankey link thickness.
EDGES: list[dict] = [
    # Bronze → Gold (from OBJECT_DEPENDENCIES)
    {"src": "ORDERS", "tgt": "ERP_OTIF", "w": 5},
    {"src": "SHIPMENTS", "tgt": "ERP_OTIF", "w": 5},
    {"src": "CUSTOMERS", "tgt": "ERP_OTIF", "w": 2},
    {"src": "SUPPLIERS", "tgt": "ERP_OTIF", "w": 2},
    {"src": "PLANTS", "tgt": "ERP_OTIF", "w": 1},
    {"src": "ORDERS", "tgt": "LOGISTICS_OTIF", "w": 5},
    {"src": "SHIPMENTS", "tgt": "LOGISTICS_OTIF", "w": 5},
    {"src": "CUSTOMERS", "tgt": "LOGISTICS_OTIF", "w": 2},
    {"src": "SUPPLIERS", "tgt": "LOGISTICS_OTIF", "w": 2},
    {"src": "PLANTS", "tgt": "LOGISTICS_OTIF", "w": 1},
    {"src": "ORDERS", "tgt": "SUPPLIER_OTIF", "w": 5},
    {"src": "SHIPMENTS", "tgt": "SUPPLIER_OTIF", "w": 5},
    {"src": "CUSTOMERS", "tgt": "SUPPLIER_OTIF", "w": 2},
    {"src": "SUPPLIERS", "tgt": "SUPPLIER_OTIF", "w": 2},
    {"src": "PLANTS", "tgt": "SUPPLIER_OTIF", "w": 1},
    {"src": "ORDERS", "tgt": "CHAINTRUTH_OTIF", "w": 5},
    {"src": "SHIPMENTS", "tgt": "CHAINTRUTH_OTIF", "w": 5},
    {"src": "CUSTOMERS", "tgt": "CHAINTRUTH_OTIF", "w": 2},
    {"src": "SUPPLIERS", "tgt": "CHAINTRUTH_OTIF", "w": 2},
    {"src": "PLANTS", "tgt": "CHAINTRUTH_OTIF", "w": 1},
    {"src": "METRIC_REGISTRY", "tgt": "CHAINTRUTH_OTIF", "w": 3},
    {"src": "ORDERS", "tgt": "LEAD_TIME_ANALYTICS", "w": 5},
    {"src": "SHIPMENTS", "tgt": "LEAD_TIME_ANALYTICS", "w": 5},
    {"src": "SUPPLIERS", "tgt": "LEAD_TIME_ANALYTICS", "w": 2},
    {"src": "PLANTS", "tgt": "LEAD_TIME_ANALYTICS", "w": 1},
    {"src": "CUSTOMERS", "tgt": "LEAD_TIME_ANALYTICS", "w": 2},
    {"src": "ORDERS", "tgt": "FILL_RATE_ANALYTICS", "w": 5},
    {"src": "SHIPMENTS", "tgt": "FILL_RATE_ANALYTICS", "w": 5},
    {"src": "SUPPLIERS", "tgt": "FILL_RATE_ANALYTICS", "w": 2},
    {"src": "PLANTS", "tgt": "FILL_RATE_ANALYTICS", "w": 1},
    {"src": "CUSTOMERS", "tgt": "FILL_RATE_ANALYTICS", "w": 2},
    {"src": "ORDERS", "tgt": "REVENUE_AT_RISK_ANALYTICS", "w": 5},
    {"src": "SHIPMENTS", "tgt": "REVENUE_AT_RISK_ANALYTICS", "w": 5},
    {"src": "SUPPLIERS", "tgt": "REVENUE_AT_RISK_ANALYTICS", "w": 2},
    {"src": "PLANTS", "tgt": "REVENUE_AT_RISK_ANALYTICS", "w": 1},
    {"src": "CUSTOMERS", "tgt": "REVENUE_AT_RISK_ANALYTICS", "w": 2},
    # Gold → Presentation
    {"src": "ERP_OTIF", "tgt": "DASHBOARD", "w": 4},
    {"src": "LOGISTICS_OTIF", "tgt": "DASHBOARD", "w": 4},
    {"src": "SUPPLIER_OTIF", "tgt": "DASHBOARD", "w": 4},
    {"src": "CHAINTRUTH_OTIF", "tgt": "CONFLICT_CENTER", "w": 6},
    {"src": "REVENUE_AT_RISK_ANALYTICS", "tgt": "SUPPLIER_RISK", "w": 5},
    {"src": "LEAD_TIME_ANALYTICS", "tgt": "DASHBOARD", "w": 3},
    {"src": "FILL_RATE_ANALYTICS", "tgt": "DASHBOARD", "w": 3},
    {"src": "REVENUE_AT_RISK_ANALYTICS", "tgt": "DASHBOARD", "w": 3},
]

# Impact analysis: what breaks if a source table changes.
IMPACT: dict[str, dict] = {
    "ORDERS": {
        "downstream": ["ERP_OTIF", "LOGISTICS_OTIF", "SUPPLIER_OTIF", "CHAINTRUTH_OTIF",
                        "LEAD_TIME_ANALYTICS", "FILL_RATE_ANALYTICS", "REVENUE_AT_RISK_ANALYTICS"],
        "severity": "critical",
        "note": "Core transactional table — feeds every analytics view.",
    },
    "SHIPMENTS": {
        "downstream": ["ERP_OTIF", "LOGISTICS_OTIF", "SUPPLIER_OTIF", "CHAINTRUTH_OTIF",
                        "LEAD_TIME_ANALYTICS", "FILL_RATE_ANALYTICS", "REVENUE_AT_RISK_ANALYTICS"],
        "severity": "critical",
        "note": "Core fulfillment table — all OTIF and logistics metrics depend on it.",
    },
    "SUPPLIERS": {
        "downstream": ["ERP_OTIF", "LOGISTICS_OTIF", "SUPPLIER_OTIF", "CHAINTRUTH_OTIF",
                        "LEAD_TIME_ANALYTICS", "FILL_RATE_ANALYTICS", "REVENUE_AT_RISK_ANALYTICS"],
        "severity": "high",
        "note": "Supplier dimension — name/region used in every view's GROUP BY.",
    },
    "CUSTOMERS": {
        "downstream": ["ERP_OTIF", "LOGISTICS_OTIF", "SUPPLIER_OTIF", "CHAINTRUTH_OTIF",
                        "LEAD_TIME_ANALYTICS", "FILL_RATE_ANALYTICS", "REVENUE_AT_RISK_ANALYTICS"],
        "severity": "high",
        "note": "Customer dimension — segment column drives all slice-and-dice.",
    },
    "PLANTS": {
        "downstream": ["ERP_OTIF", "LOGISTICS_OTIF", "SUPPLIER_OTIF", "CHAINTRUTH_OTIF",
                        "LEAD_TIME_ANALYTICS", "FILL_RATE_ANALYTICS", "REVENUE_AT_RISK_ANALYTICS"],
        "severity": "medium",
        "note": "Plant dimension — region grouping for geography analysis.",
    },
    "PARTS": {
        "downstream": [],
        "severity": "low",
        "note": "Part catalog — not currently referenced by analytics views.",
    },
    "METRIC_REGISTRY": {
        "downstream": ["CHAINTRUTH_OTIF"],
        "severity": "high",
        "note": "Ontology governance — canonical flags drive conflict detection logic.",
    },
}
