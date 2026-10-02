# ChainTruth

Governed supply chain analytics platform exposing three conflicting OTIF
(On-Time In-Full) definitions through an ontology layer — built on Snowflake,
Streamlit, and Plotly.

## Architecture

```
Bronze (RAW)          Silver (ONTOLOGY)      Gold (ANALYTICS)         Presentation
──────────────        ─────────────────      ────────────────         ────────────
SUPPLIERS (50)        ENTITY_TYPE (6)        ERP_OTIF           ──→  Dashboard
PARTS (200)           RELATIONSHIP_TYPE (7)  LOGISTICS_OTIF     ──→  Conflict Center
PLANTS (10)           METRIC_REGISTRY (7)    SUPPLIER_OTIF      ──→  Supplier Risk
CUSTOMERS (50)                               CHAINTRUTH_OTIF    ──→  13 Streamlit pages
ORDERS (5000)                                LEAD_TIME_ANALYTICS
SHIPMENTS (5031)                             FILL_RATE_ANALYTICS
                                             REVENUE_AT_RISK_ANALYTICS
```

## Quick Start (Local)

```bash
# 1. Clone and install
git clone <repo-url> && cd chaintruth
pip install -r requirements.txt

# 2. Configure Snowflake credentials (pick one method)

# Method A — Named connection (if ~/.snowflake/connections.toml exists)
export SNOWFLAKE_CONNECTION_NAME=Your account verifier (SnowFlake)

# Method B — Explicit credentials
export SNOWFLAKE_ACCOUNT=your_account.region
export SNOWFLAKE_USER=your_username
export SNOWFLAKE_PASSWORD=your_password

# 3. Set up the database (first time only)
# Run the SQL files in setup/ in order: 01 through 05

# 4. Launch
cd app
streamlit run streamlit_app.py
```

## Deployment

### Streamlit Community Cloud

1. Push the repo to GitHub.
2. In Streamlit Cloud, set **Main file path** to `app/streamlit_app.py`.
3. Add secrets under **Settings > Secrets**:
   ```toml
   [snowflake]
   account = "your_account.region"
   user = "your_username"
   password = "your_password"
   warehouse = "CHAINTRUTH_WH"
   database = "CHAINTRUTH_DB"
   role = "SYSADMIN"
   ```

### Render / Docker

```bash
docker build -t chaintruth .
docker run -p 8501:8501 \
  -e SNOWFLAKE_ACCOUNT=your_account.region \
  -e SNOWFLAKE_USER=your_username \
  -e SNOWFLAKE_PASSWORD=your_password \
  chaintruth
```

On Render, set the environment variables in the dashboard and point the
Docker build context to the repo root.

## Project Structure

```
chaintruth/
├── app/
│   ├── .streamlit/
│   │   └── config.toml          # Theme and client settings
│   ├── pages/                   # 13 Streamlit pages
│   ├── utils/
│   │   ├── charts.py            # Centralized Plotly chart system
│   │   ├── components.py        # Shared UI components
│   │   ├── db.py                # Snowflake connection + query runner
│   │   ├── lineage_config.py    # Lineage graph data model
│   │   └── theme.py             # Design tokens and CSS injection
│   └── streamlit_app.py         # Entry point / navigation
├── setup/                       # SQL scripts (01–05) to create the database
├── tests/
│   ├── test_chart_layout.py     # 40 Plotly layout tests
│   └── test_contrast.py         # WCAG contrast verification
├── .env.example                 # Template for environment variables
├── Dockerfile                   # Container build for Render / Docker
├── requirements.txt             # Python dependencies
└── README.md
```

## Pages

| Section | Page | Description |
|---------|------|-------------|
| Overview | Dashboard | KPIs, filters, 6 governance charts |
| Overview | Executive Story | 8-section judge walkthrough |
| Overview | Executive Summary | CEO/CFO one-minute overview |
| Investigate | Conflict Center | Three OTIF definitions compared |
| Investigate | Supplier Risk | Revenue at risk analysis |
| Investigate | AI Insights | Auto-generated anomaly insights |
| Investigate | Ask ChainTruth | Natural language query interface |
| Govern | Ontology Explorer | Entity / relationship / metric browser |
| Govern | Data Lineage | Interactive Sankey + impact analysis |
| Govern | Business Glossary | Governed metric definitions |
| Monitor | Alert Center | Threshold-based alerts |
| Monitor | Supply Chain Network | Force-directed network graph |
| Monitor | What-If Analysis | Parameter simulator |

## Credential Resolution Order

`db.py` checks credentials in this order:

1. `SNOWFLAKE_CONNECTION_NAME` env var → uses named connection
2. `SNOWFLAKE_ACCOUNT` / `SNOWFLAKE_USER` env vars → explicit connect
3. `st.secrets["snowflake"]` (Streamlit Cloud secrets.toml) → explicit connect
4. If none found → shows error and stops

## Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

## Tech Stack

- **Streamlit** 1.64+ with `st.navigation`
- **Plotly** 7.x for all charts (centralized via `render_chart`)
- **Snowflake** connector (CHAINTRUTH_DB with RAW / ONTOLOGY / ANALYTICS schemas)
- **Pandas** for data manipulation
- **WCAG 2.1 AA** compliant color palette
