"""Dual-mode data provider.

In DEMO mode, intercepts SQL strings, maps table references to local CSVs,
and evaluates the query using pandas.  In SNOWFLAKE mode, passes through to
the real Snowflake connector.

Pages never import this directly — they keep calling ``run_query`` from db.py.
"""
from __future__ import annotations
import os, re, pathlib
import pandas as pd
import streamlit as st

_DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"

# Map fully-qualified or short table/view names to CSV filenames.
_TABLE_MAP: dict[str, str] = {
    "CHAINTRUTH_DB.RAW.SUPPLIERS": "suppliers.csv",
    "CHAINTRUTH_DB.RAW.CUSTOMERS": "customers.csv",
    "CHAINTRUTH_DB.RAW.PLANTS": "plants.csv",
    "CHAINTRUTH_DB.RAW.ORDERS": "supplier_plant_links.csv",
    "CHAINTRUTH_DB.RAW.PARTS": "suppliers.csv",
    "CHAINTRUTH_DB.ONTOLOGY.ENTITY_TYPE": "entity_type.csv",
    "CHAINTRUTH_DB.ONTOLOGY.RELATIONSHIP_TYPE": "relationship_type.csv",
    "CHAINTRUTH_DB.ONTOLOGY.METRIC_REGISTRY": "metric_registry.csv",
    "CHAINTRUTH_DB.ANALYTICS.ERP_OTIF": "erp_otif.csv",
    "CHAINTRUTH_DB.ANALYTICS.LOGISTICS_OTIF": "logistics_otif.csv",
    "CHAINTRUTH_DB.ANALYTICS.SUPPLIER_OTIF": "supplier_otif.csv",
    "CHAINTRUTH_DB.ANALYTICS.CHAINTRUTH_OTIF": "chaintruth_otif.csv",
    "CHAINTRUTH_DB.ANALYTICS.LEAD_TIME_ANALYTICS": "lead_time_analytics.csv",
    "CHAINTRUTH_DB.ANALYTICS.FILL_RATE_ANALYTICS": "fill_rate_analytics.csv",
    "CHAINTRUTH_DB.ANALYTICS.REVENUE_AT_RISK_ANALYTICS": "revenue_at_risk_analytics.csv",
}

# Order link tables for network page
_LINK_TABLES = {
    "SUPPLIER_ID,PLANT_ID": "supplier_plant_links.csv",
    "PLANT_ID,CUSTOMER_ID": "plant_customer_links.csv",
}


@st.cache_data(ttl=600)
def _load_csv(name: str) -> pd.DataFrame:
    path = _DATA_DIR / name
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, keep_default_na=False, na_values=[""])
    for col in df.columns:
        if "MONTH" in col.upper():
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def _find_table(sql: str) -> str | None:
    """Extract the primary table reference from a SQL string."""
    m = re.search(r"FROM\s+([\w.]+)", sql, re.IGNORECASE)
    if not m:
        return None
    return m.group(1).upper()


def _find_csv(sql: str) -> str | None:
    """Map a SQL query to its CSV file."""
    tbl = _find_table(sql)
    if not tbl:
        return None
    # Direct match
    if tbl in _TABLE_MAP:
        return _TABLE_MAP[tbl]
    # Try matching just the table name
    short = tbl.split(".")[-1]
    for fq, csv in _TABLE_MAP.items():
        if fq.endswith("." + short):
            return csv
    return None


