import streamlit as st

# -- color palette (enterprise dark) ------------------------------------------
BG = "#0E1117"
CARD = "#161B22"
CARD_BORDER = "#30363D"
PRIMARY = "#00D4AA"
SECONDARY = "#4C8BF5"
WARNING = "#FFB347"
DANGER = "#FF5C5C"
SUCCESS = "#00D4AA"
TEXT = "#FFFFFF"
TEXT_MUTED = "#8B949E"
SURFACE = "#21262D"

CHART_COLORS = {
    "ERP": DANGER,
    "Logistics": WARNING,
    "Supplier": SUCCESS,
    "primary": PRIMARY,
    "Late Delivery": DANGER,
    "Short Shipped": WARNING,
    "Overdue Open": SECONDARY,
}

# -- shared Plotly layout for dark mode ----------------------------------------
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor=CARD,
    font_color=TEXT,
    title_font_color=TEXT,
    legend_font_color=TEXT_MUTED,
    xaxis=dict(gridcolor="#30363D", zerolinecolor="#30363D"),
    yaxis=dict(gridcolor="#30363D", zerolinecolor="#30363D"),
    margin=dict(l=40, r=20, t=50, b=40),
)


def apply_dark(fig, height=380):
    fig.update_layout(**PLOTLY_LAYOUT, height=height)
    return fig


