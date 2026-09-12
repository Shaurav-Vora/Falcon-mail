"""
SENTINEL - Main Application Entrypoint & Authentication Router
Manipal Academy of Higher Education Dubai Campus

SECURITY ARCHITECTURE:
1. Unauthenticated sessions are strictly gated at the Login/Registration Portal.
2. Authenticated sessions route into role-specific interfaces (Student vs Administrator).
3. Student navigation has zero access to campus-wide analytics or triage queues.
"""

import os
import sys
import streamlit as st

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pages.login import render_login_page
from utils.auth import get_current_user
from utils.ui import render_sidebar

# Lazy import page views
from pages.home import render_home_page
from pages.submit_complaint import render_submit_complaint_page
from pages.student_complaints import render_student_complaints_page
from pages.notifications import render_notifications_page
from pages.dashboard import render_dashboard_page
from pages.admin_queue import render_admin_queue_page
from pages.resolved_cases import render_resolved_cases_page

st.set_page_config(
    page_title="SENTINEL - Campus Incident Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
    # 1. Authentication Check
    current_user = get_current_user()
    if not current_user:
        render_login_page()
        return

    # 2. Render Role-Based Sidebar Navigation
    active_page = render_sidebar()

    # 3. Secure Role-Based Router
    if current_user.is_student:
        if active_page == "Home":
            render_home_page()
        elif active_page == "Submit Complaint":
            render_submit_complaint_page()
        elif active_page == "My Complaints":
            render_student_complaints_page()
        elif active_page == "Notifications":
            render_notifications_page()
        else:
            render_home_page()

    elif current_user.is_admin:
        if active_page == "Dashboard" or active_page == "Analytics":
            render_dashboard_page()
        elif active_page == "Complaint Queue":
            render_admin_queue_page()
        elif active_page == "Resolved Cases":
            render_resolved_cases_page()
        else:
            render_dashboard_page()
    else:
        render_login_page()


if __name__ == "__main__":
    main()
