import streamlit as st
import snowflake.connector
import pandas as pd
import time
import decimal


@st.cache_resource
def get_connection():
    return snowflake.connector.connect(connection_name="HA10998")


def _convert_decimals(df: pd.DataFrame) -> pd.DataFrame:
    """Convert decimal.Decimal columns to float64 and boolean strings to bool."""
    for col in df.columns:
        if len(df) == 0:
            continue
        sample = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
        if isinstance(sample, decimal.Decimal):
            df[col] = df[col].apply(lambda v: float(v) if v is not None else None).astype(float)
        elif isinstance(sample, bool):
            pass  # already bool
        elif isinstance(sample, str) and sample.lower() in ("true", "false"):
            df[col] = df[col].map({"True": True, "False": False, "true": True, "false": False})
    return df


def run_query(sql: str, retries: int = 2) -> pd.DataFrame:
    last_err = None
    for attempt in range(retries + 1):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(sql)
            df = cur.fetch_pandas_all()
            return _convert_decimals(df)
        except snowflake.connector.errors.DatabaseError as e:
            last_err = e
            if attempt < retries:
                time.sleep(1)
                st.cache_resource.clear()
            else:
                raise
    raise last_err  # unreachable but satisfies type checker


def safe_float(val, default=0.0):
    if val is None:
        return default
    try:
        result = float(val)
        if pd.isna(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


def safe_int(val, default=0):
    return int(safe_float(val, float(default)))
