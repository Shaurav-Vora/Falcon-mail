"""
SENTINEL - Student Complaints View ("My Complaints")
Displays all complaints submitted by the authenticated student.

SECURITY & SYNC ARCHITECTURE:
1. Enforces data isolation server-side: queries strictly where reporter_uid == actor.uid.
2. Students can NEVER view another student's complaint records.
3. Live status updates and resolution notes synchronized via @st.fragment(run_every="2s").
"""

import streamlit as st
from database.database import get_repository
from utils.auth import get_current_user
from utils.ui import render_global_header


@st.fragment(run_every="2s")
def render_student_complaints_fragment(user, repo):
    """Near-real-time synchronization fragment for student complaints."""
    try:
        complaints = repo.get_student_complaints(user.uid, actor=user)
    except PermissionError as pe:
        st.error(str(pe))
        return
    except Exception as e:
        st.error(f"Error fetching complaints from cloud: {e}")
        return

    if not complaints:
        st.info("You have not submitted any complaints yet. Use the 'Submit Complaint' page to register an incident.")
        return

    # Filter by status
    status_filter = st.selectbox(
        "Filter by Status",
        ["All", "Open", "In Progress", "Resolved", "Rejected"],
        key="student_status_filter",
    )

    filtered = complaints
    if status_filter != "All":
        filtered = [c for c in complaints if c.get("status") == status_filter]

    st.markdown(f"**Showing {len(filtered)} complaint(s)**")

    for c in filtered:
        cid = c.get("complaint_id", "N/A")
        status = c.get("status", "Open")
        urgency = c.get("urgency", "Medium")
        created = c.get("created_at", "")[:16].replace("T", " ")

        status_class = f"status-{status.lower().replace(' ', '-')}"
        urgency_class = f"urgency-{urgency.lower()}"

        with st.container():
            st.markdown(
                f"""
                <div class="card-container" style="margin-bottom: 1rem; border-left: 4px solid {'#10b981' if status == 'Resolved' else ('#ef4444' if urgency == 'Critical' else '#f59e0b')};">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
                        <div>
                            <span style="font-family: monospace; font-weight: 700; color: #64748b; font-size: 0.85rem;">#{cid}</span>
                            <h4 style="margin: 0.2rem 0 0.4rem 0; color: #0f172a; font-size: 1.05rem;">{c.get('title', 'Untitled')}</h4>
                        </div>
                        <div style="display: flex; gap: 0.4rem;">
                            <span class="badge {status_class}">{status}</span>
                            <span class="badge {urgency_class}">{urgency}</span>
                        </div>
                    </div>
                    <p style="color: #475569; font-size: 0.9rem; margin-bottom: 0.6rem;">{c.get('description', '')}</p>
                    <div style="display: flex; gap: 1.5rem; font-size: 0.8rem; color: #64748b; margin-top: 0.4rem;">
                        <span>Category: <b>{c.get('category', 'Other')}</b></span>
                        <span>Location: <b>{c.get('location', 'Campus')}</b></span>
                        <span>Department: <b>{c.get('department', 'General')}</b></span>
                        <span>Submitted: <b>{created}</b></span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Show Admin Resolution Note if resolved
            if status in ["Resolved", "Rejected"] and c.get("resolution_note"):
                st.markdown(
                    f"""
                    <div style="background: #f0fdf4; border: 1px solid #bbf7d0; padding: 0.75rem 1rem; border-radius: 8px; margin: -0.5rem 0 1rem 0; font-size: 0.88rem; color: #166534;">
                        <strong>Resolution Note from Administration:</strong><br>
                        {c.get('resolution_note')}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Audit Trail Expander
            with st.expander(f"View Status Timeline for #{cid}"):
                events = repo.get_complaint_events(cid, actor=user)
                if events:
                    for ev in events:
                        ev_time = str(ev.get("created_at", ""))[:19].replace("T", " ")
                        ev_type = ev.get("event_type", "status_update")
                        ev_actor = ev.get("actor_name", "Staff")
                        st.markdown(
                            f"- **{ev_time}** — *{ev_type.upper()}* by {ev_actor}: {ev.get('note', '')}"
                        )
                else:
                    st.caption("No timeline events recorded yet.")


def render_student_complaints_page():
    """Entry point for student complaints view."""
    user = get_current_user()
    if not user:
        st.warning("Please sign in to view your complaints.")
        return

    render_global_header("My Complaints")
    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <h2 style="font-size: 1.5rem; font-weight: 700; color: #0f172a; margin-bottom: 0.25rem;">My Submitted Complaints</h2>
            <p style="color: #64748b; font-size: 0.9rem;">Track live progress, investigation updates, and resolution notes in near-real-time.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        repo = get_repository()
    except Exception as e:
        st.error(f"Cloud storage connection error: {e}")
        return

    render_student_complaints_fragment(user, repo)
