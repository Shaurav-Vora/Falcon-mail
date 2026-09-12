"""
SENTINEL - Administrator Operations Dashboard & Campus Analytics
Provides campus-wide incident analytics, category distributions, priority breakdowns,
and near-real-time synchronization for facility managers and campus administration.

SECURITY DIRECTIVE:
Enforces actor.is_admin == True server-side. Students are never permitted access.
"""

import pandas as pd
import plotly.express as px
import streamlit as st
from database.database import get_repository
from utils.auth import get_current_user
from utils.ui import render_global_header


@st.fragment(run_every="2s")
def render_dashboard_live_kpis(user, repo):
    """Near-real-time synchronization fragment for campus KPIs."""
    try:
        stats = repo.get_dashboard_stats(actor=user)
        recent_complaints = repo.get_recent_complaints(actor=user, limit=50)
    except PermissionError as pe:
        st.error(f"Authorization Error: {pe}")
        return
    except Exception as e:
        st.error(f"Cloud storage connection error: {e}")
        return

    col_k1, col_k2, col_k3, col_k4 = st.columns(4)

    with col_k1:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-icon-box stat-icon-orange">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F15A24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    </svg>
                </div>
                <div class="stat-content">
                    <div class="stat-label">Total Complaints</div>
                    <div class="stat-value">{stats.get('total', 0)}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_k2:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-icon-box stat-icon-amber">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"></circle>
                        <polyline points="12 6 12 12 16 14"></polyline>
                    </svg>
                </div>
                <div class="stat-content">
                    <div class="stat-label">Open Incidents</div>
                    <div class="stat-value">{stats.get('open', 0)}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_k3:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-icon-box stat-icon-red">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#EF4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                        <line x1="12" y1="9" x2="12" y2="13"></line>
                        <line x1="12" y1="17" x2="12.01" y2="17"></line>
                    </svg>
                </div>
                <div class="stat-content">
                    <div class="stat-label">Critical Incidents</div>
                    <div class="stat-value">{stats.get('critical', 0)}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_k4:
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
                    <div class="stat-label">Resolved Cases</div>
                    <div class="stat-value">{stats.get('resolved', 0)}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)

    if not recent_complaints:
        st.info("No complaint data currently recorded. New submissions will appear here automatically.")
        return

    df = pd.DataFrame(recent_complaints)

    # Visual Breakdown Charts
    chart_col1, chart_col2 = st.columns([1, 1], gap="medium")

    with chart_col1:
        st.markdown("##### Category Distribution")
        cat_counts = df["category"].value_counts().reset_index()
        cat_counts.columns = ["Category", "Count"]
        fig_cat = px.bar(
            cat_counts,
            x="Category",
            y="Count",
            color="Category",
            color_discrete_sequence=px.colors.qualitative.Prism,
        )
        fig_cat.update_layout(height=280, showlegend=False, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_cat, use_container_width=True, config={"displayModeBar": False})

    with chart_col2:
        st.markdown("##### Priority Breakdown")
        urg_counts = df["urgency"].value_counts().reset_index()
        urg_counts.columns = ["Priority", "Count"]
        color_map = {
            "Critical": "#dc2626",
            "High": "#ea580c",
            "Medium": "#f59e0b",
            "Low": "#2563eb",
        }
        fig_urg = px.pie(
            urg_counts,
            values="Count",
            names="Priority",
            color="Priority",
            color_discrete_map=color_map,
            hole=0.45,
        )
        fig_urg.update_layout(height=280, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_urg, use_container_width=True, config={"displayModeBar": False})


def render_dashboard_page():
    """Entry point for Administrator Operations Dashboard."""
    user = get_current_user()
    if not user or not user.is_admin:
        st.error("Access Denied: Administrator privileges are required to view campus analytics.")
        return

    render_global_header("Operations Dashboard")
    st.markdown(
        """
        <div class="hero-banner" style="padding: 1.25rem 2rem; margin-bottom: 1.5rem;">
            <div style="font-size: 0.85rem; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.2rem;">CAMPUS OPERATIONS INTELLIGENCE</div>
            <div class="hero-title" style="font-size: 1.65rem; color: #17233C; margin-bottom: 0.2rem;">Manipal Campus Live <span>Command Center</span></div>
            <div class="hero-supporting">Near-real-time Firestore synchronization and incident KPIs.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        repo = get_repository()
    except Exception as e:
        st.error(f"Cloud storage connection error: {e}")
        return

    render_dashboard_live_kpis(user, repo)
