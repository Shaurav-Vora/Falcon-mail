"""
SENTINEL - User Interface Components & Dynamic Role-Based Navigation
Handles CSS styling injection, persistent sidebar collapse/expand toggle,
and dynamic role-specific navigation for Students vs Administrators.
"""

import os
import streamlit as st

STYLE_CSS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "style.css")
LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "manipal_logo.png")


def inject_custom_css():
    """Inject design system CSS with responsive sidebar collapse support."""
    css_content = ""
    if os.path.exists(STYLE_CSS_PATH):
        with open(STYLE_CSS_PATH, "r", encoding="utf-8") as f:
            css_content = f.read()

    is_collapsed = st.session_state.get("sidebar_collapsed", False)
    sidebar_width = "70px" if is_collapsed else "260px"

    dynamic_css = f"""
    <style>
        {css_content}
        
        /* Dynamic Sidebar Width */
        section[data-testid="stSidebar"] {{
            width: {sidebar_width} !important;
            min-width: {sidebar_width} !important;
            max-width: {sidebar_width} !important;
        }}
        .user-role-badge {{
            display: inline-block;
            padding: 0.2rem 0.55rem;
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-radius: 9999px;
            margin-top: 0.25rem;
        }}
        .badge-student {{
            background: #e0f2fe;
            color: #0369a1;
        }}
        .badge-admin {{
            background: #fef2f2;
            color: #b91c1c;
        }}
    </style>
    """
    st.markdown(dynamic_css, unsafe_allow_html=True)


def render_global_header(active_page_name: str = "Home"):
    """Render persistent global top header across all pages."""
    from utils.auth import get_current_user
    user = get_current_user()
    role_label = user.role.upper() if user else "VISITOR"

    st.markdown(
        f"""
        <div class="global-header">
            <div>
                <div class="header-main-title">
                    <span>SENTINEL</span>
                    <span style="font-weight: 400; color: #CBD5E1; font-size: 1.1rem;">|</span>
                    <span style="font-size: 1.05rem; font-weight: 600; color: #F15A24;">{active_page_name}</span>
                </div>
                <div class="header-sub-title">Manipal Academy of Higher Education Dubai Campus</div>
            </div>
            <div style="display: flex; align-items: center; gap: 0.75rem;">
                <span class="user-role-badge {'badge-admin' if user and user.is_admin else 'badge-student'}">{role_label}</span>
                <div class="header-user-avatar" title="{user.full_name if user else 'Account'}">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#F15A24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                        <circle cx="12" cy="7" r="4"></circle>
                    </svg>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar():
    """
    Render dynamic role-based sidebar for authenticated sessions.
    Student Routes:
      - Home
      - Submit Complaint
      - My Complaints
      - Notifications
    Admin Routes:
      - Dashboard
      - Complaint Queue
      - Analytics
      - Resolved Cases
    """
    from utils.auth import get_current_user, logout
    user = get_current_user()

    if not user:
        return "Login"

    if "sidebar_collapsed" not in st.session_state:
        st.session_state["sidebar_collapsed"] = False

    inject_custom_css()
    is_collapsed = st.session_state["sidebar_collapsed"]

    # Role-based menu definition
    if user.is_student:
        nav_items = [
            ("Home", ":material/home:"),
            ("Submit Complaint", ":material/edit_note:"),
            ("My Complaints", ":material/list_alt:"),
            ("Notifications", ":material/notifications:"),
        ]
        valid_page_names = [item[0] for item in nav_items]
        if st.session_state.get("nav_page") not in valid_page_names:
            st.session_state["nav_page"] = "Home"
    else:
        # Admin menu
        nav_items = [
            ("Dashboard", ":material/grid_view:"),
            ("Complaint Queue", ":material/inbox:"),
            ("Analytics", ":material/analytics:"),
            ("Resolved Cases", ":material/task_alt:"),
        ]
        valid_page_names = [item[0] for item in nav_items]
        if st.session_state.get("nav_page") not in valid_page_names:
            st.session_state["nav_page"] = "Dashboard"

    current_page = st.session_state.get("nav_page")

    with st.sidebar:
        # Top Header Bar: Logo & Collapse/Expand Toggle
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
            if st.button("›", key="toggle_expand_btn", help="Expand sidebar", use_container_width=True):
                st.session_state["sidebar_collapsed"] = False
                st.rerun()
            st.markdown("<div style='margin-bottom: 0.8rem;'></div>", unsafe_allow_html=True)

        # Navigation Buttons
        for page_name, icon_name in nav_items:
            is_active = (current_page == page_name)
            btn_type = "primary" if is_active else "secondary"
            btn_key = f"nav_btn_{page_name.lower().replace(' ', '_')}"

            btn_label = icon_name if is_collapsed else page_name
            btn_icon = None if is_collapsed else icon_name

            if st.button(btn_label, icon=btn_icon, type=btn_type, key=btn_key, use_container_width=True, help=page_name):
                if not is_active:
                    st.session_state["nav_page"] = page_name
                    st.rerun()

        # User Profile & Logout Bottom Card
        if not is_collapsed:
            st.markdown("<div style='margin-top: 3rem;'></div>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div style="border-top: 1px solid #E2E8F0; padding-top: 0.85rem; text-align: left;">
                    <div style="font-weight: 700; color: #17233C; font-size: 0.88rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        {user.full_name}
                    </div>
                    <div style="font-size: 0.75rem; color: #64748B;">{user.email}</div>
                    <span class="user-role-badge {'badge-admin' if user.is_admin else 'badge-student'}">{user.role}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)
            if st.button("Sign Out", icon=":material/logout:", key="logout_btn_expanded", use_container_width=True):
                logout()
        else:
            # Collapsed mode icon-only logout
            st.markdown("<div style='margin-top: 3rem;'></div>", unsafe_allow_html=True)
            if st.button(":material/logout:", key="logout_btn_collapsed", help="Sign Out", use_container_width=True):
                logout()

    return st.session_state.get("nav_page", valid_page_names[0])
