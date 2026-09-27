"""
Falcon Mail - Resolved Cases Archive (Admin)
Displays resolved and rejected complaint records with resolution notes,
assignee details, and immutable audit timelines.

SECURITY DIRECTIVE:
Enforces actor.is_admin == True server-side.
"""

import streamlit as st
from database.database import get_repository
from utils.auth import get_current_user
from utils.ui import render_global_header


def render_resolved_cases_page():
    user = get_current_user()
    if not user or not user.is_admin:
        st.error("Access Denied: Administrator privileges required.")
        return

    render_global_header("Resolved")
    st.caption("Review completed tickets, resolution notes, and their audit timelines.")

    try:
        repo = get_repository()
        resolved_cases = repo.get_resolved_cases(actor=user, limit=100)
    except Exception:
        st.error("Falcon Mail could not load resolved tickets. Check the storage connection.")
        return

    if not resolved_cases:
        st.info("No resolved or closed cases found in the archive.")
        return

    st.markdown(f"**Total Closed Incidents: {len(resolved_cases)}**")

    for c in resolved_cases:
        cid = c.get("complaint_id", "N/A")
        status = c.get("status", "Resolved")
        urgency = str(c.get("urgency") or "Pending")
        resolved_time = str(c.get("resolved_at") or c.get("updated_at") or "")[:16].replace("T", " ")
        assignee = str(c.get("assigned_admin_name") or "Staff")

        with st.container(border=True):
            heading, state = st.columns([0.72, 0.28])
            with heading:
                st.caption(f"Ticket #{cid} · Closed {resolved_time or 'time unavailable'}")
                st.markdown(f"#### {c.get('title') or 'Resolved ticket'}")
            with state:
                st.write(f"**{status}** · {urgency}")
            st.write(str(c.get("description") or "No description available."))
            st.success(f"Resolution note from {assignee}")
            st.write(str(c.get("resolution_note") or "No resolution note recorded."))

            with st.expander(f"Audit Trail for #{cid}"):
                try:
                    events = repo.get_complaint_events(cid, actor=user)
                except Exception:
                    st.error("Falcon Mail could not load this ticket's audit timeline.")
                    events = []
                if events:
                    for ev in events:
                        t = str(ev.get("created_at", ""))[:19].replace("T", " ")
                        event_type = str(ev.get("event_type") or "status_update").replace("_", " ").title()
                        st.caption(f"{t or 'Time unavailable'} · {event_type}")
                        st.write(
                            f"{ev.get('actor_name') or 'Staff'}: "
                            f"{ev.get('note') or 'No note provided.'}"
                        )
                else:
                    st.caption("No events recorded.")
