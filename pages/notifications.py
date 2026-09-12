"""
SENTINEL - Student In-App Notifications Page
Displays status change alerts, resolution notices, and updates for the student's complaints.

SECURITY & SYNC ARCHITECTURE:
1. Queries strictly where recipient_uid == actor.uid.
2. Near-real-time synchronization via @st.fragment(run_every="2s").
"""

import streamlit as st
from database.database import get_repository
from utils.auth import get_current_user
from utils.ui import render_global_header


@st.fragment(run_every="2s")
def render_notifications_fragment(user, repo):
    """Near-real-time fragment polling notifications."""
    try:
        notifications = repo.get_student_notifications(actor=user)
    except Exception as e:
        st.error(f"Error loading notifications: {e}")
        return

    if not notifications:
        st.info("No notifications yet. You will be alerted when administrators update the status of your complaints.")
        return

    unread_count = sum(1 for n in notifications if not n.get("read"))
    st.markdown(f"**Total Notifications: {len(notifications)}** (Unread: {unread_count})")

    for notif in notifications:
        nid = notif.get("notification_id")
        is_read = notif.get("read", False)
        created = str(notif.get("created_at", ""))[:16].replace("T", " ")
        title = notif.get("title", "Update")
        message = notif.get("message", "")
        cid = notif.get("complaint_id", "")

        bg_color = "#ffffff" if is_read else "#f8fafc"
        border_color = "#e2e8f0" if is_read else "#3b82f6"

        with st.container():
            col1, col2 = st.columns([0.85, 0.15])
            with col1:
                st.markdown(
                    f"""
                    <div style="background: {bg_color}; border: 1px solid {border_color}; border-radius: 8px; padding: 0.85rem; margin-bottom: 0.5rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
                            <strong style="color: #0f172a; font-size: 0.95rem;">{title}</strong>
                            <span style="color: #94a3b8; font-size: 0.75rem;">{created}</span>
                        </div>
                        <p style="color: #475569; font-size: 0.88rem; margin: 0.2rem 0;">{message}</p>
                        <span style="color: #64748b; font-size: 0.75rem;">Reference: #{cid}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col2:
                if not is_read:
                    if st.button("Mark Read", key=f"read_btn_{nid}", use_container_width=True):
                        repo.mark_notification_read(nid, actor=user)
                        st.rerun()


def render_notifications_page():
    user = get_current_user()
    if not user:
        st.warning("Please sign in to view notifications.")
        return

    render_global_header("Notifications")
    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <h2 style="font-size: 1.5rem; font-weight: 700; color: #0f172a; margin-bottom: 0.25rem;">Activity & Status Notifications</h2>
            <p style="color: #64748b; font-size: 0.9rem;">Real-time alerts when your complaints are reviewed, investigated, or resolved.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        repo = get_repository()
    except Exception as e:
        st.error(f"Cloud storage connection error: {e}")
        return

    render_notifications_fragment(user, repo)
