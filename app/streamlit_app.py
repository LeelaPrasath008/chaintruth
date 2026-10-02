"""ChainTruth — entry point.

Dual-mode: landing page for mode selection, then grouped st.navigation.
Page content lives in pages/*.py; this file has no analytics logic.
"""
import streamlit as st
from utils.theme import apply_theme
from utils.components import sidebar_brand
from utils.landing import render_landing, render_sidebar_mode_info
from utils.tour import render_tour_banner

st.set_page_config(
    page_title="ChainTruth",
    page_icon=":material/hub:",
    layout="wide",
)
apply_theme()

# ---------- Landing page (no mode selected) ----------
if "app_mode" not in st.session_state:
    render_landing()
    st.stop()

# ---------- App mode active — show sidebar + navigation ----------
sidebar_brand()
render_sidebar_mode_info()

# Start Guided Demo button in sidebar (demo mode only)
if st.session_state.get("app_mode") == "demo" and "tour_step" not in st.session_state:
    if st.sidebar.button("Start Guided Tour", use_container_width=True, key="start_tour"):
        st.session_state["tour_step"] = 0
        st.rerun()

pg = st.navigation(
    {
        "Overview": [
            st.Page("pages/02_Dashboard.py",
                    title="Dashboard", icon=":material/dashboard:", default=True),
            st.Page("pages/00_Executive_Story.py",
                    title="Executive Story", icon=":material/auto_stories:"),
            st.Page("pages/01_Executive_Summary.py",
                    title="Executive Summary", icon=":material/summarize:"),
        ],
        "Investigate": [
            st.Page("pages/03_Definition_Conflict_Center.py",
                    title="Conflict Center", icon=":material/compare_arrows:"),
            st.Page("pages/04_Supplier_Risk_Analysis.py",
                    title="Supplier Risk", icon=":material/warning:"),
            st.Page("pages/05_AI_Insights.py",
                    title="AI Insights", icon=":material/lightbulb:"),
            st.Page("pages/09_Ask_ChainTruth.py",
                    title="Ask ChainTruth", icon=":material/chat:"),
        ],
        "Govern": [
            st.Page("pages/06_Ontology_Explorer.py",
                    title="Ontology Explorer", icon=":material/account_tree:"),
            st.Page("pages/07_Data_Lineage.py",
                    title="Data Lineage", icon=":material/schema:"),
            st.Page("pages/08_Business_Glossary.py",
                    title="Business Glossary", icon=":material/menu_book:"),
        ],
        "Monitor": [
            st.Page("pages/10_Alert_Center.py",
                    title="Alert Center", icon=":material/notifications:"),
            st.Page("pages/11_Supply_Chain_Network.py",
                    title="Supply Chain Network", icon=":material/hub:"),
            st.Page("pages/12_What_If_Analysis.py",
                    title="What-If Analysis", icon=":material/tune:"),
        ],
    },
    expanded=True,
)

pg.run()
