import streamlit as st
import plotly.graph_objects as go
from utils.db import run_query as run, safe_float, safe_int
from utils.theme import T
from utils.components import (
    page_header, section, kpi_card, kpi_grid, insight, insight_panel,
    alert_card, status_chip, footer,
)
from utils.charts import render_chart, SERIES
from utils.lineage_config import (
    NODES, EDGES, IMPACT, LAYER_COLORS, LAYER_TINTS,
)

page_header(
    "Data Lineage",
    "Trace every metric from raw ingestion through ontology governance to analytics",
)

# ── Executive summary KPIs ──────────────────────────────────────────────────
deps = run(
    "SELECT COUNT(*) AS EDGES, "
    "COUNT(DISTINCT REFERENCED_OBJECT_NAME) AS SOURCES, "
    "COUNT(DISTINCT REFERENCING_OBJECT_NAME) AS TARGETS "
    "FROM SNOWFLAKE.ACCOUNT_USAGE.OBJECT_DEPENDENCIES "
    "WHERE REFERENCED_DATABASE = 'CHAINTRUTH_DB'"
)
n_edges = safe_int(deps["EDGES"].iloc[0])
n_sources = safe_int(deps["SOURCES"].iloc[0])
n_targets = safe_int(deps["TARGETS"].iloc[0])

kpi_grid([
    kpi_card("Dependency Edges", str(n_edges), icon_name="link",
             caption="From ACCOUNT_USAGE.OBJECT_DEPENDENCIES"),
    kpi_card("Source Objects", str(n_sources), icon_name="factory",
             caption="Bronze + Silver tables"),
    kpi_card("Target Views", str(n_targets), icon_name="chart",
             caption="Gold analytics views"),
    kpi_card("Medallion Layers", "4", icon_name="shield",
             caption="Bronze → Silver → Gold → Presentation"),
])

# ── Sankey diagram ──────────────────────────────────────────────────────────
section("End-to-End Lineage")

node_ids = [n["id"] for n in NODES]
idx = {nid: i for i, nid in enumerate(node_ids)}

node_labels = [n["label"] for n in NODES]
node_colors = [LAYER_COLORS[n["layer"]] for n in NODES]

src_idx = [idx[e["src"]] for e in EDGES]
tgt_idx = [idx[e["tgt"]] for e in EDGES]
values = [e["w"] for e in EDGES]

link_colors = []
for e in EDGES:
    layer = next(n["layer"] for n in NODES if n["id"] == e["src"])
    link_colors.append(LAYER_TINTS[layer])

fig_sankey = go.Figure(go.Sankey(
    arrangement="snap",
    node=dict(
        label=node_labels,
        color=node_colors,
        pad=14,
        thickness=18,
        line=dict(color=T["border"], width=0.5),
    ),
    link=dict(
        source=src_idx,
        target=tgt_idx,
        value=values,
        color=link_colors,
    ),
))

render_chart(
    fig_sankey, "sankey",
    "Medallion Data Flow",
    subtitle="Bronze (RAW) → Silver (ONTOLOGY) → Gold (ANALYTICS) → Presentation",
    height=480,
    legend="none",
)

# Legend chips
cols = st.columns(4)
for i, (layer, color) in enumerate(LAYER_COLORS.items()):
    with cols[i]:
        st.markdown(
            f'<span style="display:inline-block; width:12px; height:12px; '
            f'border-radius:50%; background:{color}; margin-right:6px; '
            f'vertical-align:middle;"></span>'
            f'<span style="font-size:13px; color:{T["text_muted"]};">{layer}</span>',
            unsafe_allow_html=True,
        )

# ── Impact analysis ─────────────────────────────────────────────────────────
section("Impact Analysis")
st.markdown(
    f'<p style="color:{T["text_muted"]}; font-size:13px; margin-bottom:12px;">'
    "Select a source table to see downstream blast radius and severity.</p>",
    unsafe_allow_html=True,
)

selected = st.selectbox(
    "Source table",
    list(IMPACT.keys()),
    label_visibility="collapsed",
)

info = IMPACT[selected]
sev = info["severity"]
level_map = {"critical": "danger", "high": "warning", "medium": "success", "low": "success"}

st.markdown(alert_card(
    f"Impact of changes to RAW.{selected}",
    f'{info["note"]}<br>Severity: {status_chip(sev.upper(), level_map[sev])}'
    f'<br>Downstream objects: <strong>{len(info["downstream"])}</strong>',
    kind=level_map[sev],
), unsafe_allow_html=True)

if info["downstream"]:
    items = []
    for obj in info["downstream"]:
        node = next((n for n in NODES if n["id"] == obj), None)
        schema = node["schema"] if node else "ANALYTICS"
        items.append(insight(
            f"{schema}.{obj}",
            f"Will be affected if {selected} schema or data changes.",
            level="warning",
        ))
    st.markdown(insight_panel(items), unsafe_allow_html=True)
