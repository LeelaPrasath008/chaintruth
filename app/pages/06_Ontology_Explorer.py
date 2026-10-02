import streamlit as st
import pandas as pd
from utils.db import run_query

st.set_page_config(page_title="Ontology Explorer", layout="wide")

# -- custom styling ------------------------------------------------------------
st.markdown("""
<style>
    .canonical-badge {
        background-color: #00CC96;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75em;
        font-weight: 600;
    }
    .variant-badge {
        background-color: #636EFA;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75em;
    }
    .entity-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .relationship-arrow {
        font-size: 1.1em;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

st.title("Ontology Explorer")
st.caption(
    "Browse the ChainTruth supply-chain ontology: entities, relationships, "
    "and governed metric definitions."
)

@st.cache_data(ttl=300)
def load_entities():
    return run_query(
        "SELECT * FROM CHAINTRUTH_DB.ONTOLOGY.ENTITY_TYPE ORDER BY ENTITY_TYPE_ID"
    )


@st.cache_data(ttl=300)
def load_relationships():
    return run_query(
        "SELECT * FROM CHAINTRUTH_DB.ONTOLOGY.RELATIONSHIP_TYPE ORDER BY RELATIONSHIP_ID"
    )


@st.cache_data(ttl=300)
def load_metrics():
    return run_query(
        "SELECT * FROM CHAINTRUTH_DB.ONTOLOGY.METRIC_REGISTRY "
        "ORDER BY METRIC_NAME, IS_CANONICAL DESC"
    )


entities_df = load_entities()
relationships_df = load_relationships()
metrics_df = load_metrics()

# -- ensure IS_CANONICAL is proper bool ----------------------------------------
metrics_df["IS_CANONICAL"] = metrics_df["IS_CANONICAL"].apply(
    lambda v: bool(v) if isinstance(v, bool) else str(v).lower() == "true"
)

# -- sidebar search & filters -------------------------------------------------
st.sidebar.header("Search & Filter")

search = st.sidebar.text_input("Search across all tables", placeholder="e.g. OTIF, Supplier, order...")

st.sidebar.markdown("---")
st.sidebar.subheader("Metric Filters")

owners = sorted(metrics_df["OWNER_TEAM"].unique())
sel_owners = st.sidebar.multiselect("Owner Team", options=owners)

units = sorted(metrics_df["UNIT"].unique())
sel_units = st.sidebar.multiselect("Unit", options=units)

sel_canonical = st.sidebar.radio(
    "Canonical Status", ["All", "Canonical Only", "Variants Only"], index=0
)

# -- apply search --------------------------------------------------------------
search_lower = search.strip().lower()


def text_match(df: pd.DataFrame) -> pd.DataFrame:
    if not search_lower:
        return df
    mask = pd.Series(False, index=df.index)
    for col in df.select_dtypes(include="object").columns:
        mask |= df[col].fillna("").str.lower().str.contains(search_lower, regex=False)
    return df[mask]


filtered_entities = text_match(entities_df)
filtered_rels = text_match(relationships_df)
filtered_metrics = text_match(metrics_df)

if sel_owners:
    filtered_metrics = filtered_metrics[filtered_metrics["OWNER_TEAM"].isin(sel_owners)]
if sel_units:
    filtered_metrics = filtered_metrics[filtered_metrics["UNIT"].isin(sel_units)]
if sel_canonical == "Canonical Only":
    filtered_metrics = filtered_metrics[filtered_metrics["IS_CANONICAL"]]
elif sel_canonical == "Variants Only":
    filtered_metrics = filtered_metrics[~filtered_metrics["IS_CANONICAL"]]

# -- overview counters ---------------------------------------------------------
st.markdown("### Overview")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Entities", len(filtered_entities))
c2.metric("Relationships", len(filtered_rels))
c3.metric("Metrics", len(filtered_metrics))
c4.metric("Canonical", int(filtered_metrics["IS_CANONICAL"].sum()))
c5.metric("Owner Teams", filtered_metrics["OWNER_TEAM"].nunique())

st.markdown("---")

# =============================================================================
# ENTITIES
# =============================================================================
st.markdown("### Entities")
st.caption("Core supply-chain objects tracked by ChainTruth.")

if filtered_entities.empty:
    st.info("No entities match your search.")
else:
    cols = st.columns(3)
    for i, (_, row) in enumerate(filtered_entities.iterrows()):
        with cols[i % 3]:
            st.markdown(
                f"**{row['ENTITY_NAME']}** &ensp; `{row['ENTITY_TYPE_ID']}`\n\n"
                f"{row['DESCRIPTION']}\n\n"
                f"Source: `{row['SOURCE_TABLE']}`  \n"
                f"PK: `{row['PRIMARY_KEY_COLUMN']}`"
            )
            st.markdown("---")

# =============================================================================
# RELATIONSHIPS
# =============================================================================
st.markdown("### Relationships")
st.caption("Directed edges connecting entities in the supply-chain graph.")

if filtered_rels.empty:
    st.info("No relationships match your search.")
else:
    for _, row in filtered_rels.iterrows():
        from_name = row["FROM_ENTITY_TYPE_ID"]
        to_name = row["TO_ENTITY_TYPE_ID"]
        st.markdown(
            f"<div class='entity-card'>"
            f"<strong>{row['RELATIONSHIP_NAME']}</strong> &ensp; "
            f"<code>{row['RELATIONSHIP_ID']}</code><br/>"
            f"<span class='relationship-arrow'>"
            f"{from_name} &rarr; {to_name}</span> &ensp; "
            f"<code>{row['CARDINALITY']}</code><br/>"
            f"<small>Join: <code>{from_name}.{row['JOIN_COLUMN_FROM']}</code> = "
            f"<code>{to_name}.{row['JOIN_COLUMN_TO']}</code></small><br/>"
            f"<small>{row['DESCRIPTION'] or ''}</small>"
            f"</div>",
            unsafe_allow_html=True,
        )

st.markdown("---")

# =============================================================================
# METRICS
# =============================================================================
st.markdown("### Metric Registry")
st.caption("Governed metric definitions with canonical flagging and full lineage.")

if filtered_metrics.empty:
    st.info("No metrics match your filters.")
else:
    for _, row in filtered_metrics.iterrows():
        label = row["METRIC_NAME"]
        badges = ""
        if row["IS_CANONICAL"]:
            badges += " <span class='canonical-badge'>CANONICAL</span>"
        if pd.notna(row["METRIC_VARIANT"]) and row["METRIC_VARIANT"]:
            badges += f" <span class='variant-badge'>{row['METRIC_VARIANT']}</span>"

        with st.expander(f"{label} — {row['METRIC_ID']}"):
            st.markdown(
                f"#### {label}{badges}",
                unsafe_allow_html=True,
            )

            col_a, col_b, col_c = st.columns(3)
            col_a.markdown(f"**Owner:** {row['OWNER_TEAM']}")
            col_b.markdown(f"**Unit:** {row['UNIT']}")
            direction = row["DIRECTION"].replace("_", " ").title()
            col_c.markdown(f"**Direction:** {direction}")

            st.markdown(f"**Description**  \n{row['DESCRIPTION']}")

            st.markdown("**SQL Expression**")
            st.code(row["METRIC_SQL"], language="sql")

            st.markdown(
                f"**Source Tables:** `{row['SOURCE_TABLES']}`  \n"
                f"**Source Columns:** `{row['SOURCE_COLUMNS']}`"
            )
