"""ChainTruth design tokens and global CSS.

Every visual constant lives here.  Pages call ``apply_theme()`` once at the
top; nothing else injects ``<style>`` blocks.
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------
T = dict(
    bg="#F4F6F9",
    surface="#FFFFFF",
    border="#DDE3EA",
    text="#1B2733",
    text_muted="#5B6B7B",
    primary="#0B6BCB",
    primary_hover="#095AAE",
    accent="#29B5E8",
    sidebar_bg="#0F2A43",
    sidebar_text="#E6EDF5",
    sidebar_muted="#A9B8C9",
    sidebar_active_bg="#1B4468",
    success="#17794C",
    success_tint="#E6F4EC",
    warning="#8A5A00",
    warning_tint="#FFF4DB",
    danger="#B3202F",
    danger_tint="#FBE8EA",
    series=["#2F6FB5", "#2A9D8F", "#C77700", "#7A5FB3", "#D1495B", "#6B7C93"],
    grid="#E6EBF1",
    radius="8px",
    shadow="0 1px 2px rgba(15,42,67,.06)",
    font='"Segoe UI",-apple-system,"Helvetica Neue",Arial,sans-serif',
)

# Convenience aliases used by page code
PRIMARY = T["primary"]
DANGER = T["danger"]
WARNING = T["warning"]
SUCCESS = T["success"]


def apply_theme():
    """Inject the single global CSS block.  Call once per page run."""
    st.markdown(_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# CSS — single block, explicit colors, no inheritance assumptions
# ---------------------------------------------------------------------------
_CSS = f"""<style>
/* ---- CSS custom properties ---- */
:root {{
    --ct-primary: {T["primary"]};
    --ct-bg: {T["bg"]};
    --ct-surface: {T["surface"]};
    --ct-text: {T["text"]};
    --ct-muted: {T["text_muted"]};
    --ct-border: {T["border"]};
    --ct-primary-soft: rgba(11,107,203,.08);
    --ct-s1:4px; --ct-s2:8px; --ct-s3:12px; --ct-s4:16px; --ct-s5:24px; --ct-s6:32px;
    --ct-r-sm:8px; --ct-r-md:12px; --ct-r-lg:16px;
    --ct-shadow-sm: {T["shadow"]};
    --ct-shadow-md: 0 4px 12px rgba(15,42,67,.08);
    --ct-shadow-hover: 0 8px 20px rgba(15,42,67,.12);
}}

/* ---- base ---- */
html, body, [data-testid="stAppViewContainer"],
[data-testid="stApp"] {{
    background-color: {T["bg"]} !important;
    color: {T["text"]} !important;
    font-family: {T["font"]};
}}
.main .block-container {{
    padding: 1.5rem 2rem 4rem 2rem;
    max-width: 1400px;
}}
@media (max-width: 768px) {{
    .main .block-container {{ padding: 1rem; }}
}}
h1,h2,h3,h4,h5,h6 {{ color: {T["text"]} !important; }}
p, li, span, label {{ color: {T["text"]}; }}

/* ---- sidebar (navy) ---- */
section[data-testid="stSidebar"] {{
    background-color: {T["sidebar_bg"]} !important;
    border-right: none !important;
}}
section[data-testid="stSidebar"] * {{
    color: {T["sidebar_text"]} !important;
}}
section[data-testid="stSidebar"] [data-testid="stSidebarNavSeparator"] span {{
    color: {T["sidebar_muted"]} !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    letter-spacing: .5px !important;
    text-transform: uppercase !important;
}}
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] {{
    border-radius: 6px;
    margin: 1px 8px;
    padding: 6px 12px;
    transition: background .15s;
}}
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover {{
    background: rgba(255,255,255,.08);
}}
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] {{
    background: {T["sidebar_active_bg"]} !important;
    border-left: 3px solid {T["accent"]};
}}
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] span {{
    color: #FFFFFF !important;
    font-weight: 600;
}}
/* brand block */
.ct-sidebar-brand {{
    text-align: left; padding: 16px 20px 12px 20px;
    border-bottom: 1px solid rgba(255,255,255,.1);
    margin-bottom: 8px;
    position: sticky; top: 0; z-index: 999;
    background: {T["sidebar_bg"]};
}}
.ct-sidebar-brand .ct-logo {{
    font-size: 18px; font-weight: 700; color: #FFFFFF !important;
    letter-spacing: -.3px;
}}
.ct-sidebar-brand .ct-logo span {{ color: {T["accent"]}; }}
.ct-sidebar-brand .ct-env {{
    display: inline-block; margin-top: 4px;
    font-size: 10px; font-weight: 600; letter-spacing: .4px;
    padding: 2px 8px; border-radius: 4px;
    background: rgba(255,255,255,.1); color: {T["sidebar_muted"]} !important;
}}

