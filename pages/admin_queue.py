"""
SENTINEL - Administrator Complaint Queue & Triage Interface
Displays unresolved campus complaints sorted strictly by Priority (Critical -> High -> Medium -> Low),
then oldest first.

SECURITY & CONCURRENCY DIRECTIVE:
1. Enforces actor.is_admin == True server-side.
2. "Assign to Myself" executes via atomic Firestore transaction to prevent race conditions.
3. Status changes to 'Resolved' or 'Rejected' require non-empty resolution notes.
4. Live synchronization via @st.fragment(run_every="2s").
"""

import streamlit as st
from database.database import get_repository
from utils.auth import get_current_user
from utils.ui import render_global_header


@st.fragment(run_every="2s")
def render_admin_queue_fragment(user, repo):
    """Near-real-time fragment for unresolved incident queue."""
    try:
        complaints = repo.get_unresolved_complaints(actor=user)
    except PermissionError as pe:
        st.error(f"Authorization Error: {pe}")
        return
    except Exception as e:
        st.error(f"Error fetching queue from cloud: {e}")
        return

    if not complaints:
        st.success("Triage Queue Empty: All campus incidents have been addressed or resolved!")
        return

    # Category and Urgency Filter Bar
    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
    with col_f1:
        urg_filter = st.selectbox("Priority Filter", ["All", "Critical", "High", "Medium", "Low"], key="q_urg_filter")
    with col_f2:
        cat_filter = st.selectbox("Category Filter", ["All"] + sorted(list(set(c.get("category", "Other") for c in complaints))), key="q_cat_filter")
    with col_f3:
        search_query = st.text_input("Search Queue", placeholder="Search description, location, ID...", key="q_search_text")

    filtered = complaints
    if urg_filter != "All":
        filtered = [c for c in filtered if c.get("urgency") == urg_filter]
    if cat_filter != "All":
        filtered = [c for c in filtered if c.get("category") == cat_filter]
    if search_query.strip():
        q = search_query.strip().lower()
        filtered = [
            c for c in filtered
            if q in c.get("complaint_id", "").lower()
            or q in c.get("description", "").lower()
            or q in c.get("location", "").lower()
            or q in c.get("reporter_name", "").lower()
        ]

    st.markdown(f"**Unresolved Incidents: {len(filtered)} / {len(complaints)} total** (Sorted by Priority $\\rightarrow$ Oldest First)")

    for c in filtered:
        cid = c.get("complaint_id", "N/A")
        status = c.get("status", "Open")
        urgency = c.get("urgency", "Medium")
        category = c.get("category", "Other")
        location = c.get("location", "Campus")
        reporter_name = c.get("reporter_name", "Anonymous")
        student_id = c.get("student_id", "N/A")
        assigned_to = c.get("assigned_admin_name")
        assigned_uid = c.get("assigned_admin_uid")
        created = str(c.get("created_at", ""))[:16].replace("T", " ")

        urgency_border = {
            "Critical": "#dc2626",
            "High": "#ea580c",
            "Medium": "#d97706",
            "Low": "#2563eb",
        }.get(urgency, "#cbd5e1")

        with st.container():
            st.markdown(
                f"""
                <div class="card-container" style="border-left: 5px solid {urgency_border}; margin-bottom: 0.75rem;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <span style="font-family: monospace; font-weight: 700; color: #475569; font-size: 0.85rem;">#{cid}</span>
                            <span style="color: #94a3b8; font-size: 0.8rem; margin-left: 0.5rem;">Submitted {created}</span>
                            <h4 style="margin: 0.2rem 0; color: #0f172a; font-size: 1.05rem;">{c.get('title', 'Untitled Incident')}</h4>
                        </div>
                        <div style="display: flex; gap: 0.4rem;">
                            <span class="badge status-{status.lower().replace(' ', '-')}">{status}</span>
                            <span class="badge urgency-{urgency.lower()}">{urgency}</span>
                        </div>
                    </div>
                    <p style="color: #334155; font-size: 0.92rem; margin: 0.4rem 0;">{c.get('description', '')}</p>
                    <div style="display: flex; flex-wrap: wrap; gap: 1.25rem; font-size: 0.8rem; color: #64748b; margin-top: 0.5rem; background: #f8fafc; padding: 0.5rem; border-radius: 6px;">
                        <span>Reporter: <b>{reporter_name}</b> ({student_id})</span>
                        <span>Category: <b>{category}</b></span>
                        <span>Location: <b>{location}</b></span>
                        <span>Assigned To: <b style="color: {'#0369a1' if assigned_to else '#94a3b8'};">{assigned_to or 'Unassigned'}</b></span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Action Controls in Expander
            with st.expander(f"Manage Incident #{cid}", expanded=False):
                col_act1, col_act2 = st.columns([1, 1])

                with col_act1:
                    # Atomic "Assign to Myself" transaction
                    if not assigned_uid:
                        if st.button("Assign to Myself", key=f"claim_{cid}", type="primary", use_container_width=True):
                            res = repo.assign_complaint(cid, actor=user)
                            if res.get("success"):
                                st.success("Incident assigned to you.")
                                st.rerun()
                            else:
                                st.error(res.get("message", "Failed to claim incident."))
                    elif assigned_uid == user.uid:
                        st.info("Currently assigned to you.")
                    else:
                        st.warning(f"Assigned to {assigned_to}")

                with col_act2:
                    # Status Transition with Mandatory Resolution Note Validation
                    new_status = st.selectbox(
                        "Change Status",
                        ["Open", "In Progress", "Resolved", "Rejected"],
                        index=["Open", "In Progress", "Resolved", "Rejected"].index(status),
                        key=f"status_sel_{cid}",
                    )

                res_note = st.text_area(
                    "Resolution Note / Action Taken",
                    value=c.get("resolution_note") or "",
                    placeholder="Mandatory if resolving or rejecting. Explain corrective actions taken...",
                    key=f"note_{cid}",
                )

                if st.button("Update Incident Status", key=f"update_btn_{cid}", use_container_width=True):
                    try:
                        ok = repo.update_complaint_status(
                            complaint_id=cid,
                            new_status=new_status,
                            actor=user,
                            resolution_note=res_note,
                        )
                        if ok:
                            st.success(f"Status updated to '{new_status}' successfully.")
                            st.rerun()
                        else:
                            st.error("Failed to update status.")
                    except ValueError as ve:
                        st.error(str(ve))
                    except PermissionError as pe:
                        st.error(str(pe))


def render_admin_queue_page():
    user = get_current_user()
    if not user or not user.is_admin:
        st.error("Access Denied: Administrator privileges are required to view the Complaint Queue.")
        return

    render_global_header("Complaint Queue")
    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <h2 style="font-size: 1.5rem; font-weight: 700; color: #0f172a; margin-bottom: 0.25rem;">Operations Triage & Resolution Queue</h2>
            <p style="color: #64748b; font-size: 0.9rem;">Prioritized active complaints with live near-real-time synchronization, atomic staff assignment, and audited resolution workflow.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        repo = get_repository()
    except Exception as e:
        st.error(f"Cloud storage connection error: {e}")
        return

    render_admin_queue_fragment(user, repo)
