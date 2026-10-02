"""Defensive data-cleaning helpers for filter dropdowns and sorting."""
from __future__ import annotations
import pandas as pd


def clean_filter_values(series: pd.Series) -> pd.Series:
    """Coerce a column to clean strings, replacing NaN/None with 'Unknown'."""
    return series.fillna("Unknown").astype(str).replace("nan", "Unknown")


def safe_sort(values: list) -> list:
    """Sort a list that may contain mixed types by coercing everything to str."""
    return sorted(str(v) for v in values if pd.notna(v) and str(v) != "nan")


def safe_multiselect_options(series: pd.Series) -> list[str]:
    """Return a sorted, deduplicated, NaN-safe list of string options."""
    return safe_sort(clean_filter_values(series).unique().tolist())
