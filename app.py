import streamlit as st
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.database import init_db
from utils.ui import render_sidebar
from pages.home import render_home_page
from pages.submit_complaint import render_submit_complaint_page
from pages.dashboard import render_dashboard_page
from pages.history import render_history_page

st.set_page_config(
    page_title="SENTINEL - Manipal Dubai Campus Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    # Initialize SQLite database schema
    init_db()

    # Render branded sidebar and get active page route
    active_page = render_sidebar()

    # Page Router
    if active_page == "Home":
        render_home_page()
    elif active_page == "Submit Complaint":
        render_submit_complaint_page()
    elif active_page == "Dashboard":
        render_dashboard_page()
    elif active_page == "History":
        render_history_page()
    else:
        render_home_page()

if __name__ == "__main__":
    main()
