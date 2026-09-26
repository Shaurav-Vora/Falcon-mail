"""
Falcon Mail - Student Tickets View
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
        st.info("You have not raised any tickets yet. Use 'Raise a ticket' to get started.")
        return

    # Filter by status
    status_filter = st.selectbox(
        "Filter by Status",
        ["All", "Processing", "Needs Review", "Open", "In Progress", "Resolved", "Rejected"],
        key="student_status_filter",
    )

    filtered = complaints
    if status_filter != "All":
        filtered = [c for c in complaints if c.get("status") == status_filter]

    st.markdown(f"**Showing {len(filtered)} complaint(s)**")

    for c in filtered:
        cid = c.get("complaint_id", "N/A")
        status = str(c.get("status") or "Processing")
        urgency = str(c.get("urgency") or "Pending")
        created = str(c.get("created_at") or "")[:16].replace("T", " ")

        with st.container(border=True):
            heading, badges = st.columns([0.72, 0.28])
            with heading:
                st.caption(f"Ticket #{cid}")
                st.markdown(f"#### {c.get('title') or 'Ticket update'}")
            with badges:
                st.markdown(f"**{status}** · {urgency}")

            st.write(str(c.get("description") or "No description available."))
            category_column, location_column = st.columns(2)
            with category_column:
                st.caption("Category")
                st.write(str(c.get("category") or "Pending analysis"))
            with location_column:
                st.caption("Location")
                st.write(str(c.get("location") or "Not specified"))

            department_column, submitted_column = st.columns(2)
            with department_column:
                st.caption("Department")
                st.write(str(c.get("department") or "Awaiting routing"))
            with submitted_column:
                st.caption("Submitted")
                st.write(created or "Pending")

            # Show Admin Resolution Note if resolved
            if status in ["Resolved", "Rejected"] and c.get("resolution_note"):
                st.success("Resolution note from administration")
                st.write(str(c.get("resolution_note")))

            # Audit Trail Expander
            with st.expander(f"View Status Timeline for #{cid}"):
                events = repo.get_complaint_events(cid, actor=user)
                if events:
                    for ev in events:
                        ev_time = str(ev.get("created_at", ""))[:19].replace("T", " ")
                        ev_type = ev.get("event_type", "status_update")
                        ev_actor = ev.get("actor_name", "Staff")
                        st.caption(f"{ev_time} · {str(ev_type).replace('_', ' ').title()}")
                        st.write(f"{ev_actor}: {ev.get('note') or 'No note provided.'}")
                else:
                    st.caption("No timeline events recorded yet.")


def render_student_complaints_page():
    """Entry point for student complaints view."""
    user = get_current_user()
    if not user:
        st.warning("Please sign in to view your complaints.")
        return

    render_global_header("My tickets")
    st.caption("Track progress, staff updates, and resolution notes in near real time.")

    try:
        repo = get_repository()
    except Exception as e:
        st.error(f"Cloud storage connection error: {e}")
        return

    render_student_complaints_fragment(user, repo)
