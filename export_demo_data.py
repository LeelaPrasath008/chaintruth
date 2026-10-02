"""Export Snowflake analytics data to CSV for demo mode.

Run once while connected to Snowflake:
    SNOWFLAKE_CONNECTION_NAME=HA10998 python export_demo_data.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))
os.environ.setdefault("SNOWFLAKE_CONNECTION_NAME", "HA10998")
from utils.db import run_query

DATA_DIR = os.path.join(os.path.dirname(__file__), "app", "data")
os.makedirs(DATA_DIR, exist_ok=True)

EXPORTS = {
    "suppliers.csv": "SELECT SUPPLIER_ID, SUPPLIER_NAME, REGION, COUNTRY FROM CHAINTRUTH_DB.RAW.SUPPLIERS ORDER BY SUPPLIER_ID",
    "customers.csv": "SELECT CUSTOMER_ID, CUSTOMER_NAME, SEGMENT FROM CHAINTRUTH_DB.RAW.CUSTOMERS ORDER BY CUSTOMER_ID",
    "plants.csv": "SELECT PLANT_ID, PLANT_NAME, REGION, COUNTRY FROM CHAINTRUTH_DB.RAW.PLANTS ORDER BY PLANT_ID",
    "entity_type.csv": "SELECT * FROM CHAINTRUTH_DB.ONTOLOGY.ENTITY_TYPE ORDER BY ENTITY_TYPE_ID",
    "relationship_type.csv": "SELECT * FROM CHAINTRUTH_DB.ONTOLOGY.RELATIONSHIP_TYPE ORDER BY RELATIONSHIP_ID",
    "metric_registry.csv": "SELECT * FROM CHAINTRUTH_DB.ONTOLOGY.METRIC_REGISTRY ORDER BY METRIC_ID",
    "erp_otif.csv": "SELECT * FROM CHAINTRUTH_DB.ANALYTICS.ERP_OTIF ORDER BY ORDER_MONTH, SUPPLIER_ID",
    "logistics_otif.csv": "SELECT * FROM CHAINTRUTH_DB.ANALYTICS.LOGISTICS_OTIF ORDER BY ORDER_MONTH, SUPPLIER_ID",
    "supplier_otif.csv": "SELECT * FROM CHAINTRUTH_DB.ANALYTICS.SUPPLIER_OTIF ORDER BY ORDER_MONTH, SUPPLIER_ID",
    "chaintruth_otif.csv": "SELECT * FROM CHAINTRUTH_DB.ANALYTICS.CHAINTRUTH_OTIF ORDER BY ORDER_MONTH, SUPPLIER_ID",
    "lead_time_analytics.csv": "SELECT * FROM CHAINTRUTH_DB.ANALYTICS.LEAD_TIME_ANALYTICS ORDER BY ORDER_MONTH, SUPPLIER_ID",
    "fill_rate_analytics.csv": "SELECT * FROM CHAINTRUTH_DB.ANALYTICS.FILL_RATE_ANALYTICS ORDER BY ORDER_MONTH, SUPPLIER_ID",
    "revenue_at_risk_analytics.csv": "SELECT * FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS ORDER BY ORDER_MONTH, SUPPLIER_ID",
    "supplier_plant_links.csv": "SELECT DISTINCT o.SUPPLIER_ID, o.PLANT_ID FROM CHAINTRUTH_DB.RAW.ORDERS o ORDER BY o.SUPPLIER_ID, o.PLANT_ID",
    "plant_customer_links.csv": "SELECT DISTINCT o.PLANT_ID, o.CUSTOMER_ID FROM CHAINTRUTH_DB.RAW.ORDERS o ORDER BY o.PLANT_ID, o.CUSTOMER_ID",
}

for fname, sql in EXPORTS.items():
    print(f"Exporting {fname}...", end=" ")
    df = run_query(sql)
    path = os.path.join(DATA_DIR, fname)
    df.to_csv(path, index=False)
    print(f"{len(df)} rows")

print(f"\nDone. {len(EXPORTS)} files written to {DATA_DIR}")