/* ---- sidebar buttons ---- */
section[data-testid="stSidebar"] button[kind="secondary"] {{
    background: rgba(255,255,255,.12) !important;
    color: {T["sidebar_text"]} !important;
    border: 1px solid rgba(255,255,255,.2) !important;
}}
section[data-testid="stSidebar"] button[kind="secondary"]:hover {{
    background: rgba(255,255,255,.22) !important;
    border-color: rgba(255,255,255,.35) !important;
}}
/* sidebar footer */
.ct-sidebar-footer {{
    position: absolute; bottom: 0; left: 0; right: 0;
    text-align: center; padding: 12px;
    font-size: 11px; color: {T["sidebar_muted"]} !important;
    border-top: 1px solid rgba(255,255,255,.06);
}}

/* ---- page header ---- */
.ct-page-header {{
    display: flex; align-items: baseline; justify-content: space-between;
    padding-bottom: 12px; margin-bottom: 20px;
    border-bottom: 1px solid {T["border"]};
}}
.ct-page-header .ct-ph-left h1 {{
    font-size: 28px; font-weight: 700; line-height: 1.2;
    margin: 0 0 4px 0; color: {T["text"]} !important;
}}
.ct-page-header .ct-ph-left p {{
    font-size: 14px; color: {T["text_muted"]}; margin: 0 0 8px 0; line-height: 1.5;
}}
.ct-page-header .ct-ph-right {{
    font-size: 12px; color: {T["text_muted"]}; text-align: right;
    white-space: nowrap;
}}
/* header badge row */
.ct-badge-row {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.ct-badge {{
    display: inline-flex; align-items: center; gap: 4px;
    font-size: 12px; font-weight: 500; padding: 2px 10px;
    border-radius: 999px; border: 1px solid {T["border"]};
    background: var(--ct-primary-soft); color: {T["text_muted"]};
    white-space: nowrap;
}}
.ct-badge-dot {{
    width: 6px; height: 6px; border-radius: 50%;
    background: {T["primary"]}; flex-shrink: 0;
}}

/* ---- KPI grid ---- */
.ct-kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: var(--ct-s4); margin-bottom: var(--ct-s5);
}}
.ct-kpi {{
    background: {T["surface"]}; border: 1px solid {T["border"]};
    border-radius: var(--ct-r-md); padding: var(--ct-s4);
    box-shadow: var(--ct-shadow-sm); min-height: 120px;
    display: flex; flex-direction: column; justify-content: center;
    transition: transform .15s ease, box-shadow .15s ease;
}}
.ct-kpi:hover {{
    transform: translateY(-2px);
    box-shadow: var(--ct-shadow-hover);
}}
.ct-kpi-top {{
    display: flex; align-items: center; gap: 8px;
    margin-bottom: 6px;
}}
.ct-kpi-icon {{
    width: 36px; height: 36px; border-radius: 50%;
    background: var(--ct-primary-soft);
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0; color: {T["primary"]};
}}
.ct-kpi-label {{
    font-size: 12px; line-height: 16px; font-weight: 600;
    color: {T["text_muted"]}; text-transform: uppercase;
    letter-spacing: .04em;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}}
.ct-kpi-value {{
    font-size: clamp(24px, 2.2vw, 32px); line-height: 1.2; font-weight: 700;
    color: {T["text"]}; white-space: nowrap;
    font-variant-numeric: tabular-nums;
}}
.ct-kpi-caption {{
    font-size: 12px; color: {T["text_muted"]}; margin-top: 4px; line-height: 1.4;
}}

