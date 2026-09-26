"""Falcon Mail shared interface shell and role-based navigation."""

import html
import os
import streamlit as st

STYLE_CSS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "style.css")


def inject_custom_css():
    """Inject the restrained Falcon Mail design system."""
    css_content = ""
    if os.path.exists(STYLE_CSS_PATH):
        with open(STYLE_CSS_PATH, "r", encoding="utf-8") as f:
            css_content = f.read()

    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)


def render_global_header(active_page_name: str = "Raise a ticket"):
    """Render a quiet page header with escaped account details."""
    from utils.auth import get_current_user
    user = get_current_user()
    role_label = "Administrator" if user and user.is_admin else "Student"
    safe_page = html.escape(active_page_name)
    safe_name = html.escape(str(user.full_name or user.email or "Account")) if user else "Visitor"

    st.markdown(
        f"""
        <div class="global-header">
            <div>
                <div class="header-main-title">
                    <span>{safe_page}</span>
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 0.84rem; font-weight: 600; color: #17233C;">{safe_name}</div>
                <span class="user-role-badge">{role_label}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_admin_evidence_header(title: str, description: str) -> None:
    """Render the shared heading used by administrator evidence pages."""
    render_global_header(title)
    st.caption(description)
    st.divider()


def render_navigation():
    """Render compact student top navigation or the admin workspace sidebar."""
    from utils.auth import get_current_user, logout
    user = get_current_user()

    if not user:
        return "Login"

    if user.is_student:
        nav_items = [
            ("Raise a ticket", ":material/edit_note:"),
            ("My tickets", ":material/list_alt:"),
            ("Notifications", ":material/notifications:"),
        ]
        valid_page_names = [item[0] for item in nav_items]
        if st.session_state.get("nav_page") not in valid_page_names:
            st.session_state["nav_page"] = "Raise a ticket"

        st.markdown(
            """
            <style>section[data-testid="stSidebar"] { display: none !important; }</style>
            <div class="student-brand-row">
                <div>
                    <div class="student-brand-name">Falcon Mail</div>
                    <div class="student-brand-campus">Manipal Dubai student services</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        current_page = st.session_state["nav_page"]
        with st.container(key="student_nav_row"):
            columns = st.columns([1, 1, 1, 0.72])
            for column, (page_name, icon_name) in zip(columns[:3], nav_items):
                with column:
                    if st.button(
                        page_name,
                        icon=icon_name,
                        type="primary" if current_page == page_name else "secondary",
                        key=f"student_nav_{page_name.lower().replace(' ', '_')}",
                        use_container_width=True,
                    ):
                        st.session_state["nav_page"] = page_name
                        st.rerun()
            with columns[3]:
                if st.button(
                    "Sign out",
                    icon=":material/logout:",
                    key="student_sign_out",
                    use_container_width=True,
                ):
                    logout()
        return st.session_state["nav_page"]

    nav_items = [
        ("Live tickets", ":material/inbox:"),
        ("Dashboard", ":material/grid_view:"),
        ("Corpus", ":material/library_books:"),
        ("Models", ":material/model_training:"),
        ("Resolved", ":material/task_alt:"),
    ]
    valid_page_names = [item[0] for item in nav_items]
    if st.session_state.get("nav_page") not in valid_page_names:
        st.session_state["nav_page"] = "Live tickets"
    current_page = st.session_state["nav_page"]
    safe_name = html.escape(str(user.full_name or user.email or "Administrator"))
    safe_email = html.escape(str(user.email or ""))

    with st.sidebar:
        st.markdown(
            """
            <div class="admin-brand">
                <div class="admin-brand-name">Falcon Mail</div>
                <div class="admin-brand-caption">Operations workspace</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        for page_name, icon_name in nav_items:
            if st.button(
                page_name,
                icon=icon_name,
                type="primary" if current_page == page_name else "secondary",
                key=f"admin_nav_{page_name.lower().replace(' ', '_')}",
                use_container_width=True,
            ):
                st.session_state["nav_page"] = page_name
                st.rerun()

        st.markdown(
            f"""
            <div class="admin-account">
                <div class="admin-account-name">{safe_name}</div>
                <div class="admin-account-email">{safe_email}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Sign out", icon=":material/logout:", key="admin_sign_out", use_container_width=True):
            logout()

    return st.session_state["nav_page"]


def render_sidebar():
    """Compatibility wrapper for older imports."""
    return render_navigation()
