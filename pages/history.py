import streamlit as st
import pandas as pd
import html
from utils.ui import render_global_header
from database.database import get_all_complaints, update_complaint_status
from config import CATEGORIES, URGENCY_LEVELS

def render_history_page():
    """Render Page 4: History & Status Management (Searchable, filterable incident history with NLP inspection drawer)."""
    render_global_header("History")
    
    # Hero Header Banner
    st.markdown(
        """
        <div class="hero-banner" style="padding: 1.25rem 2rem; margin-bottom: 1.5rem;">
            <div style="font-size: 0.85rem; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.2rem;">COMPLAINT RECORDS</div>
            <div class="hero-title" style="font-size: 1.65rem; color: #17233C; margin-bottom: 0.2rem;">Track and Manage <span>History</span></div>
            <div class="hero-supporting">Real-time status tracking and AI audit records.</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    all_records = get_all_complaints()
    df = pd.DataFrame(all_records) if all_records else pd.DataFrame()
    
    if df.empty:
        st.info("No complaint history available yet. Submit a complaint from the Submit Complaint page first!")
        return

    # 1. HISTORY KPI CARDS (Professional monochrome vector line icons)
    total_sub = len(df)
    in_prog = len(df[df['status'] == 'In Progress'])
    resolved = len(df[df['status'] == 'Resolved'])
    duplicates = len(df[df['is_duplicate'] == 1])

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-icon-box stat-icon-orange">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F15A24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                        <line x1="16" y1="13" x2="8" y2="13"></line>
                        <line x1="16" y1="17" x2="8" y2="17"></line>
                        <polyline points="10 9 9 9 8 9"></polyline>
                    </svg>
                </div>
                <div class="stat-content">
                    <div class="stat-label">Total Submitted</div>
                    <div class="stat-value">{total_sub}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with k2:
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
                    <div class="stat-label">In Progress</div>
                    <div class="stat-value">{in_prog}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with k3:
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
                    <div class="stat-label">Resolved</div>
                    <div class="stat-value">{resolved}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with k4:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-icon-box stat-icon-amber">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                    </svg>
                </div>
                <div class="stat-content">
                    <div class="stat-label">Duplicates</div>
                    <div class="stat-value">{duplicates}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)
    
    # 2. INTERACTIVE FILTER BAR (Compact, 1 clean row, monochrome icon, outlined reset)
    with st.container(border=True):
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 0.45rem; margin-bottom: 0.5rem;">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#F15A24" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                </svg>
                <span style="font-weight: 700; font-size: 0.92rem; color: #17233C; letter-spacing: -0.01em;">Filter & Search Records</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns([2.0, 1.15, 1.15, 1.15, 0.75], vertical_alignment="center")
        
        with f_col1:
            search_query = st.text_input(
                "Search Keyword / ID / Location",
                placeholder="Search text, ID, location...",
                label_visibility="collapsed",
                key="hist_search_input"
            )
        with f_col2:
            status_filter = st.selectbox(
                "Status Filter",
                ["All Statuses", "Open", "In Progress", "Resolved", "Rejected"],
                label_visibility="collapsed",
                key="hist_status_select"
            )
        with f_col3:
            cat_filter = st.selectbox(
                "Category Filter",
                ["All Categories"] + CATEGORIES,
                label_visibility="collapsed",
                key="hist_cat_select"
            )
        with f_col4:
            urg_filter = st.selectbox(
                "Urgency Filter",
                ["All Urgencies"] + URGENCY_LEVELS,
                label_visibility="collapsed",
                key="hist_urg_select"
            )
        with f_col5:
            st.markdown('<div class="reset-btn-container">', unsafe_allow_html=True)
            reset_btn = st.button("Reset", key="hist_reset_button", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if reset_btn:
                st.session_state["hist_search_input"] = ""
                st.session_state["hist_status_select"] = "All Statuses"
                st.session_state["hist_cat_select"] = "All Categories"
                st.session_state["hist_urg_select"] = "All Urgencies"
                st.rerun()

    st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)

    # Apply Filtering
    filtered_df = df.copy()
    
    if search_query:
        query_str = str(search_query).lower()
        filtered_df = filtered_df[
            filtered_df['complaint_text'].str.lower().str.contains(query_str, na=False) |
            filtered_df['id'].astype(str).str.contains(query_str, na=False) |
            filtered_df['location'].str.lower().str.contains(query_str, na=False)
        ]
        
    if status_filter != "All Statuses":
        filtered_df = filtered_df[filtered_df['status'] == status_filter]
    if cat_filter != "All Categories":
        filtered_df = filtered_df[filtered_df['category'] == cat_filter]
    if urg_filter != "All Urgencies":
        filtered_df = filtered_df[filtered_df['urgency'] == urg_filter]

    # Helper function to truncate summary to ~75 characters to avoid table expansion & date clipping
    def truncate_summary(text, max_len=75):
        if not text or pd.isna(text):
            return "No summary provided"
        s = str(text).strip()
        return s if len(s) <= max_len else s[:max_len-3] + "..."

    # 3. HISTORY TABLE (Full width, intelligent column sizing, no clipping)
    display_df = filtered_df[['id', 'summary', 'category', 'urgency', 'location', 'status', 'created_at']].copy()
    display_df.columns = ['ID', 'Summary', 'Category', 'Urgency', 'Location', 'Status', 'Date']
    display_df['Summary'] = display_df['Summary'].apply(truncate_summary)
    display_df['Date'] = display_df['Date'].astype(str).str.slice(0, 16)
    
    with st.container(border=True):
        st.markdown(
            f"""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.65rem;">
                <span style="font-size: 0.98rem; font-weight: 700; color: #17233C;">Incident Records</span>
                <span style="font-size: 0.8rem; font-weight: 600; color: #64748B;">Showing {len(filtered_df)} of {len(df)} records</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        if display_df.empty:
            st.info("No incident records match your current filter criteria. Click 'Reset' above to view all records.")
        else:
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ID": st.column_config.NumberColumn("ID", width="small"),
                    "Summary": st.column_config.TextColumn("Summary", width="large"),
                    "Category": st.column_config.TextColumn("Category", width="small"),
                    "Urgency": st.column_config.TextColumn("Urgency", width="small"),
                    "Location": st.column_config.TextColumn("Location", width="small"),
                    "Status": st.column_config.TextColumn("Status", width="small"),
                    "Date": st.column_config.TextColumn("Date", width="small"),
                }
            )

    st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)

    # 4. COMPLAINT STATUS MANAGER & FULL AUDIT DRAWER
    complaint_ids = list(filtered_df['id']) if not filtered_df.empty else list(df['id'])
    
    if complaint_ids:
        with st.container(border=True):
            st.markdown(
                """
                <div style="display: flex; align-items: center; gap: 0.45rem; margin-bottom: 0.75rem;">
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#F15A24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="3"></circle>
                        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                    </svg>
                    <span style="font-weight: 700; font-size: 0.98rem; color: #17233C;">Complaint Status Manager</span>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            col_sel, col_stat, col_act = st.columns([1.2, 1.2, 1.0], vertical_alignment="bottom")
            
            with col_sel:
                selected_id = st.selectbox("Select Complaint ID to Inspect:", complaint_ids)
            
            selected_record = df[df['id'] == selected_id].iloc[0].to_dict()
            
            with col_stat:
                current_status = selected_record.get('status', 'Open')
                status_options = ["Open", "In Progress", "Resolved", "Rejected"]
                default_status_idx = status_options.index(current_status) if current_status in status_options else 0
                new_status_selection = st.selectbox("Change Status To:", status_options, index=default_status_idx)
                
            with col_act:
                if st.button("Save Status Update", type="primary", use_container_width=True):
                    if update_complaint_status(int(selected_id), new_status_selection):
                        st.success(f"Status of Complaint #{selected_id} updated to '{new_status_selection}'!")
                        st.rerun()
                    else:
                        st.error("Failed to update status in database.")

        st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)
        
        # 5. COMPLAINT DETAIL PANEL (Complete 10 fields, escaped HTML, no raw code)
        rec_id = selected_record['id']
        rec_date = str(selected_record.get('created_at', ''))[:16]
        rec_status = html.escape(str(selected_record.get('status', 'Open')))
        status_cls = f"badge-{rec_status.lower().replace(' ', '-')}"
        
        raw_complaint_text = html.escape(str(selected_record.get('complaint_text', '')))
        raw_summary = html.escape(str(selected_record.get('summary', 'No summary available.')))
        raw_category = html.escape(str(selected_record.get('category', 'General')))
        raw_urgency = html.escape(str(selected_record.get('urgency', 'Medium')))
        raw_location = html.escape(str(selected_record.get('location', 'Campus Wide')))
        raw_department = html.escape(str(selected_record.get('recommended_department', 'Campus Facilities')))
        
        cat_conf = float(selected_record.get('category_confidence', 0.0) or 0.0) * 100
        urg_conf = float(selected_record.get('urgency_confidence', 0.0) or 0.0) * 100
        cat_conf_str = f"Confidence: {cat_conf:.1f}%" if cat_conf > 0 else "Confidence: Assessed"
        urg_conf_str = f"Confidence: {urg_conf:.1f}%" if urg_conf > 0 else "Confidence: Assessed"
        
        urg_color = "#EF4444" if raw_urgency in ["Critical", "High"] else ("#F59E0B" if raw_urgency == "Medium" else "#16A34A")
        
        is_dup = bool(selected_record.get('is_duplicate'))
        dup_of = selected_record.get('duplicate_of_id')
        dup_text = f"Yes (Matched #{dup_of})" if is_dup and dup_of else ("Yes (Potential Duplicate)" if is_dup else "None (Unique Complaint)")
        dup_color = "#D97706" if is_dup else "#16A34A"

        detail_card_html = f"""
        <div class="sentinel-card-container">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; border-bottom: 1px solid #F1F5F9; padding-bottom: 0.75rem;">
                <div>
                    <span style="font-size: 1.15rem; font-weight: 800; color: #17233C;">Complaint #{rec_id}</span>
                    <span style="margin-left: 0.75rem; font-size: 0.82rem; color: #64748B;">Submitted on {rec_date}</span>
                </div>
                <div>
                    <span class="badge {status_cls}">{rec_status}</span>
                </div>
            </div>
            
            <div style="margin-bottom: 1rem;">
                <div style="font-weight: 700; font-size: 0.75rem; color: #64748B; text-transform: uppercase; letter-spacing: 0.03em; margin-bottom: 0.35rem;">ORIGINAL COMPLAINT TEXT</div>
                <div style="font-size: 0.92rem; color: #17233C; background: #F8FAFC; padding: 0.85rem 1rem; border-radius: 10px; border: 1px solid #E2E8F0; line-height: 1.5;">
                    "{raw_complaint_text}"
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.85rem; margin-bottom: 0.85rem;">
                <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 0.85rem;">
                    <div style="font-weight: 700; font-size: 0.72rem; color: #64748B; text-transform: uppercase; letter-spacing: 0.03em;">CATEGORY</div>
                    <div style="font-weight: 700; color: #F15A24; font-size: 0.95rem; margin-top: 0.2rem;">{raw_category}</div>
                    <div style="font-size: 0.74rem; color: #94A3B8; margin-top: 0.15rem;">{cat_conf_str}</div>
                </div>
                <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 0.85rem;">
                    <div style="font-weight: 700; font-size: 0.72rem; color: #64748B; text-transform: uppercase; letter-spacing: 0.03em;">PRIORITY / URGENCY</div>
                    <div style="font-weight: 700; color: {urg_color}; font-size: 0.95rem; margin-top: 0.2rem;">{raw_urgency}</div>
                    <div style="font-size: 0.74rem; color: #94A3B8; margin-top: 0.15rem;">{urg_conf_str}</div>
                </div>
                <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 0.85rem;">
                    <div style="font-weight: 700; font-size: 0.72rem; color: #64748B; text-transform: uppercase; letter-spacing: 0.03em;">LOCATION</div>
                    <div style="font-weight: 700; color: #3B82F6; font-size: 0.95rem; margin-top: 0.2rem;">{raw_location}</div>
                    <div style="font-size: 0.74rem; color: #94A3B8; margin-top: 0.15rem;">Extracted by NLP</div>
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.85rem; margin-bottom: 0.85rem;">
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 0.85rem;">
                    <div style="font-weight: 700; font-size: 0.72rem; color: #64748B; text-transform: uppercase; letter-spacing: 0.03em;">RECOMMENDED DEPARTMENT</div>
                    <div style="font-size: 0.92rem; font-weight: 600; color: #17233C; margin-top: 0.25rem; display: flex; align-items: center; gap: 0.4rem;">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="4" y="2" width="16" height="20" rx="2" ry="2"></rect>
                            <line x1="9" y1="22" x2="9" y2="2"></line>
                            <line x1="15" y1="22" x2="15" y2="2"></line>
                        </svg>
                        <span>{raw_department}</span>
                    </div>
                </div>
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 0.85rem;">
                    <div style="font-weight: 700; font-size: 0.72rem; color: #64748B; text-transform: uppercase; letter-spacing: 0.03em;">DUPLICATE MATCH</div>
                    <div style="font-size: 0.92rem; font-weight: 600; color: {dup_color}; margin-top: 0.25rem; display: flex; align-items: center; gap: 0.4rem;">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="{dup_color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
                        </svg>
                        <span>{html.escape(dup_text)}</span>
                    </div>
                </div>
            </div>
            
            <div style="background: #FFF3ED; border: 1px solid #FED7C2; border-radius: 10px; padding: 0.85rem 1rem;">
                <div style="display: flex; align-items: center; gap: 0.4rem; font-weight: 700; font-size: 0.72rem; color: #C2410C; text-transform: uppercase; letter-spacing: 0.03em; margin-bottom: 0.25rem;">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#C2410C" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
                    </svg>
                    <span>AI GENERATED SUMMARY</span>
                </div>
                <div style="font-size: 0.92rem; color: #17233C; font-weight: 500; line-height: 1.45;">{raw_summary}</div>
            </div>
        </div>
        """
        
        st.markdown(detail_card_html, unsafe_allow_html=True)
