"""Smoke test the demo data provider SQL engine."""
import sys, os, types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

st_stub = types.ModuleType("streamlit")
st_stub.cache_data = lambda **kw: (lambda f: f)
st_stub.cache_resource = lambda **kw: (lambda f: f)
st_stub.session_state = {"app_mode": "demo"}
st_stub.error = lambda *a, **kw: None
st_stub.stop = lambda: None
sys.modules["streamlit"] = st_stub

from utils.data_provider import demo_query


def test_simple_select():
    df = demo_query("SELECT SUPPLIER_ID, SUPPLIER_NAME FROM CHAINTRUTH_DB.RAW.SUPPLIERS ORDER BY SUPPLIER_ID")
    assert len(df) == 50
    assert "SUPPLIER_ID" in df.columns


def test_aggregate_otif():
    df = demo_query(
        "SELECT ROUND(SUM(OTIF_COUNT)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
        "FROM CHAINTRUTH_DB.ANALYTICS.ERP_OTIF"
    )
    assert len(df) == 1
    assert "V" in df.columns
    assert 0 < df["V"].iloc[0] < 100


def test_distinct():
    df = demo_query("SELECT DISTINCT REGION FROM CHAINTRUTH_DB.RAW.SUPPLIERS ORDER BY REGION")
    assert len(df) >= 3
    assert "REGION" in df.columns


def test_group_by_with_limit():
    df = demo_query(
        "SELECT SUPPLIER_NAME, SUM(REVENUE_AT_RISK) AS RAR "
        "FROM CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS "
        "GROUP BY SUPPLIER_NAME ORDER BY RAR DESC LIMIT 5"
    )
    assert len(df) == 5
    assert "SUPPLIER_NAME" in df.columns
    assert "RAR" in df.columns


def test_count_star():
    df = demo_query("SELECT COUNT(*) AS V FROM CHAINTRUTH_DB.RAW.SUPPLIERS")
    assert df["V"].iloc[0] == 50


def test_info_schema():
    df = demo_query(
        "SELECT TABLE_NAME, ROW_COUNT FROM CHAINTRUTH_DB.INFORMATION_SCHEMA.TABLES "
        "WHERE TABLE_SCHEMA = 'RAW' AND TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME"
    )
    assert len(df) >= 5
    assert "TABLE_NAME" in df.columns


def test_dependencies():
    df = demo_query(
        "SELECT COUNT(*) AS EDGES, COUNT(DISTINCT REFERENCED_OBJECT_NAME) AS SOURCES "
        "FROM SNOWFLAKE.ACCOUNT_USAGE.OBJECT_DEPENDENCIES "
        "WHERE REFERENCED_DATABASE = 'CHAINTRUTH_DB'"
    )
    assert df["EDGES"].iloc[0] == 36


def test_ontology_select_star():
    df = demo_query("SELECT * FROM CHAINTRUTH_DB.ONTOLOGY.METRIC_REGISTRY ORDER BY METRIC_ID")
    assert len(df) == 7
    assert "METRIC_NAME" in df.columns


def test_conflict_rate():
    df = demo_query(
        "SELECT ROUND(SUM(CONFLICTED_SHIPMENTS)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
        "FROM CHAINTRUTH_DB.ANALYTICS.CHAINTRUTH_OTIF"
    )
    assert 80 < df["V"].iloc[0] < 100, f"Conflict rate {df['V'].iloc[0]} not near expected ~89%"


def test_supplier_otif_rate():
    df = demo_query(
        "SELECT ROUND(SUM(OTIF_COUNT)*100.0/NULLIF(SUM(TOTAL_SHIPMENTS),0),1) AS V "
        "FROM CHAINTRUTH_DB.ANALYTICS.SUPPLIER_OTIF"
    )
    assert 50 < df["V"].iloc[0] < 70, f"Supplier OTIF {df['V'].iloc[0]} not near expected ~61%"
