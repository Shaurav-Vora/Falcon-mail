"""
SENTINEL - Resolved Cases Archive (Admin)
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

    render_global_header("Resolved Cases")
    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <h2 style="font-size: 1.5rem; font-weight: 700; color: #0f172a; margin-bottom: 0.25rem;">Resolved & Closed Incident Archive</h2>
            <p style="color: #64748b; font-size: 0.9rem;">Historical log of closed campus complaints with resolution notes and full audit timelines.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        repo = get_repository()
        resolved_cases = repo.get_resolved_cases(actor=user, limit=100)
    except Exception as e:
        st.error(f"Error loading resolved cases: {e}")
        return

    if not resolved_cases:
        st.info("No resolved or closed cases found in the archive.")
        return

    st.markdown(f"**Total Closed Incidents: {len(resolved_cases)}**")

    for c in resolved_cases:
        cid = c.get("complaint_id", "N/A")
        status = c.get("status", "Resolved")
        urgency = c.get("urgency", "Medium")
        resolved_time = str(c.get("resolved_at") or c.get("updated_at") or "")[:16].replace("T", " ")
        assignee = c.get("assigned_admin_name", "Staff")

        with st.container():
            st.markdown(
                f"""
                <div class="card-container" style="margin-bottom: 0.75rem; border-left: 4px solid {'#10b981' if status == 'Resolved' else '#64748b'};">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <span style="font-family: monospace; font-weight: 700; color: #64748b; font-size: 0.85rem;">#{cid}</span>
                            <span style="color: #94a3b8; font-size: 0.8rem; margin-left: 0.5rem;">Closed {resolved_time}</span>
                            <h4 style="margin: 0.2rem 0; color: #0f172a; font-size: 1.05rem;">{c.get('title', 'Untitled')}</h4>
                        </div>
                        <span class="badge status-{status.lower()}">{status}</span>
                    </div>
                    <p style="color: #475569; font-size: 0.9rem; margin: 0.35rem 0;">{c.get('description', '')}</p>
                    <div style="background: #f0fdf4; border: 1px solid #bbf7d0; padding: 0.65rem 0.85rem; border-radius: 6px; font-size: 0.85rem; color: #166534; margin: 0.5rem 0;">
                        <strong>Resolution Note by {assignee}:</strong> {c.get('resolution_note', 'No note recorded.')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.expander(f"Audit Trail for #{cid}"):
                events = repo.get_complaint_events(cid, actor=user)
                if events:
                    for ev in events:
                        t = str(ev.get("created_at", ""))[:19].replace("T", " ")
                        st.markdown(f"- **{t}** [{ev.get('event_type')}] by {ev.get('actor_name')}: {ev.get('note')}")
                else:
                    st.caption("No events recorded.")