def _apply_where(df: pd.DataFrame, sql: str) -> pd.DataFrame:
    """Apply simple WHERE IN clauses from the SQL to the dataframe."""
    where_match = re.search(r"WHERE\s+(.+?)(?:GROUP|ORDER|LIMIT|$)", sql, re.IGNORECASE | re.DOTALL)
    if not where_match:
        return df
    where_clause = where_match.group(1).strip()
    # Parse individual IN clauses
    for m in re.finditer(r"(\w+)\s+IN\s*\(([^)]+)\)", where_clause, re.IGNORECASE):
        col = m.group(1).upper()
        vals_str = m.group(2)
        vals = [v.strip().strip("'\"") for v in vals_str.split(",")]
        if col in df.columns:
            df = df[df[col].astype(str).isin(vals)]
    # Parse simple equality: COL = 'value'
    for m in re.finditer(r"(\w+)\s*=\s*'([^']+)'", where_clause):
        col = m.group(1).upper()
        val = m.group(2)
        if col in df.columns:
            df = df[df[col].astype(str) == val]
    # Parse boolean: IS_CANONICAL = TRUE
    for m in re.finditer(r"(\w+)\s*=\s*(TRUE|FALSE)\b", where_clause, re.IGNORECASE):
        col = m.group(1).upper()
        val = m.group(2).upper() == "TRUE"
        if col in df.columns:
            df = df[df[col].astype(str).str.upper().isin(["TRUE", "1"] if val else ["FALSE", "0"])]
    return df


def _parse_select_exprs(sql: str) -> list[tuple[str, str]]:
    """Parse SELECT expressions into (expr, alias) pairs."""
    select_match = re.search(r"SELECT\s+(.+?)\s+FROM", sql, re.IGNORECASE | re.DOTALL)
    if not select_match:
        return []
    select_str = select_match.group(1).strip()
    # Strip leading DISTINCT keyword
    if select_str.upper().startswith("DISTINCT "):
        select_str = select_str[9:].strip()
    if select_str == "*":
        return [("*", "*")]
    # Split by comma, respecting parentheses
    exprs = []
    depth = 0
    current = ""
    for ch in select_str:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            exprs.append(current.strip())
            current = ""
            continue
        current += ch
    if current.strip():
        exprs.append(current.strip())

    results = []
    for expr in exprs:
        # Find alias
        alias_match = re.search(r"\s+AS\s+(\w+)\s*$", expr, re.IGNORECASE)
        if alias_match:
            alias = alias_match.group(1).upper()
            expr_body = expr[:alias_match.start()].strip()
        else:
            alias = expr.strip().split(".")[-1].upper()
            expr_body = expr.strip()
        results.append((expr_body, alias))
    return results


def _eval_agg(df: pd.DataFrame, expr: str, alias: str) -> float | int:
    """Evaluate a single aggregate expression against a dataframe."""
    expr_up = expr.upper().strip()

    # COUNT(DISTINCT col)
    m = re.match(r"COUNT\s*\(\s*DISTINCT\s+(\w+)\s*\)", expr_up)
    if m:
        col = m.group(1)
        return int(df[col].nunique()) if col in df.columns else 0

    # COUNT(*)
    if re.match(r"COUNT\s*\(\s*\*\s*\)", expr_up):
        return len(df)

    # SUM(col) or SUM(expr)
    m = re.match(r"SUM\s*\((.+)\)", expr_up)
    if m:
        inner = m.group(1).strip()
        # SUM(A*B)
        mul = re.match(r"(\w+)\s*\*\s*(\w+)", inner)
        if mul:
            a, b = mul.group(1), mul.group(2)
            if a in df.columns and b in df.columns:
                return float((pd.to_numeric(df[a], errors="coerce") * pd.to_numeric(df[b], errors="coerce")).sum())
        # SUM(CASE...) — approximate as sum of matching boolean column
        if "CASE" in inner:
            return 0.0
        # Simple SUM(col)
        if inner in df.columns:
            return float(pd.to_numeric(df[inner], errors="coerce").sum())
        return 0.0

    # MIN(col)
    m = re.match(r"MIN\s*\((\w+)\)", expr_up)
    if m:
        col = m.group(1)
        if col in df.columns:
            return float(pd.to_numeric(df[col], errors="coerce").min())
        return 0.0

    # MAX(col)
    m = re.match(r"MAX\s*\((\w+)\)", expr_up)
    if m:
        col = m.group(1)
        if col in df.columns:
            return float(pd.to_numeric(df[col], errors="coerce").max())
        return 0.0

    return 0.0


