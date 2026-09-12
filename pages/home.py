"""
SENTINEL - Student Home Page
Personal landing page for authenticated students.

SECURITY & PRIVACY DIRECTIVE:
1. Student home displays ONLY the student's personal complaints and metrics.
2. Campus-wide complaints, counts, and other students' data are NEVER exposed.
"""

import html
import streamlit as st
from database.database import get_repository
from nlp.pipeline import process_complaint
from utils.auth import get_current_user
from utils.ui import render_global_header


def render_home_page():
    """Render Student Home View with personal metrics and quick complaint submission."""
    user = get_current_user()
    if not user:
        st.warning("Please sign in to access SENTINEL.")
        return

    render_global_header("Home")

    # 1. HERO BANNER
    st.markdown(
        f"""
        <div class="hero-banner">
            <div class="hero-title">Welcome back, <span>{html.escape(user.full_name)}</span></div>
            <div class="hero-subtitle">Report campus issues quickly and track your resolutions in real time.</div>
            <div class="hero-supporting">Student ID: {html.escape(user.student_id or 'N/A')} | {html.escape(user.programme or 'MAHE Dubai')}</div>
            <div class="hero-watermark">
                For a better campus,<br>together.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        repo = get_repository()
        stats = repo.get_dashboard_stats(actor=user)
        my_complaints = repo.get_student_complaints(user.uid, actor=user)
    except Exception as e:
        st.error(f"Cloud connection error: {e}")
        stats = {"total": 0, "open": 0, "in_progress": 0, "resolved": 0}
        my_complaints = []

    # 2. PERSONAL METRICS KPI ROW
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-icon-box stat-icon-orange">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F15A24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    </svg>
                </div>
                <div class="stat-content">
                    <div class="stat-label">My Total Submitted</div>
                    <div class="stat-value">{stats.get('total', 0)}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_s2:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-icon-box stat-icon-blue">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"></circle>
                        <polyline points="12 6 12 12 16 14"></polyline>
                    </svg>
                </div>
                <div class="stat-content">
                    <div class="stat-label">My Open Incidents</div>
                    <div class="stat-value">{stats.get('open', 0)}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_s3:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-icon-box stat-icon-amber">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="12" y1="2" x2="12" y2="6"></line>
                        <line x1="12" y1="18" x2="12" y2="22"></line>
                    </svg>
                </div>
                <div class="stat-content">
                    <div class="stat-label">In Progress</div>
                    <div class="stat-value">{stats.get('in_progress', 0)}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_s4:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-icon-box stat-icon-green">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#16A34A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                        <polyline points="22 4 12 14.01 9 11.01"></polyline>
                    </svg>
                </div>
                <div class="stat-content">
                    <div class="stat-label">My Resolved</div>
                    <div class="stat-value">{stats.get('resolved', 0)}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)

    # 3. MAIN SECTION: QUICK SUBMIT + REAL-TIME AI INSIGHT
    col_left, col_right = st.columns([1.15, 0.85], gap="large")

    with col_left:
        st.markdown(
            """
            <div style="font-size: 1.15rem; font-weight: 700; color: #17233C; margin-bottom: 0.2rem;">
                Submit a Quick Complaint
            </div>
            <div style="font-size: 0.85rem; color: #64748B; margin-bottom: 0.75rem;">
                Describe your issue in detail. Our NLP engine will analyze, route, and assess urgency in real time.
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("home_quick_complaint_form", clear_on_submit=False):
            input_text = st.text_area(
                "Complaint Description",
                height=140,
                placeholder="E.g., Air conditioner not working in Room 204...",
                label_visibility="collapsed",
            )
            st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)
            submit_btn = st.form_submit_button("Analyze & Submit Incident", use_container_width=True, type="primary")

        if submit_btn:
            if not input_text or not input_text.strip():
                st.warning("Please enter a complaint description before submitting.")
            else:
                with st.spinner("Processing complaint through SENTINEL NLP pipeline..."):
                    try:
                        analysis_result = process_complaint(
                            text=input_text,
                            actor=user,
                            repo=repo,
                            store_in_db=True,
                        )
                        st.session_state["latest_analysis"] = analysis_result
                        st.success(f"Complaint #{analysis_result.get('complaint_id')} submitted successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error processing complaint: {str(e)}")

    with col_right:
        st.markdown(
            """
            <div style="font-size: 1.15rem; font-weight: 700; color: #17233C; margin-bottom: 0.2rem;">
                AI Real-Time Insight
            </div>
            <div style="font-size: 0.85rem; color: #64748B; margin-bottom: 0.75rem;">
                Live multi-task NLP analysis generated by SENTINEL models.
            </div>
            """,
            unsafe_allow_html=True,
        )

        latest = st.session_state.get("latest_analysis")

        if not latest:
            st.markdown(
                """
                <div style="background: #FFFFFF; border: 1.5px dashed #CBD5E1; border-radius: 14px; padding: 2.5rem 1.5rem; text-align: center; color: #64748B;">
                    <div style="display: flex; justify-content: center; margin-bottom: 0.6rem;">
                        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                            <line x1="8" y1="21" x2="16" y2="21"></line>
                            <line x1="12" y1="17" x2="12" y2="21"></line>
                        </svg>
                    </div>
                    <div style="font-weight: 700; font-size: 0.98rem; color: #17233C;">Submit a complaint to view AI analysis</div>
                    <div style="font-size: 0.82rem; color: #64748B; margin-top: 0.3rem;">Category, priority, location, and routing recommendations will appear here.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            cat = latest.get("category", "Other")
            urg = latest.get("urgency", "Medium")
            dept = latest.get("department", "General Services")
            loc = latest.get("location", "Campus")

            st.markdown(
                f"""
                <div class="card-container" style="border-left: 4px solid {'#ef4444' if urg == 'Critical' else '#f59e0b'};">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <span style="font-weight: 700; color: #0f172a;">{latest.get('title', 'Analysis Result')}</span>
                        <span class="badge urgency-{urg.lower()}">{urg}</span>
                    </div>
                    <p style="font-size: 0.85rem; color: #475569; margin: 0.25rem 0;">{latest.get('summary', '')}</p>
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 0.5rem; display: flex; flex-direction: column; gap: 0.2rem;">
                        <span>Category: <b>{cat}</b> ({latest.get('category_confidence', 1.0)*100:.1f}%)</span>
                        <span>Routing: <b>{dept}</b></span>
                        <span>Location: <b>{loc}</b></span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)

    # 4. MY RECENT COMPLAINTS TABLE (Personal records only)
    st.markdown("<div style='font-size: 1.1rem; font-weight: 700; color: #17233C; margin-bottom: 0.5rem;'>My Recent Submissions</div>", unsafe_allow_html=True)
    if not my_complaints:
        st.info("You haven't submitted any complaints yet.")
    else:
        recent = my_complaints[:5]
        for c in recent:
            cid = c.get("complaint_id", "N/A")
            status = c.get("status", "Open")
            created = str(c.get("created_at", ""))[:16].replace("T", " ")
            st.markdown(
                f"""
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.6rem 0.8rem; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; margin-bottom: 0.4rem;">
                    <div>
                        <span style="font-family: monospace; font-weight: 700; color: #475569;">#{cid}</span>
                        <span style="margin-left: 0.5rem; color: #0f172a; font-weight: 600;">{c.get('title', 'Untitled')}</span>
                        <span style="margin-left: 0.5rem; color: #94a3b8; font-size: 0.78rem;">{created}</span>
                    </div>
                    <span class="badge status-{status.lower().replace(' ', '-')}">{status}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
