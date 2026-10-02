"""Landing page — shown when no mode is selected."""
import streamlit as st
from utils.theme import T
from utils.db import connect_from_wizard


def render_landing():
    """Render the welcome screen with mode selection."""
    st.markdown(
        f'<div style="text-align:center; padding:48px 0 8px 0;">'
        f'<span style="font-size:52px; font-weight:800; color:{T["primary"]}; letter-spacing:-1.5px;">'
        f'Chain<span style="color:{T["text"]};">Truth</span></span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="text-align:center; color:{T["text_muted"]}; font-size:16px; margin-bottom:36px;">'
        f'Supply Chain Ontology &amp; Governed Conversational Analytics</p>',
        unsafe_allow_html=True,
    )

    # Feature cards
    features = [
        ("Governed Metrics", "Three competing OTIF definitions with canonical flagging"),
        ("Business Ontology", "Entity-relationship model linking suppliers, orders, and shipments"),
        ("Conflict Detection", "Quantify when metric definitions disagree on the same data"),
        ("Conversational Analytics", "Ask questions in natural language, grounded in governed views"),
        ("Revenue Risk Insights", "Identify at-risk revenue from late, short, or overdue orders"),
    ]
    card_html = ""
    for title, desc in features:
        card_html += (
            f'<div style="background:{T["surface"]}; border:1px solid {T["border"]}; '
            f'border-radius:{T["radius"]}; padding:14px 18px; '
            f'box-shadow:{T["shadow"]};">'
            f'<div style="font-size:14px; font-weight:600; color:{T["primary"]};">'
            f'{title}</div>'
            f'<div style="font-size:13px; color:{T["text_muted"]}; margin-top:4px;">{desc}</div>'
            f'</div>'
        )
    st.markdown(
        f'<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px,1fr)); '
        f'gap:12px; max-width:800px; margin:0 auto 36px auto;">{card_html}</div>',
        unsafe_allow_html=True,
    )

    # Mode selection buttons
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Explore Demo", use_container_width=True, type="primary"):
                st.session_state["app_mode"] = "demo"
                st.rerun()
        with c2:
            if st.button("Connect Snowflake", use_container_width=True):
                st.session_state["show_wizard"] = True
                st.rerun()

    # Connection wizard
    if st.session_state.get("show_wizard"):
        st.markdown("---")
        st.markdown(
            f'<div style="text-align:center; font-size:18px; font-weight:600; '
            f'color:{T["text"]}; margin-bottom:16px;">Connect Your Snowflake Account</div>',
            unsafe_allow_html=True,
        )
        col_l, col_m, col_r = st.columns([1, 2, 1])
        with col_m:
            with st.form("snowflake_connect"):
                account = st.text_input("Account", placeholder="org-account.region")
                user = st.text_input("User", placeholder="username")
                password = st.text_input("Password", type="password")
                warehouse = st.text_input("Warehouse", value="CHAINTRUTH_WH")
                database = st.text_input("Database", value="CHAINTRUTH_DB")
                role = st.text_input("Role", value="SYSADMIN")
                submitted = st.form_submit_button("Connect", use_container_width=True, type="primary")
                if submitted:
                    if not account or not user:
                        st.error("Account and User are required.")
                    else:
                        with st.spinner("Connecting to Snowflake..."):
                            if connect_from_wizard(account, user, password, warehouse, database, role):
                                st.success("Connected successfully!")
                                st.rerun()


def render_sidebar_mode_info():
    """Show current mode and switch option in sidebar."""
    mode = st.session_state.get("app_mode", "")
    if mode == "demo":
        st.sidebar.markdown(
            f'<div style="background:rgba(255,255,255,.06); border-radius:6px; '
            f'padding:8px 12px; margin-bottom:8px; font-size:12px; color:{T["sidebar_muted"]};">'
            f'<span style="color:{T["accent"]}; font-weight:600;">DEMO MODE</span><br>'
            f'Using local sample data</div>',
            unsafe_allow_html=True,
        )
    elif mode == "snowflake":
        st.sidebar.markdown(
            f'<div style="background:rgba(255,255,255,.06); border-radius:6px; '
            f'padding:8px 12px; margin-bottom:8px; font-size:12px; color:{T["sidebar_muted"]};">'
            f'<span style="color:{T["success"]}; font-weight:600;">SNOWFLAKE</span><br>'
            f'Connected to live data</div>',
            unsafe_allow_html=True,
        )
    if mode:
        if st.sidebar.button("Switch Mode", use_container_width=True, key="switch_mode"):
            for key in ["app_mode", "show_wizard", "_wizard_conn", "messages", "tour_step"]:
                st.session_state.pop(key, None)
            st.cache_resource.clear()
            st.cache_data.clear()
            st.rerun()