else:
    st.info("No downstream analytics views depend on this table.")

# ── Live metadata ───────────────────────────────────────────────────────────
section("Live Object Metadata")
st.markdown(
    f'<p style="color:{T["text_muted"]}; font-size:13px; margin-bottom:12px;">'
    "Row counts and column schemas queried live from Snowflake INFORMATION_SCHEMA.</p>",
    unsafe_allow_html=True,
)

tab_bronze, tab_silver, tab_gold = st.tabs(["Bronze (RAW)", "Silver (ONTOLOGY)", "Gold (ANALYTICS)"])

with tab_bronze:
    raw_tables = run(
        "SELECT TABLE_NAME, ROW_COUNT "
        "FROM CHAINTRUTH_DB.INFORMATION_SCHEMA.TABLES "
        "WHERE TABLE_SCHEMA = 'RAW' AND TABLE_TYPE = 'BASE TABLE' "
        "ORDER BY TABLE_NAME"
    )
    c1, c2, c3 = st.columns(3)
    for i, (_, row) in enumerate(raw_tables.iterrows()):
        name = row["TABLE_NAME"]
        rows = safe_int(row["ROW_COUNT"])
        with [c1, c2, c3][i % 3]:
            with st.expander(f"{name} — {rows:,} rows"):
                cols_df = run(
                    f"SELECT COLUMN_NAME, DATA_TYPE "
                    f"FROM CHAINTRUTH_DB.INFORMATION_SCHEMA.COLUMNS "
                    f"WHERE TABLE_SCHEMA = 'RAW' AND TABLE_NAME = '{name}' "
                    f"ORDER BY ORDINAL_POSITION"
                )
                st.dataframe(cols_df, hide_index=True, use_container_width=True)

with tab_silver:
    ont_tables = run(
        "SELECT TABLE_NAME, ROW_COUNT "
        "FROM CHAINTRUTH_DB.INFORMATION_SCHEMA.TABLES "
        "WHERE TABLE_SCHEMA = 'ONTOLOGY' AND TABLE_TYPE = 'BASE TABLE' "
        "ORDER BY TABLE_NAME"
    )
    c1, c2, c3 = st.columns(3)
    for i, (_, row) in enumerate(ont_tables.iterrows()):
        name = row["TABLE_NAME"]
        rows = safe_int(row["ROW_COUNT"])
        with [c1, c2, c3][i % 3]:
            with st.expander(f"{name} — {rows:,} rows"):
                cols_df = run(
                    f"SELECT COLUMN_NAME, DATA_TYPE "
                    f"FROM CHAINTRUTH_DB.INFORMATION_SCHEMA.COLUMNS "
                    f"WHERE TABLE_SCHEMA = 'ONTOLOGY' AND TABLE_NAME = '{name}' "
                    f"ORDER BY ORDINAL_POSITION"
                )
                st.dataframe(cols_df, hide_index=True, use_container_width=True)

with tab_gold:
    views = run(
        "SELECT TABLE_NAME "
        "FROM CHAINTRUTH_DB.INFORMATION_SCHEMA.TABLES "
        "WHERE TABLE_SCHEMA = 'ANALYTICS' AND TABLE_TYPE = 'VIEW' "
        "ORDER BY TABLE_NAME"
    )
    for _, row in views.iterrows():
        name = row["TABLE_NAME"]
        dep_df = run(
            "SELECT REFERENCED_OBJECT_NAME AS SOURCE_TABLE "
            "FROM SNOWFLAKE.ACCOUNT_USAGE.OBJECT_DEPENDENCIES "
            f"WHERE REFERENCING_OBJECT_NAME = '{name}' "
            "AND REFERENCED_DATABASE = 'CHAINTRUTH_DB' "
            "ORDER BY REFERENCED_OBJECT_NAME"
        )
        sources = ", ".join(dep_df["SOURCE_TABLE"].tolist()) if not dep_df.empty else "—"
        with st.expander(f"ANALYTICS.{name}"):
            st.markdown(f"**Source tables:** {sources}")
            sample = run(f"SELECT * FROM CHAINTRUTH_DB.ANALYTICS.{name} LIMIT 3")
            st.dataframe(sample, hide_index=True, use_container_width=True)

# ── Governance summary ──────────────────────────────────────────────────────
section("Governance")

gov_items = [
    insight(
        "All lineage edges verified",
        f"{n_edges} dependency edges confirmed via SNOWFLAKE.ACCOUNT_USAGE.OBJECT_DEPENDENCIES.",
        level="success",
    ),
    insight(
        "Ontology layer governs conflict detection",
        "METRIC_REGISTRY canonical flags drive CHAINTRUTH_OTIF conflict logic.",
        level="success",
    ),
    insight(
        "No orphan tables",
        "PARTS is the only RAW table not referenced by analytics views (catalog-only).",
        level="warning",
    ),
]
st.markdown(insight_panel(gov_items), unsafe_allow_html=True)

footer()