def _eval_full_expr(df: pd.DataFrame, expr_up: str, alias: str) -> float:
    """Evaluate a complete expression that may include ROUND, division, multiplication."""
    # ROUND(expr, n)
    round_match = re.match(r"ROUND\s*\((.+),\s*(\d+)\)\s*$", expr_up)
    if round_match:
        inner = round_match.group(1).strip()
        decimals = int(round_match.group(2))
        return round(_eval_full_expr(df, inner, alias), decimals)

    # expr / NULLIF(expr, 0)
    # Find the top-level division — match from right to handle nested parens
    div_match = re.search(r"/\s*NULLIF\s*\(", expr_up)
    if div_match:
        num_part = expr_up[:div_match.start()].strip()
        den_part_match = re.search(r"NULLIF\s*\((.+?),\s*0\s*\)", expr_up[div_match.start():])
        if den_part_match:
            den_expr = den_part_match.group(1).strip()
            num_val = _eval_full_expr(df, num_part, alias)
            den_val = _eval_full_expr(df, den_expr, alias)
            return num_val / den_val if den_val else 0.0

    # expr * number (e.g., SUM(X)*100.0)
    mul_match = re.match(r"(.+?)\s*\*\s*([\d.]+)\s*$", expr_up)
    if mul_match:
        left = mul_match.group(1).strip()
        multiplier = float(mul_match.group(2))
        return _eval_full_expr(df, left, alias) * multiplier

    # Otherwise it's a bare aggregate
    return float(_eval_agg(df, expr_up, alias))


def _parse_group_by(sql: str) -> list[str]:
    m = re.search(r"GROUP\s+BY\s+([\w\s,._]+?)(?:\s+ORDER|\s+HAVING|\s+LIMIT|$)", sql, re.IGNORECASE)
    if not m:
        return []
    return [c.strip().upper().split(".")[-1] for c in m.group(1).split(",")]


def _parse_order_limit(sql: str) -> tuple[list[tuple[str, bool]], int | None]:
    """Return ([(col, ascending)], limit)."""
    orders = []
    m = re.search(r"ORDER\s+BY\s+(.+?)(?:\s+LIMIT|$)", sql, re.IGNORECASE)
    if m:
        for part in m.group(1).split(","):
            part = part.strip()
            desc = "DESC" in part.upper()
            col = re.sub(r"\s+(ASC|DESC).*", "", part, flags=re.IGNORECASE).strip()
            # Handle SUM(...) in ORDER BY — use alias from select
            if "(" in col:
                col = None  # skip complex order by
            else:
                col = col.upper().split(".")[-1]
            orders.append((col, not desc))

    limit = None
    m = re.search(r"LIMIT\s+(\d+)", sql, re.IGNORECASE)
    if m:
        limit = int(m.group(1))
    return orders, limit


