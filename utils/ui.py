import streamlit as st
import os
import html

STYLE_CSS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "style.css")
LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "manipal_logo.png")

def inject_custom_css():
    """Inject polished design system CSS from assets/style.css with responsive sidebar collapse support."""
    css_content = ""
    if os.path.exists(STYLE_CSS_PATH):
        with open(STYLE_CSS_PATH, "r", encoding="utf-8") as f:
            css_content = f.read()
            
    is_collapsed = st.session_state.get("sidebar_collapsed", False)
    sidebar_width = "70px" if is_collapsed else "250px"
    
    dynamic_css = f"""
    <style>
        {css_content}
        
        /* Dynamic Sidebar Width based on persistent session state */
        section[data-testid="stSidebar"] {{
            width: {sidebar_width} !important;
            min-width: {sidebar_width} !important;
            max-width: {sidebar_width} !important;
        }}
    </style>
    """
    st.markdown(dynamic_css, unsafe_allow_html=True)

def render_global_header(active_page_name: str = "Home"):
    """Render persistent global top header across all pages."""
    st.markdown(
        """
        <div class="global-header">
            <div>
                <div class="header-main-title">
                    <span>SENTINEL</span>
                    <span style="font-weight: 400; color: #CBD5E1; font-size: 1.1rem;">|</span>
                    <span style="font-size: 1.05rem; font-weight: 600; color: #F15A24;">AI Complaint Intelligence</span>
                </div>
                <div class="header-sub-title">Manipal Academy of Higher Education Dubai Campus</div>
            </div>
            <div class="header-user-avatar" title="Campus User Account">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#F15A24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                    <circle cx="12" cy="7" r="4"></circle>
                </svg>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_sidebar():
    """
    Render branded sidebar with custom persistent collapse/expand toggle.
    Guarantees:
    - Collapse/Expand toggle button is ALWAYS visible at the top.
    - Width persists across page navigation (250px expanded vs 70px collapsed).
    - In collapsed state, navigation remains fully functional with icons.
    """
    if "sidebar_collapsed" not in st.session_state:
        st.session_state["sidebar_collapsed"] = False
        
    inject_custom_css()
    is_collapsed = st.session_state["sidebar_collapsed"]
    current_page = st.session_state.get("nav_page", "Home")
    
    with st.sidebar:
        # Top Header Bar in Sidebar: Logo & Collapse/Expand Toggle
        if not is_collapsed:
            col_logo, col_btn = st.columns([0.78, 0.22], vertical_alignment="center")
            with col_logo:
                if os.path.exists(LOGO_PATH):
                    st.image(LOGO_PATH, use_container_width=True)
                else:
                    st.markdown("<div style='font-weight:800; color:#F15A24; font-size:1.1rem;'>MANIPAL</div>", unsafe_allow_html=True)
            with col_btn:
                if st.button("‹", key="toggle_collapse_btn", help="Collapse sidebar", use_container_width=True):
                    st.session_state["sidebar_collapsed"] = True
                    st.rerun()
            st.markdown("<div style='margin-bottom: 1.2rem;'></div>", unsafe_allow_html=True)
        else:
            # Collapsed state header: Always visible Expand button
            if st.button("›", key="toggle_expand_btn", help="Expand sidebar", use_container_width=True):
                st.session_state["sidebar_collapsed"] = False
                st.rerun()
            st.markdown("<div style='margin-bottom: 0.8rem;'></div>", unsafe_allow_html=True)

        # 4 Navigation Items
        nav_items = [
            ("Home", ":material/home:"),
            ("Submit Complaint", ":material/edit_note:"),
            ("Dashboard", ":material/grid_view:"),
            ("History", ":material/history:")
        ]
        
        for page_name, icon_name in nav_items:
            is_active = (current_page == page_name)
            btn_type = "primary" if is_active else "secondary"
            btn_key = f"nav_btn_{page_name.lower().replace(' ', '_')}"
            
            # Label depends on collapsed state: show full label if expanded, icon-only style if collapsed
            btn_label = icon_name if is_collapsed else page_name
            btn_icon = None if is_collapsed else icon_name
            
            if st.button(btn_label, icon=btn_icon, type=btn_type, key=btn_key, use_container_width=True, help=page_name):
                if not is_active:
                    st.session_state["nav_page"] = page_name
                    st.rerun()

        # Footer (visible in expanded mode)
        if not is_collapsed:
            st.markdown("<div style='margin-top: 5rem;'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="border-top: 1px solid #E2E8F0; padding-top: 0.85rem; text-align: left;">
                    <div style="font-weight: 800; color: #17233C; font-size: 0.85rem;">SENTINEL</div>
                    <div style="font-size: 0.75rem; color: #64748B;">AI Incident Intelligence</div>
                    <div style="font-size: 0.72rem; color: #F15A24; margin-top: 0.3rem; font-weight: 600;">
                        For a better campus, together.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    return st.session_state.get("nav_page", "Home")
