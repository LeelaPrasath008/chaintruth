import streamlit as st
import pandas as pd
from utils.db import run_query
from utils.theme import T
from utils.components import page_header, kpi_card, kpi_grid, section, footer
from utils.tour import render_tour_banner
from utils.data_cleaning import safe_multiselect_options

page_header("Ontology Explorer", "Browse the ChainTruth supply-chain ontology")
render_tour_banner()

@st.cache_data(ttl=300)
def load_entities():
    return run_query("SELECT * FROM CHAINTRUTH_DB.ONTOLOGY.ENTITY_TYPE ORDER BY ENTITY_TYPE_ID")

@st.cache_data(ttl=300)
def load_relationships():
    return run_query("SELECT * FROM CHAINTRUTH_DB.ONTOLOGY.RELATIONSHIP_TYPE ORDER BY RELATIONSHIP_ID")

@st.cache_data(ttl=300)
def load_metrics():
    return run_query(
        "SELECT * FROM CHAINTRUTH_DB.ONTOLOGY.METRIC_REGISTRY ORDER BY METRIC_NAME, IS_CANONICAL DESC"
    )

entities_df = load_entities()
relationships_df = load_relationships()
metrics_df = load_metrics()

metrics_df["IS_CANONICAL"] = metrics_df["IS_CANONICAL"].apply(
    lambda v: bool(v) if isinstance(v, bool) else str(v).lower() == "true"
)

# -- sidebar search & filters -------------------------------------------------
st.sidebar.markdown("**Search & Filter**")
search = st.sidebar.text_input("Search across all tables", placeholder="e.g. OTIF, Supplier, order...")
st.sidebar.markdown("---")
st.sidebar.markdown("**Metric Filters**")
owners = safe_multiselect_options(metrics_df["OWNER_TEAM"])
sel_owners = st.sidebar.multiselect("Owner Team", options=owners)
units = safe_multiselect_options(metrics_df["UNIT"])
sel_units = st.sidebar.multiselect("Unit", options=units)
sel_canonical = st.sidebar.radio("Canonical Status", ["All", "Canonical Only", "Variants Only"], index=0)

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

# -- overview KPIs -------------------------------------------------------------
section("Ontology overview")
kpi_grid([
    kpi_card("Entity Types", str(len(filtered_entities)), status="healthy", icon_name="factory"),
    kpi_card("Relationships", str(len(filtered_rels)), status="healthy", icon_name="link"),
    kpi_card("Metrics", str(len(filtered_metrics)), status="healthy", icon_name="chart"),
    kpi_card("Canonical", str(int(filtered_metrics["IS_CANONICAL"].sum())), status="healthy", icon_name="shield"),
    kpi_card("Owner Teams", str(filtered_metrics["OWNER_TEAM"].nunique()), icon_name="users"),
])

# =============================================================================
# ENTITIES
# =============================================================================
section("Entity types")

if filtered_entities.empty:
    st.info("No entities match your search.")
else:
    cols = st.columns(3)
    for i, (_, row) in enumerate(filtered_entities.iterrows()):
        with cols[i % 3]:
            st.markdown(
                f'<div class="ct-story">'
                f'<h3 style="font-size:1rem; margin-bottom:0.5rem;">{row["ENTITY_NAME"]}</h3>'
                f'<p style="margin:0 0 0.3rem 0;">{row["DESCRIPTION"]}</p>'
                f'<p style="margin:0; font-size:0.8rem;"><b>Source:</b> <code>{row["SOURCE_TABLE"]}</code> &nbsp; '
                f'<b>PK:</b> <code>{row["PRIMARY_KEY_COLUMN"]}</code></p></div>',
                unsafe_allow_html=True,
            )

# =============================================================================
# RELATIONSHIPS
# =============================================================================
section("Relationships")

if filtered_rels.empty:
    st.info("No relationships match your search.")
else:
    for _, row in filtered_rels.iterrows():
        from_name = row["FROM_ENTITY_TYPE_ID"]
        to_name = row["TO_ENTITY_TYPE_ID"]
        st.markdown(
            f'<div class="ct-story">'
            f'<b style="color:{T["primary"]};">{row["RELATIONSHIP_NAME"]}</b> &ensp; '
            f'<code style="color:{T["text_muted"]};">{row["RELATIONSHIP_ID"]}</code><br/>'
            f'<span style="font-size:1.1rem; font-weight:600; color:{T["text"]};">'
            f'{from_name} &rarr; {to_name}</span> &ensp; '
            f'<code style="color:{T["text_muted"]};">{row["CARDINALITY"]}</code><br/>'
            f'<span style="font-size:0.82rem; color:{T["text_muted"]};">'
            f'Join: <code>{from_name}.{row["JOIN_COLUMN_FROM"]}</code> = '
            f'<code>{to_name}.{row["JOIN_COLUMN_TO"]}</code></span><br/>'
            f'<span style="font-size:0.82rem; color:{T["text_muted"]};">{row["DESCRIPTION"] or ""}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

# =============================================================================
# METRICS
# =============================================================================
section("Metric registry")

if filtered_metrics.empty:
    st.info("No metrics match your filters.")
else:
    for _, row in filtered_metrics.iterrows():
        label = row["METRIC_NAME"]
        badges = ""
        if row["IS_CANONICAL"]:
            badges += ' <span class="ct-chip ct-chip-success">CANONICAL</span>'
        if pd.notna(row["METRIC_VARIANT"]) and row["METRIC_VARIANT"]:
            badges += f' <span class="ct-chip ct-chip-neutral">{row["METRIC_VARIANT"]}</span>'

        with st.expander(f"{label} — {row['METRIC_ID']}"):
            st.markdown(f"#### {label}{badges}", unsafe_allow_html=True)
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

footer()
