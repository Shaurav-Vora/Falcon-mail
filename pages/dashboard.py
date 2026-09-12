import streamlit as st
import pandas as pd
import plotly.express as px
from utils.ui import render_global_header
from database.database import get_all_complaints

def render_dashboard_page():
    """Render Page 3: Analytics Dashboard with refined low-data chart behavior and monochrome icons."""
    render_global_header("Dashboard")
    
    # Hero Banner Header
    st.markdown(
        """
        <div class="hero-banner" style="padding: 1.25rem 2rem; margin-bottom: 1.5rem;">
            <div style="font-size: 0.85rem; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.2rem;">ANALYTICS DASHBOARD</div>
            <div class="hero-title" style="font-size: 1.65rem; color: #17233C; margin-bottom: 0.2rem;">A Safer, Better Campus <span>Together</span></div>
            <div class="hero-supporting">Real insights. Real action. Happier tomorrows.</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    all_complaints = get_all_complaints()
    df = pd.DataFrame(all_complaints) if all_complaints else pd.DataFrame()

    if df.empty:
        st.info("No complaint data currently recorded in SQLite database. Submit some complaints first!")
        return

    # 1. TOP 4 KPI CARDS (Professional monochrome vector line icons)
    total_count = len(df)
    open_count = len(df[df['status'] == 'Open'])
    critical_count = len(df[df['urgency'] == 'Critical'])
    resolved_count = len(df[df['status'] == 'Resolved'])

    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
    
    with col_k1:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-icon-box stat-icon-orange">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F15A24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                        <line x1="16" y1="13" x2="8" y2="13"></line>
                        <line x1="16" y1="17" x2="8" y2="17"></line>
                    </svg>
                </div>
                <div class="stat-content">
                    <div class="stat-label">Total Complaints</div>
                    <div class="stat-value">{total_count}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
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
                    <div class="stat-label">Open Complaints</div>
                    <div class="stat-value">{open_count}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
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
                    <div class="stat-label">Critical Priority</div>
                    <div class="stat-value">{critical_count}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
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
                    <div class="stat-label">Resolved Complaints</div>
                    <div class="stat-value">{resolved_count}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)
    
    # 2. 3 ANALYTICS CHARTS GRID (Equal cards, graceful low-data handling)
    chart_col1, chart_col2, chart_col3 = st.columns([1.0, 1.0, 1.0], gap="medium")
    
    with chart_col1:
        with st.container(border=True):
            st.markdown("<div style='font-weight: 700; color:#17233C; font-size: 0.95rem; margin-bottom: 0.5rem;'>Complaints by Category</div>", unsafe_allow_html=True)
            cat_df = df['category'].value_counts().reset_index()
            cat_df.columns = ['Category', 'Count']
            
            fig_cat = px.bar(
                cat_df, x='Category', y='Count',
                color='Count',
                color_continuous_scale=['#FED7C2', '#F15A24']
            )
            
            # Low-data protection: keep single bar restrained
            is_low_cat = len(cat_df) <= 2
            if is_low_cat:
                fig_cat.update_traces(width=0.35)
                
            fig_cat.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                height=250,
                coloraxis_showscale=False,
                xaxis=dict(
                    showgrid=False,
                    tickfont=dict(color="#17233C", size=12),
                    linecolor="#E2E8F0"
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor="#F1F5F9",
                    dtick=1,
                    tickfont=dict(color="#64748B", size=12),
                    title=None
                ),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_cat, use_container_width=True, config={"displayModeBar": False})

    with chart_col2:
        with st.container(border=True):
            st.markdown("<div style='font-weight: 700; color:#17233C; font-size: 0.95rem; margin-bottom: 0.5rem;'>Urgency Distribution</div>", unsafe_allow_html=True)
            urg_df = df['urgency'].value_counts().reset_index()
            urg_df.columns = ['Urgency', 'Count']
            
            color_map = {'Critical': '#EF4444', 'High': '#F97316', 'Medium': '#F59E0B', 'Low': '#16A34A'}
            
            fig_urg = px.pie(
                urg_df, values='Count', names='Urgency',
                hole=0.6,
                color='Urgency',
                color_discrete_map=color_map
            )
            fig_urg.update_traces(
                textposition='inside' if len(urg_df) > 1 else 'none',
                textinfo='percent' if len(urg_df) > 1 else 'none'
            )
            fig_urg.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                height=250,
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.22,
                    xanchor="center",
                    x=0.5,
                    font=dict(size=12, color="#334155")
                ),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_urg, use_container_width=True, config={"displayModeBar": False})

    with chart_col3:
        with st.container(border=True):
            st.markdown("<div style='font-weight: 700; color:#17233C; font-size: 0.95rem; margin-bottom: 0.5rem;'>Most Affected Locations</div>", unsafe_allow_html=True)
            loc_df = df['location'].value_counts().head(5).reset_index()
            loc_df.columns = ['Location', 'Count']
            
            fig_loc = px.bar(
                loc_df, x='Count', y='Location',
                orientation='h',
                color='Count',
                color_continuous_scale=['#FED7C2', '#F15A24']
            )
            
            # Low-data protection: keep single horizontal bar restrained
            is_low_loc = len(loc_df) <= 2
            if is_low_loc:
                fig_loc.update_traces(width=0.35)
                
            fig_loc.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                height=250,
                coloraxis_showscale=False,
                xaxis=dict(
                    showgrid=True,
                    gridcolor="#F1F5F9",
                    dtick=1,
                    tickfont=dict(color="#64748B", size=12),
                    title=None
                ),
                yaxis=dict(
                    showgrid=False,
                    tickfont=dict(color="#17233C", size=12),
                    autorange="reversed",
                    linecolor="#E2E8F0",
                    title=None
                ),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_loc, use_container_width=True, config={"displayModeBar": False})

    st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)

    # 3. RECENT INCIDENT REPORTS (Enclosed in a clean card)
    with st.container(border=True):
        st.markdown("<div style='font-size: 1.05rem; font-weight: 700; color:#17233C; margin-bottom: 0.85rem;'>Recent Incident Reports</div>", unsafe_allow_html=True)
        
        table_df = df[['id', 'complaint_text', 'category', 'urgency', 'location', 'status', 'created_at']].head(10).copy()
        table_df.columns = ['ID', 'Complaint', 'Category', 'Priority', 'Location', 'Status', 'Date']
        table_df['Date'] = table_df['Date'].astype(str).str.slice(0, 10)
        
        st.dataframe(
            table_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn("ID", width="small"),
                "Complaint": st.column_config.TextColumn("Complaint", width="large"),
                "Category": st.column_config.TextColumn("Category", width="medium"),
                "Priority": st.column_config.TextColumn("Priority", width="small"),
                "Location": st.column_config.TextColumn("Location", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Date": st.column_config.TextColumn("Date", width="small"),
            }
        )