# -- CSS injection -------------------------------------------------------------
def inject_css():
    st.markdown("""
    <style>
        /* --- global --- */
        .main .block-container { padding-top: 0.8rem; max-width: 1280px; }
        section[data-testid="stSidebar"] { background-color: #0D1117; border-right: 1px solid #21262D; }
        section[data-testid="stSidebar"] .stMarkdown p,
        section[data-testid="stSidebar"] .stMarkdown span,
        section[data-testid="stSidebar"] label { color: #C9D1D9 !important; }

        /* --- hero banner --- */
        .hero-banner {
            background: linear-gradient(135deg, #0D1B2A 0%, #1B2838 50%, #0D1117 100%);
            border: 1px solid #00D4AA33;
            border-radius: 14px; padding: 2.2rem 2.5rem; margin-bottom: 1.5rem;
            position: relative; overflow: hidden;
        }
        .hero-banner::before {
            content: ''; position: absolute; top: -50%; right: -20%;
            width: 400px; height: 400px; border-radius: 50%;
            background: radial-gradient(circle, #00D4AA15 0%, transparent 70%);
        }
        .hero-banner h1 {
            color: #00D4AA; margin: 0 0 0.3rem 0; font-size: 2.2rem;
            font-weight: 800; letter-spacing: -0.5px;
        }
        .hero-banner p { color: #8B949E; margin: 0; font-size: 1rem; }
        .hero-badge {
            display: inline-block; background: #00D4AA22; color: #00D4AA;
            padding: 3px 12px; border-radius: 20px; font-size: 0.72rem;
            font-weight: 600; letter-spacing: 0.5px; margin-bottom: 0.6rem;
        }

        /* --- KPI cards --- */
        .kpi-card {
            background: #161B22; border: 1px solid #30363D;
            border-radius: 12px; padding: 1.3rem 1rem;
            text-align: center; transition: all 0.25s ease;
        }
        .kpi-card:hover { border-color: #00D4AA55; box-shadow: 0 0 20px #00D4AA15; transform: translateY(-2px); }
        .kpi-icon { font-size: 1.6rem; margin-bottom: 0.3rem; }
        .kpi-value { font-size: 1.9rem; font-weight: 800; color: #FFFFFF; margin: 0.15rem 0; letter-spacing: -0.5px; }
        .kpi-label { font-size: 0.75rem; color: #8B949E; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; }
        .kpi-status {
            font-size: 0.7rem; font-weight: 700; padding: 2px 10px;
            border-radius: 20px; display: inline-block; margin-top: 0.5rem;
        }
        .status-healthy { background: #00D4AA22; color: #00D4AA; }
        .status-warning { background: #FFB34722; color: #FFB347; }
        .status-critical { background: #FF5C5C22; color: #FF5C5C; }

        /* --- insight cards --- */
        .insight-card {
            background: #161B22; border-left: 3px solid #4C8BF5; border-radius: 10px;
            padding: 1rem 1.3rem; margin-bottom: 0.65rem;
            border: 1px solid #30363D; border-left-width: 3px;
        }
        .insight-card.danger { border-left-color: #FF5C5C; }
        .insight-card.warning { border-left-color: #FFB347; }
        .insight-card.success { border-left-color: #00D4AA; }
        .insight-card.critical { border-left-color: #FF5C5C; }
        .insight-title { font-weight: 700; font-size: 0.92rem; color: #E6EDF3; margin-bottom: 0.25rem; }
        .insight-body { font-size: 0.85rem; color: #8B949E; line-height: 1.5; }
        .insight-body b { color: #E6EDF3; }

        /* --- section headers --- */
        .section-header {
            font-size: 1rem; font-weight: 700; color: #E6EDF3;
            padding-bottom: 0.5rem; margin: 1.5rem 0 1rem 0;
            border-bottom: 1px solid #21262D;
            display: flex; align-items: center; gap: 0.5rem;
        }
        .section-dot { width: 8px; height: 8px; border-radius: 50%; background: #00D4AA; display: inline-block; }

        /* --- alert styles --- */
        .alert-critical { background: #FF5C5C12; border: 1px solid #FF5C5C44; border-left: 3px solid #FF5C5C; border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: 0.5rem; }
        .alert-warning  { background: #FFB34712; border: 1px solid #FFB34744; border-left: 3px solid #FFB347; border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: 0.5rem; }
        .alert-info     { background: #4C8BF512; border: 1px solid #4C8BF544; border-left: 3px solid #4C8BF5; border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: 0.5rem; }
        .alert-critical strong, .alert-warning strong, .alert-info strong { color: #E6EDF3; }
        .alert-critical span, .alert-warning span, .alert-info span { color: #8B949E; font-size: 0.88rem; }

        /* --- story card --- */
        .story-card {
            background: #161B22; border: 1px solid #30363D; border-radius: 12px;
            padding: 1.5rem; margin-bottom: 1rem;
        }
        .story-card h3 { color: #00D4AA; margin-top: 0; }
        .story-card p { color: #8B949E; }
        .story-card b { color: #E6EDF3; }

        /* --- sidebar branding --- */
        .sidebar-brand {
            text-align: center; padding: 0.8rem 0 1rem 0;
            border-bottom: 1px solid #21262D; margin-bottom: 1rem;
        }
        .sidebar-brand h2 { color: #00D4AA; margin: 0; font-size: 1.3rem; font-weight: 800; letter-spacing: -0.3px; }
        .sidebar-brand p { color: #484F58; font-size: 0.7rem; margin: 0.2rem 0 0 0; letter-spacing: 0.3px; }

        /* --- metric widget overrides --- */
        [data-testid="stMetric"] { background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 0.8rem 1rem; }
        [data-testid="stMetricLabel"] p { color: #8B949E !important; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.5px; }
        [data-testid="stMetricValue"] { color: #E6EDF3 !important; font-weight: 700; }

        /* --- footer --- */
        .ct-footer { text-align: center; color: #484F58; font-size: 0.72rem; padding: 1.5rem 0 0.5rem 0; border-top: 1px solid #21262D; margin-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)


# -- component helpers ---------------------------------------------------------

def sidebar_brand():
    st.sidebar.markdown(
        '<div class="sidebar-brand">'
        '<h2>ChainTruth</h2>'
        '<p>SUPPLY CHAIN GOVERNANCE PLATFORM</p>'
        '</div>',
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str):
    st.markdown(
        f'<div class="hero-banner">'
        f'<div class="hero-badge">CHAINTRUTH PLATFORM</div>'
        f'<h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


def kpi_card(icon: str, value: str, label: str, status: str = ""):
    status_html = ""
    if status == "healthy":
        status_html = '<div class="kpi-status status-healthy">HEALTHY</div>'
    elif status == "warning":
        status_html = '<div class="kpi-status status-warning">WARNING</div>'
    elif status == "critical":
        status_html = '<div class="kpi-status status-critical">CRITICAL</div>'
    return (
        f'<div class="kpi-card">'
        f'<div class="kpi-icon">{icon}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-label">{label}</div>'
        f'{status_html}'
        f'</div>'
    )


def insight(title: str, body: str, level: str = ""):
    cls = f"insight-card {level}" if level else "insight-card"
    return (
        f'<div class="{cls}">'
        f'<div class="insight-title">{title}</div>'
        f'<div class="insight-body">{body}</div>'
        f'</div>'
    )


def section(title: str):
    st.markdown(
        f'<div class="section-header"><span class="section-dot"></span>{title}</div>',
        unsafe_allow_html=True,
    )


def footer():
    st.markdown(
        '<div class="ct-footer">'
        'ChainTruth &bull; Built with Snowflake &amp; CoCo CLI &bull; Hackathon 2026'
        '</div>',
        unsafe_allow_html=True,
    )
