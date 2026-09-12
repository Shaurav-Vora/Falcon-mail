import streamlit as st
from utils.ui import render_global_header
from nlp.pipeline import process_complaint
from config import DEFAULT_DUPLICATE_THRESHOLD, CATEGORIES

def render_submit_complaint_page():
    """Render Page 2: Submit Complaint with chip suggestions, tips, and AI breakdown."""
    render_global_header("Submit Complaint")
    
    # 1. HERO BANNER
    st.markdown(
        """
        <div class="hero-banner" style="padding: 1.25rem 2rem; margin-bottom: 1.5rem;">
            <div class="hero-title" style="font-size: 1.6rem;">Submit a <span>Complaint</span></div>
            <div class="hero-subtitle" style="font-size: 1rem;">Speak up for a better campus.</div>
            <div class="hero-supporting">Describe your issue in detail. Our AI will analyze and categorize it automatically.</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Check if a submission result was just generated
    last_sub = st.session_state.get("last_submission_result")
    if last_sub:
        render_submission_result_view(last_sub)
        return

    # 2. BALANCED 65% / 35% TWO-COLUMN LAYOUT
    col_left, col_right = st.columns([0.65, 0.35], gap="large")
    
    with col_left:
        # Form Header
        st.markdown(
            """
            <div style="font-size: 1.15rem; font-weight: 700; color: #17233C; margin-bottom: 2px;">
                Complaint Details
            </div>
            <div style="font-size: 0.82rem; color: #64748B; margin-bottom: 12px;">
                Provide as much detail as possible for a quicker resolution.
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Suggestion Chips Section
        st.markdown("<div style='font-size: 0.8rem; font-weight: 600; color: #64748B; margin-bottom: 6px;'>Example issue suggestions (Click to insert):</div>", unsafe_allow_html=True)
        
        chip_cols1 = st.columns(3)
        chip_text = None
        
        with chip_cols1[0]:
            if st.button("AC not working", key="chip_ac", type="secondary", use_container_width=True):
                chip_text = "The air conditioner in Room 204 has stopped working and the room is getting very warm."
            
        with chip_cols1[1]:
            if st.button("Wi-Fi issue", key="chip_wifi", type="secondary", use_container_width=True):
                chip_text = "The Wi-Fi in Computer Lab 3 keeps disconnecting every few minutes during lectures."
            
        with chip_cols1[2]:
            if st.button("Cleanliness", key="chip_clean", type="secondary", use_container_width=True):
                chip_text = "Restroom near the main cafeteria has not been cleaned since yesterday morning."
                
        chip_cols2 = st.columns(3)
        with chip_cols2[0]:
            if st.button("Library facilities", key="chip_lib", type="secondary", use_container_width=True):
                chip_text = "The study room power outlets in the library 2nd floor are damaged and not supplying power."
            
        with chip_cols2[1]:
            if st.button("Hostel maintenance", key="chip_hostel", type="secondary", use_container_width=True):
                chip_text = "The shower drain in male hostel block 2 is clogged causing water pooling."
            
        with chip_cols2[2]:
            if st.button("Classroom equipment", key="chip_projector", type="secondary", use_container_width=True):
                chip_text = "The projector in Lecture Hall 1 is flickering and presentation starts in 20 minutes."

        if chip_text:
            st.session_state["complaint_input_value"] = chip_text

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

        # Main Complaint Form
        with st.form("detailed_complaint_form", clear_on_submit=False):
            initial_val = st.session_state.get("complaint_input_value", "")
            
            st.markdown("<div style='font-size: 0.85rem; font-weight: 600; color: #17233C; margin-bottom: 4px;'>Describe your issue *</div>", unsafe_allow_html=True)
            complaint_text = st.text_area(
                "Describe your issue *",
                value=initial_val,
                height=140,
                placeholder="E.g., Describe the issue you're facing on campus...",
                label_visibility="collapsed"
            )
            
            st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)
            
            # Location + Category Inputs
            col_opt1, col_opt2 = st.columns(2)
            with col_opt1:
                st.markdown("<div style='font-size: 0.82rem; font-weight: 600; color: #17233C; margin-bottom: 4px;'>Location (Optional)</div>", unsafe_allow_html=True)
                optional_loc = st.text_input("Location (Optional)", placeholder="e.g. Room 204, Block A", label_visibility="collapsed")
                st.markdown("<div style='font-size: 11px; color: #94A3B8; margin-top: 2px;'>Room, block, building, or area</div>", unsafe_allow_html=True)
                
            with col_opt2:
                st.markdown("<div style='font-size: 0.82rem; font-weight: 600; color: #17233C; margin-bottom: 4px;'>Category (Optional Context)</div>", unsafe_allow_html=True)
                optional_cat = st.selectbox("Category (Optional Context)", ["Automatic AI Selection"] + CATEGORIES, label_visibility="collapsed")
                st.markdown("<div style='font-size: 11px; color: #94A3B8; margin-top: 2px;'>AI will still predict the most appropriate category automatically.</div>", unsafe_allow_html=True)

            st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

            # File Uploader
            st.markdown("<div style='font-size: 0.82rem; font-weight: 600; color: #17233C; margin-bottom: 2px;'>Attach a file (Optional)</div><div style='font-size: 11px; color: #94A3B8; margin-bottom: 6px;'>Images, PDFs or documents</div>", unsafe_allow_html=True)
            uploaded_doc = st.file_uploader("Attach file", type=["jpg", "png", "pdf", "docx"], label_visibility="collapsed")
            
            st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)

            # Analyze & Submit Button (Right-aligned, strong CTA)
            btn_space, btn_action = st.columns([0.5, 0.5])
            with btn_action:
                submit_btn = st.form_submit_button("Analyze & Submit Complaint", use_container_width=True)

        if submit_btn:
            if not complaint_text or not complaint_text.strip():
                st.error("Please enter a complaint description.")
            else:
                full_text = complaint_text
                if optional_loc:
                    full_text += f" Location: {optional_loc}"
                    
                with st.spinner("Running SENTINEL NLP Analysis..."):
                    try:
                        res = process_complaint(full_text, store_in_db=True, duplicate_threshold=DEFAULT_DUPLICATE_THRESHOLD)
                        st.session_state["last_submission_result"] = res
                        st.session_state["complaint_input_value"] = ""
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to process complaint: {str(e)}")

    with col_right:
        # CARD 1: REPORTING TIPS (Compact, zero raw HTML)
        with st.container(border=True):
            st.markdown("<div style='font-size: 0.98rem; font-weight: 700; color: #17233C; margin-bottom: 2px;'>Reporting Tips</div><div style='font-size: 0.78rem; color: #64748B; margin-bottom: 12px;'>A few tips to help us understand and resolve your issue faster.</div>", unsafe_allow_html=True)
            
            tips = [
                ("1", "Be specific", "Explain what happened and how it affects you."),
                ("2", "Include location", "Mention the room, block, building, or campus area."),
                ("3", "Include timing", "Mention when the issue started or when it occurred."),
                ("4", "Add relevant details", "Include anything that may help the responsible team resolve it faster.")
            ]
            
            for num, title, desc in tips:
                st.markdown(
                    f"<div style='display:flex; align-items:flex-start; gap:10px; margin-bottom:10px;'>"
                    f"<span style='background:#FFF1E8; color:#F15A24; font-weight:700; font-size:12px; width:22px; height:22px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0;'>{num}</span>"
                    f"<div><div style='font-size:13px; font-weight:600; color:#17233C; line-height:1.2;'>{title}</div>"
                    f"<div style='font-size:12px; color:#64748B; line-height:1.3;'>{desc}</div></div>"
                    f"</div>",
                    unsafe_allow_html=True
                )

        st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

        # CARD 2: HOW AI HELPS (Compact, zero raw HTML)
        with st.container(border=True):
            st.markdown("<div style='font-size: 0.98rem; font-weight: 700; color: #17233C; margin-bottom: 2px;'>How AI Helps</div><div style='font-size: 0.78rem; color: #64748B; margin-bottom: 12px;'>Our AI automatically analyzes your complaint to:</div>", unsafe_allow_html=True)
            
            ai_features = [
                ("Category Detection", "Identifies the most relevant complaint category."),
                ("Urgency Detection", "Estimates the priority of the complaint."),
                ("Location Extraction", "Finds room, block, building, or area information."),
                ("Duplicate Detection", "Checks for similar complaints already submitted."),
                ("Summary Generation", "Creates a short structured summary.")
            ]
            
            for title, desc in ai_features:
                st.markdown(
                    f"<div style='display:flex; align-items:flex-start; gap:8px; margin-bottom:9px;'>"
                    f"<span style='color:#F15A24; font-size:13px; line-height:1.3; font-weight:700;'>•</span>"
                    f"<div><div style='font-size:13px; font-weight:600; color:#17233C; line-height:1.2;'>{title}</div>"
                    f"<div style='font-size:11.5px; color:#64748B; line-height:1.3;'>{desc}</div></div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                
            st.markdown(
                "<div style='background:#FFF7F2; border:1px solid #FED7C2; border-radius:8px; padding:8px 12px; text-align:center; font-size:12px; font-weight:700; color:#C2410C; margin-top:8px;'>"
                "Smarter insights. Faster resolution."
                "</div>",
                unsafe_allow_html=True
            )

def render_submission_result_view(result: dict):
    """Render successful submission breakdown card."""
    st.success(f"Complaint Record **#{result['complaint_id']}** Successfully Saved to Database!")
    
    st.markdown("### SENTINEL AI Processing Results")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-icon-box stat-icon-orange">📁</div>
                <div>
                    <div class="stat-label">Category</div>
                    <div style="font-size: 1.15rem; font-weight: 800; color: #F15A24;">{result['category']}</div>
                    <div style="font-size: 0.75rem; color: #94A3B8;">{result['category_confidence']*100:.1f}% confidence</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c2:
        urg = result['urgency']
        u_cls = "stat-icon-red" if urg in ["Critical", "High"] else ("stat-icon-amber" if urg == "Medium" else "stat-icon-green")
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-icon-box {u_cls}">⚠️</div>
                <div>
                    <div class="stat-label">Urgency</div>
                    <div style="font-size: 1.15rem; font-weight: 800; color: #17233C;">{urg}</div>
                    <div style="font-size: 0.75rem; color: #94A3B8;">{result['urgency_confidence']*100:.1f}% confidence</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c3:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-icon-box stat-icon-blue">📍</div>
                <div>
                    <div class="stat-label">Location</div>
                    <div style="font-size: 1.1rem; font-weight: 700; color: #17233C;">{result['entities']['location']}</div>
                    <div style="font-size: 0.75rem; color: #94A3B8;">Extracted by NLP</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c4:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-icon-box stat-icon-green">🏢</div>
                <div>
                    <div class="stat-label">Department</div>
                    <div style="font-size: 0.95rem; font-weight: 700; color: #17233C;">{result['recommended_department']}</div>
                    <div style="font-size: 0.75rem; color: #94A3B8;">Assigned Unit</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)
    st.markdown("#### Executive Summary")
    st.info(result["summary"])
    
    dup = result["duplicate"]
    if dup.get("is_duplicate"):
        st.warning(f"Duplicate Alert: Similar to existing Complaint #{dup.get('matched_id')} (Similarity: {dup.get('similarity')*100:.1f}%).\nMatched Text: \"{dup.get('matched_text')}\"")
    else:
        st.success("Unique Incident: No duplicate complaints detected in database.")
        
    st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)
    
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("Submit Another Complaint", use_container_width=True):
            st.session_state["last_submission_result"] = None
            st.rerun()
            
    with btn_col2:
        if st.button("Go to Dashboard", use_container_width=True):
            st.session_state["last_submission_result"] = None
            st.session_state["nav_page"] = "Dashboard"
            st.rerun()