def demo_query(sql: str) -> pd.DataFrame:
    """Execute a SQL query against local CSV files."""
    sql_clean = " ".join(sql.split())

    # Handle INFORMATION_SCHEMA queries with static responses
    if "INFORMATION_SCHEMA" in sql.upper():
        return _handle_info_schema(sql_clean)

    # Handle ACCOUNT_USAGE.OBJECT_DEPENDENCIES
    if "OBJECT_DEPENDENCIES" in sql.upper():
        return _handle_dependencies(sql_clean)

    # Handle DISTINCT col FROM orders (network page link queries)
    distinct_match = re.search(r"SELECT\s+DISTINCT\s+\w+\.(\w+),\s*\w+\.(\w+)\s+FROM", sql_clean, re.IGNORECASE)
    if distinct_match:
        cols = f"{distinct_match.group(1).upper()},{distinct_match.group(2).upper()}"
        if cols in _LINK_TABLES:
            return _load_csv(_LINK_TABLES[cols])

    csv_file = _find_csv(sql_clean)
    if not csv_file:
        return pd.DataFrame()

    df = _load_csv(csv_file).copy()
    if df.empty:
        return df

    # Normalize column names to uppercase
    df.columns = [c.upper() for c in df.columns]

    # Apply WHERE filters
    df = _apply_where(df, sql_clean)

    # Parse SELECT
    select_exprs = _parse_select_exprs(sql_clean)
    if not select_exprs:
        return df

    # SELECT *
    if select_exprs == [("*", "*")]:
        limit_match = re.search(r"LIMIT\s+(\d+)", sql_clean, re.IGNORECASE)
        if limit_match:
            df = df.head(int(limit_match.group(1)))
        return df

    # GROUP BY
    group_cols = _parse_group_by(sql_clean)

    if group_cols:
        # Grouped aggregation
        valid_groups = [c for c in group_cols if c in df.columns]
        if not valid_groups:
            return pd.DataFrame()

        grouped = df.groupby(valid_groups, as_index=False)
        result_rows = []
        for name, group_df in grouped:
            row = {}
            if isinstance(name, tuple):
                for i, col in enumerate(valid_groups):
                    row[col] = name[i]
            else:
                row[valid_groups[0]] = name

            for expr, alias in select_exprs:
                expr_up = expr.upper().strip()
                col_name = expr_up.split(".")[-1]
                if col_name in valid_groups:
                    continue
                row[alias] = _eval_full_expr(group_df, expr_up, alias)
            result_rows.append(row)

        result = pd.DataFrame(result_rows)
    else:
        # No GROUP BY — check if it's all aggregates
        has_agg = any(
            re.match(r"(SUM|COUNT|AVG|MIN|MAX|ROUND)\s*\(", expr.upper().strip())
            for expr, _ in select_exprs
        )
        if has_agg:
            row = {}
            for expr, alias in select_exprs:
                expr_up = expr.upper().strip()
                row[alias] = _eval_full_expr(df, expr_up, alias)
            result = pd.DataFrame([row])
        else:
            # Simple SELECT col1, col2 FROM table
            cols = []
            renames = {}
            for expr, alias in select_exprs:
                col = expr.upper().strip().split(".")[-1]
                if col.startswith("DISTINCT "):
                    col = col.replace("DISTINCT ", "")
                if col in df.columns:
                    cols.append(col)
                    if alias != col:
                        renames[col] = alias
            if cols:
                result = df[cols].copy()
                if renames:
                    result = result.rename(columns=renames)
                if "DISTINCT" in sql_clean.upper().split("FROM")[0]:
                    result = result.drop_duplicates()
            else:
                result = df

    # ORDER BY
    orders, limit = _parse_order_limit(sql_clean)
    if orders and not result.empty:
        valid_orders = [(col, asc) for col, asc in orders if col and col in result.columns]
        if valid_orders:
            result = result.sort_values(
                [c for c, _ in valid_orders],
                ascending=[a for _, a in valid_orders],
            )

    # LIMIT
    if limit and not result.empty:
        result = result.head(limit)

    return result.reset_index(drop=True)