/* ---- status chips ---- */
.ct-chip {{
    display: inline-flex; align-items: center; gap: 4px;
    font-size: 11px; font-weight: 600; padding: 2px 8px;
    border-radius: 4px; white-space: nowrap;
}}
.ct-chip svg {{ width: 12px; height: 12px; flex-shrink: 0; }}
.ct-chip-success {{ background: {T["success_tint"]}; color: {T["success"]}; }}
.ct-chip-warning {{ background: {T["warning_tint"]}; color: {T["warning"]}; }}
.ct-chip-danger  {{ background: {T["danger_tint"]};  color: {T["danger"]};  }}
.ct-chip-neutral {{ background: #EEF1F5; color: {T["text_muted"]}; }}

/* ---- section header ---- */
.ct-section {{
    font-size: 18px; line-height: 24px; font-weight: 600;
    color: {T["text"]}; padding-bottom: 8px; margin: var(--ct-s5) 0 var(--ct-s4) 0;
    border-bottom: 1px solid {T["border"]};
}}

/* ---- insight panel ---- */
.ct-insight {{
    background: {T["surface"]}; border: 1px solid {T["border"]};
    border-left: 3px solid {T["primary"]}; border-radius: var(--ct-r-sm);
    padding: 12px 16px; margin-bottom: 8px;
    box-shadow: var(--ct-shadow-sm);
}}
.ct-insight-danger  {{ border-left-color: {T["danger"]}; }}
.ct-insight-warning {{ border-left-color: {T["warning"]}; }}
.ct-insight-success {{ border-left-color: {T["success"]}; }}
.ct-insight b {{ color: {T["text"]}; }}
.ct-insight .ct-it {{ font-weight: 600; font-size: 14px; color: {T["text"]}; margin-bottom: 2px; }}
.ct-insight .ct-ib {{ font-size: 13px; color: {T["text_muted"]}; line-height: 1.5; }}

/* ---- alerts ---- */
.ct-alert {{
    border-radius: var(--ct-r-sm); padding: 12px 16px;
    margin-bottom: 8px; border-left: 3px solid;
    font-size: 13px; line-height: 1.5;
}}
.ct-alert strong {{ display: block; font-size: 14px; margin-bottom: 2px; }}
.ct-alert-danger  {{ background: {T["danger_tint"]};  border-left-color: {T["danger"]};  color: {T["text"]}; }}
.ct-alert-warning {{ background: {T["warning_tint"]}; border-left-color: {T["warning"]}; color: {T["text"]}; }}
.ct-alert-info    {{ background: #E8F1FB;             border-left-color: {T["primary"]}; color: {T["text"]}; }}

/* ---- story card (Executive Story) ---- */
.ct-story {{
    background: {T["surface"]}; border: 1px solid {T["border"]};
    border-radius: var(--ct-r-md); padding: 20px 24px;
    margin-bottom: 16px; box-shadow: var(--ct-shadow-sm);
}}
.ct-story h3 {{ color: {T["text"]}; margin-top: 0; font-size: 18px; }}
.ct-story p  {{ color: {T["text_muted"]}; font-size: 14px; line-height: 1.6; }}
.ct-story b  {{ color: {T["text"]}; }}

/* ---- flow steps (lineage) ---- */
.ct-flow {{
    display: flex; align-items: center; justify-content: center;
    gap: 0; flex-wrap: wrap; margin: 16px 0;
}}
.ct-flow-step {{
    background: {T["surface"]}; border: 1px solid {T["border"]};
    border-radius: var(--ct-r-sm); padding: 10px 16px; text-align: center;
    min-width: 130px; box-shadow: var(--ct-shadow-sm);
    transition: transform .15s ease, box-shadow .15s ease;
}}
.ct-flow-step:hover {{
    transform: translateY(-2px); box-shadow: var(--ct-shadow-md);
}}
.ct-flow-step.ct-flow-final {{
    border-color: {T["primary"]}; background: var(--ct-primary-soft);
}}
.ct-flow-step .ct-fs-icon {{ font-size: 20px; margin-bottom: 4px; }}
.ct-flow-step .ct-fs-title {{ font-size: 13px; font-weight: 600; color: {T["text"]}; }}
.ct-flow-step .ct-fs-desc  {{ font-size: 11px; color: {T["text_muted"]}; }}
.ct-flow-arrow {{ color: {T["primary"]}; font-size: 18px; font-weight: 700; padding: 0 6px; }}
@media (max-width: 768px) {{
    .ct-flow {{ flex-direction: column; }}
    .ct-flow-arrow {{ transform: rotate(90deg); }}
}}

/* ---- outcome card (Executive Story) ---- */
.ct-outcome {{
    background: {T["surface"]}; border: 1px solid {T["border"]};
    border-radius: var(--ct-r-sm); padding: 16px; text-align: center;
    box-shadow: var(--ct-shadow-sm); margin-bottom: 12px;
}}
.ct-outcome .ct-oc-title {{ font-size: 14px; font-weight: 600; color: {T["text"]}; }}
.ct-outcome .ct-oc-desc  {{ font-size: 12px; color: {T["text_muted"]}; margin-top: 4px; }}

/* ---- metric row (ontology) ---- */
.ct-mrow {{
    display: flex; gap: 8px; align-items: center;
    background: {T["surface"]}; border: 1px solid {T["border"]};
    border-radius: var(--ct-r-sm); padding: 8px 16px; margin-bottom: 6px;
}}
.ct-mrow-name {{ flex: 1; font-size: 14px; font-weight: 600; color: {T["text"]}; }}
.ct-mrow-owner {{ font-size: 12px; color: {T["text_muted"]}; }}

/* ---- copilot messages ---- */
.ct-cpmsg {{
    display: flex; gap: 10px; align-items: flex-start;
    padding: 10px 14px; margin-bottom: 6px;
    background: {T["surface"]}; border: 1px solid {T["border"]};
    border-radius: var(--ct-r-md);
}}
.ct-cpmsg .ct-cp-avatar {{
    width: 28px; height: 28px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; flex-shrink: 0;
}}
.ct-cpmsg .ct-cp-avatar.user {{ background: #E8F1FB; }}
.ct-cpmsg .ct-cp-avatar.ai   {{ background: {T["success_tint"]}; }}
.ct-cpmsg .ct-cp-text {{ font-size: 13px; color: {T["text"]}; line-height: 1.5; }}
.ct-cpmsg .ct-cp-text b {{ color: {T["text"]}; }}

/* ---- typing indicator ---- */
@keyframes ct-dot-pulse {{ 0%,80%,100%{{opacity:.3}} 40%{{opacity:1}} }}
.ct-typing {{ display: inline-flex; gap: 4px; padding: 8px 0; }}
.ct-typing span {{
    width: 8px; height: 8px; border-radius: 50%;
    background: {T["text_muted"]}; animation: ct-dot-pulse 1.2s infinite;
}}
.ct-typing span:nth-child(2) {{ animation-delay: .15s; }}
.ct-typing span:nth-child(3) {{ animation-delay: .3s; }}

/* ---- skeleton shimmer ---- */
@keyframes ct-shimmer {{
    0% {{ background-position: -200px 0; }}
    100% {{ background-position: calc(200px + 100%) 0; }}
}}
.ct-skel {{
    background: linear-gradient(90deg, {T["bg"]} 0%, #E8ECF1 50%, {T["bg"]} 100%);
    background-size: 200px 100%;
    animation: ct-shimmer 1.5s infinite;
    border-radius: var(--ct-r-sm);
}}
.ct-skel-kpi {{ height: 120px; }}
.ct-skel-chart {{ height: 340px; }}
.ct-skel-text {{ height: 16px; margin-bottom: 8px; width: 80%; }}

/* ---- enhanced table wrapper ---- */
.ct-table-toolbar {{
    display: flex; gap: var(--ct-s2); align-items: center;
    margin-bottom: var(--ct-s2); flex-wrap: wrap;
}}
.ct-table-toolbar .ct-table-count {{
    font-size: 12px; color: {T["text_muted"]}; margin-left: auto;
}}

/* ---- Plotly container overrides ---- */
[data-testid="stPlotlyChart"] {{ background: transparent !important; }}

/* ---- dataframe / table ---- */
[data-testid="stDataFrame"] {{
    font-size: 13px;
    border-radius: var(--ct-r-sm);
    border: 1px solid {T["border"]};
    overflow: hidden;
}}

/* ---- expanders ---- */
[data-testid="stExpander"] {{
    border-radius: var(--ct-r-sm);
    border: 1px solid {T["border"]};
}}
[data-testid="stExpander"] summary {{ font-weight: 600; }}

/* ---- inputs ---- */
[data-testid="stMultiSelect"], [data-testid="stSelectbox"],
[data-testid="stTextInput"] {{
    font-size: 14px;
}}
input:focus-visible, select:focus-visible, textarea:focus-visible {{
    outline: 2px solid {T["primary"]}; outline-offset: 2px;
}}
button {{ border-radius: var(--ct-r-sm) !important; }}

/* ---- responsive grid utility ---- */
.ct-grid {{
    display: grid; gap: var(--ct-s4);
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}}

/* ---- hide deploy button ---- */
.stDeployButton {{ display: none !important; }}

/* ---- reduced motion ---- */
@media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{ transition: none !important; animation: none !important; }}
}}

/* ---- focus ---- */
*:focus-visible {{
    outline: 2px solid {T["primary"]}; outline-offset: 2px;
}}

/* ---- footer ---- */
.ct-footer {{
    text-align: center; font-size: 12px; color: {T["text_muted"]};
    padding: 24px 0 8px 0; margin-top: 32px;
    border-top: 1px solid {T["border"]};
}}
</style>"""
