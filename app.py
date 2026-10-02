"""Falcon Mail Streamlit application."""

import os
import sys
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pages.login import render_login_page
from utils.auth import get_current_user
from utils.ui import inject_custom_css, render_navigation

from pages.submit_complaint import render_submit_complaint_page
from pages.student_complaints import render_student_complaints_page
from pages.notifications import render_notifications_page
from pages.dashboard import render_dashboard_page
from pages.admin_queue import render_admin_queue_page
from pages.corpus import render_corpus_page
from pages.models import render_models_page
from pages.resolved_cases import render_resolved_cases_page

st.set_page_config(
    page_title="Falcon Mail - Campus Tickets",
    page_icon="✉️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
    inject_custom_css()

    current_user = get_current_user()
    if not current_user:
        render_login_page()
        return

    active_page = render_navigation()

    if current_user.is_student:
        if active_page == "Raise a ticket":
            render_submit_complaint_page()
        elif active_page == "My tickets":
            render_student_complaints_page()
        elif active_page == "Notifications":
            render_notifications_page()
        else:
            render_submit_complaint_page()

    elif current_user.is_admin:
        if active_page == "Live tickets":
            render_admin_queue_page()
        elif active_page == "Dashboard":
            render_dashboard_page()
        elif active_page == "Resolved":
            render_resolved_cases_page()
        elif active_page == "Corpus":
            render_corpus_page()
        elif active_page == "Models":
            render_models_page()
        else:
            render_admin_queue_page()
    else:
        render_login_page()


if __name__ == "__main__":
    main()