def _handle_info_schema(sql: str) -> pd.DataFrame:
    """Handle INFORMATION_SCHEMA queries with static metadata."""
    sql_up = sql.upper()

    if "INFORMATION_SCHEMA.TABLES" in sql_up:
        schema_match = re.search(r"TABLE_SCHEMA\s*=\s*'(\w+)'", sql, re.IGNORECASE)
        schema = schema_match.group(1).upper() if schema_match else "RAW"

        tables_meta = {
            "RAW": [
                ("SUPPLIERS", "BASE TABLE", 50), ("CUSTOMERS", "BASE TABLE", 50),
                ("PLANTS", "BASE TABLE", 10), ("ORDERS", "BASE TABLE", 5000),
                ("SHIPMENTS", "BASE TABLE", 5031), ("PARTS", "BASE TABLE", 200),
            ],
            "ONTOLOGY": [
                ("ENTITY_TYPE", "BASE TABLE", 6), ("RELATIONSHIP_TYPE", "BASE TABLE", 7),
                ("METRIC_REGISTRY", "BASE TABLE", 7),
            ],
            "ANALYTICS": [
                ("ERP_OTIF", "VIEW", None), ("LOGISTICS_OTIF", "VIEW", None),
                ("SUPPLIER_OTIF", "VIEW", None), ("CHAINTRUTH_OTIF", "VIEW", None),
                ("LEAD_TIME_ANALYTICS", "VIEW", None), ("FILL_RATE_ANALYTICS", "VIEW", None),
                ("REVENUE_AT_RISK_ANALYTICS", "VIEW", None),
            ],
        }
        rows = tables_meta.get(schema, [])
        type_filter = None
        if "TABLE_TYPE" in sql_up:
            if "'BASE TABLE'" in sql_up:
                type_filter = "BASE TABLE"
            elif "'VIEW'" in sql_up:
                type_filter = "VIEW"
        if type_filter:
            rows = [r for r in rows if r[1] == type_filter]
        return pd.DataFrame(rows, columns=["TABLE_NAME", "TABLE_TYPE", "ROW_COUNT"])

    if "INFORMATION_SCHEMA.COLUMNS" in sql_up:
        table_match = re.search(r"TABLE_NAME\s*=\s*'(\w+)'", sql, re.IGNORECASE)
        if not table_match:
            return pd.DataFrame(columns=["COLUMN_NAME", "DATA_TYPE"])
        table = table_match.group(1).upper()
        # Load the CSV and infer column types
        for fq, csv_name in _TABLE_MAP.items():
            if fq.endswith("." + table):
                df = _load_csv(csv_name)
                if df.empty:
                    return pd.DataFrame(columns=["COLUMN_NAME", "DATA_TYPE"])
                type_map = {"int64": "NUMBER", "float64": "FLOAT", "object": "VARCHAR",
                            "bool": "BOOLEAN", "datetime64[ns]": "TIMESTAMP_NTZ"}
                rows = [(col.upper(), type_map.get(str(df[col].dtype), "VARCHAR"))
                        for col in df.columns]
                return pd.DataFrame(rows, columns=["COLUMN_NAME", "DATA_TYPE"])
        return pd.DataFrame(columns=["COLUMN_NAME", "DATA_TYPE"])

    return pd.DataFrame()


def _handle_dependencies(sql: str) -> pd.DataFrame:
    """Return static dependency metadata for demo mode."""
    sql_up = sql.upper()

    if "COUNT(*)" in sql_up:
        return pd.DataFrame([{"EDGES": 36, "SOURCES": 7, "TARGETS": 7}])

    if "REFERENCING_OBJECT_NAME" in sql_up:
        # Per-view dependencies
        view_match = re.search(r"REFERENCING_OBJECT_NAME\s*=\s*'(\w+)'", sql, re.IGNORECASE)
        if view_match:
            view = view_match.group(1).upper()
            deps = {
                "ERP_OTIF": ["CUSTOMERS", "ORDERS", "PLANTS", "SHIPMENTS", "SUPPLIERS"],
                "LOGISTICS_OTIF": ["CUSTOMERS", "ORDERS", "PLANTS", "SHIPMENTS", "SUPPLIERS"],
                "SUPPLIER_OTIF": ["CUSTOMERS", "ORDERS", "PLANTS", "SHIPMENTS", "SUPPLIERS"],
                "CHAINTRUTH_OTIF": ["CUSTOMERS", "METRIC_REGISTRY", "ORDERS", "PLANTS", "SHIPMENTS", "SUPPLIERS"],
                "LEAD_TIME_ANALYTICS": ["CUSTOMERS", "ORDERS", "PLANTS", "SHIPMENTS", "SUPPLIERS"],
                "FILL_RATE_ANALYTICS": ["CUSTOMERS", "ORDERS", "PLANTS", "SHIPMENTS", "SUPPLIERS"],
                "REVENUE_AT_RISK_ANALYTICS": ["CUSTOMERS", "ORDERS", "PLANTS", "SHIPMENTS", "SUPPLIERS"],
            }
            sources = deps.get(view, [])
            return pd.DataFrame({"SOURCE_TABLE": sources})

    return pd.DataFrame()


def is_demo_mode() -> bool:
    return st.session_state.get("app_mode") == "demo"
