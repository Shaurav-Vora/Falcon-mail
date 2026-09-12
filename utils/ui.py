import streamlit as st
import os
import base64

def get_image_base64(image_path: str) -> str:
    """Convert an image file to base64 string for CSS/HTML rendering."""
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    return ""

def inject_custom_css():
    """Inject polished design system CSS matching the Manipal Dubai campus theme."""
    
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "manipal_logo.png")
    
    css = """
    <style>
        /* Import Professional Typography */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #F8FAFC;
            color: #17233C;
        }

        /* Hide Streamlit Default UI Elements and Detached Chevron */
        header[data-testid="stHeader"] { display: none !important; }
        footer { display: none !important; }
        [data-testid="stSidebarNav"] { display: none !important; }
        .stDeployButton { display: none !important; }
        #MainMenu { display: none !important; }
        button[data-testid="stSidebarCollapseButton"],
        div[data-testid="stSidebarCollapseButton"],
        button[data-testid="stSidebarHeaderCollapseButton"] { display: none !important; }

        /* Center Content Container & Enforce Max Width */
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 2.5rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 1240px !important;
            margin: 0 auto !important;
        }

        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #E2E8F0 !important;
            width: 250px !important;
        }
        
        section[data-testid="stSidebar"] .block-container {
            padding-top: 1.5rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }

        /* Top Global Header */
        .global-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 1.2rem;
            margin-bottom: 1.5rem;
            border-bottom: 1px solid #E2E8F0;
        }

        .header-main-title {
            font-size: 1.45rem;
            font-weight: 800;
            color: #17233C;
            letter-spacing: -0.02em;
            margin: 0;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }

        .header-sub-title {
            font-size: 0.82rem;
            color: #64748B;
            margin-top: 0.1rem;
            font-weight: 500;
        }

        .header-user-avatar {
            width: 38px;
            height: 38px;
            border-radius: 50%;
            background-color: #FFF3ED;
            border: 1.5px solid #FED7C2;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #F15A24;
            cursor: pointer;
            transition: all 0.15s ease-in-out;
        }

        .header-user-avatar:hover {
            background-color: #FFEBE0;
            border-color: #F15A24;
        }

        /* Hero Banner Styling */
        .hero-banner {
            background: linear-gradient(135deg, #FFF7F2 0%, #FFEBE0 60%, #FFE2D1 100%);
            border: 1px solid #FED7C2;
            border-radius: 16px;
            padding: 1.75rem 2rem;
            margin-bottom: 1.5rem;
            position: relative;
            box-shadow: 0 2px 8px rgba(241, 90, 36, 0.04);
        }

        .hero-title {
            font-size: 1.85rem;
            font-weight: 800;
            color: #17233C;
            margin-bottom: 0.25rem;
            letter-spacing: -0.02em;
        }

        .hero-title span {
            color: #F15A24;
        }

        .hero-subtitle {
            font-size: 1.05rem;
            font-weight: 600;
            color: #334155;
            margin-bottom: 0.2rem;
        }

        .hero-supporting {
            font-size: 0.875rem;
            color: #64748B;
            font-weight: 500;
        }

        .hero-watermark {
            position: absolute;
            right: 2rem;
            top: 50%;
            transform: translateY(-50%);
            opacity: 0.6;
            text-align: right;
            font-style: italic;
            color: #C2410C;
            font-size: 0.85rem;
            font-family: 'Georgia', serif;
            pointer-events: none;
        }

        /* Stat Cards */
        .stat-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 14px;
            padding: 1.1rem 1.2rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
            min-height: 90px;
            transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        }

        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.08);
            border-color: #CBD5E1;
        }

        .stat-icon-box {
            width: 44px;
            height: 44px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.3rem;
            flex-shrink: 0;
            border: 1px solid transparent;
        }

        .stat-icon-orange { background-color: #FFF3ED; color: #F15A24; border-color: #FED7C2; }
        .stat-icon-red { background-color: #FEF2F2; color: #EF4444; border-color: #FECACA; }
        .stat-icon-green { background-color: #F0FDF4; color: #16A34A; border-color: #DCFCE7; }
        .stat-icon-blue { background-color: #EFF6FF; color: #3B82F6; border-color: #DBEAFE; }
        .stat-icon-amber { background-color: #FFFBEB; color: #F59E0B; border-color: #FDE68A; }

        .stat-label {
            font-size: 0.75rem;
            font-weight: 600;
            color: #64748B;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }

        .stat-value {
            font-size: 1.6rem;
            font-weight: 800;
            color: #17233C;
            line-height: 1.2;
        }

        /* Badges */
        .badge {
            display: inline-block;
            padding: 0.25rem 0.6rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }

        .badge-critical { background-color: #FEE2E2; color: #991B1B; }
        .badge-high { background-color: #FFEDD5; color: #C2410C; }
        .badge-medium { background-color: #FEF3C7; color: #B45309; }
        .badge-low { background-color: #DCFCE7; color: #15803D; }

        .badge-open { background-color: #DBEAFE; color: #1E40AF; }
        .badge-in-progress { background-color: #E0E7FF; color: #3730A3; }
        .badge-resolved { background-color: #DCFCE7; color: #15803D; }
        .badge-rejected { background-color: #F3F4F6; color: #4B5563; }

        /* Primary CTA Submit Button - Main Content */
        .block-container div[data-testid="stFormSubmitButton"] button,
        .block-container div.stButton > button[kind="primary"] {
            background: #F15A24 !important;
            color: #FFFFFF !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            border: none !important;
            border-radius: 9px !important;
            padding: 0.6rem 1.6rem !important;
            box-shadow: 0 2px 6px rgba(241, 90, 36, 0.25) !important;
            transition: all 0.15s ease-in-out !important;
            height: 44px !important;
            min-height: 44px !important;
        }

        .block-container div[data-testid="stFormSubmitButton"] button:hover,
        .block-container div.stButton > button[kind="primary"]:hover {
            background: #D94B1B !important;
            box-shadow: 0 4px 10px rgba(241, 90, 36, 0.35) !important;
        }

        .block-container div[data-testid="stFormSubmitButton"] button p,
        .block-container div.stButton > button[kind="primary"] p {
            color: #FFFFFF !important;
            font-weight: 600 !important;
        }

        /* Suggestion Chip Buttons (Secondary buttons in main container) */
        .block-container div[data-testid="stButton"] button[kind="secondary"],
        .block-container div[data-testid="stButton"] button:not([kind="primary"]) {
            background-color: #FFF7F2 !important;
            color: #C2410C !important;
            border: 1px solid #FED7C2 !important;
            border-radius: 20px !important;
            font-size: 0.82rem !important;
            font-weight: 600 !important;
            height: 36px !important;
            min-height: 36px !important;
            padding: 0.25rem 0.85rem !important;
            box-shadow: none !important;
            width: 100% !important;
            transition: all 0.15s ease-in-out !important;
        }

        .block-container div[data-testid="stButton"] button[kind="secondary"]:hover,
        .block-container div[data-testid="stButton"] button:not([kind="primary"]):hover {
            background-color: #FFEBE0 !important;
            border-color: #F15A24 !important;
            color: #F15A24 !important;
            box-shadow: none !important;
        }

        .block-container div[data-testid="stButton"] button[kind="secondary"] p,
        .block-container div[data-testid="stButton"] button:not([kind="primary"]) p {
            color: #C2410C !important;
            font-weight: 600 !important;
            font-size: 0.82rem !important;
        }

        .block-container div[data-testid="stButton"] button[kind="secondary"]:hover p,
        .block-container div[data-testid="stButton"] button:not([kind="primary"]):hover p {
            color: #F15A24 !important;
        }

        /* Outlined Reset Button */
        .reset-btn-container button,
        .reset-btn-container button[kind="secondary"],
        .reset-btn-container button:not([kind="primary"]) {
            background-color: #FFFFFF !important;
            color: #475569 !important;
            border: 1px solid #CBD5E1 !important;
            border-radius: 8px !important;
            font-size: 0.82rem !important;
            font-weight: 600 !important;
            height: 38px !important;
            min-height: 38px !important;
            padding: 0.2rem 0.6rem !important;
            box-shadow: none !important;
            transition: all 0.15s ease !important;
        }

        .reset-btn-container button:hover,
        .reset-btn-container button[kind="secondary"]:hover,
        .reset-btn-container button:not([kind="primary"]):hover {
            background-color: #F8FAFC !important;
            border-color: #94A3B8 !important;
            color: #0F172A !important;
        }

        .reset-btn-container button p,
        .reset-btn-container button[kind="secondary"] p,
        .reset-btn-container button:not([kind="primary"]) p {
            color: #475569 !important;
            font-size: 0.82rem !important;
            font-weight: 600 !important;
        }

        .reset-btn-container button:hover p,
        .reset-btn-container button[kind="secondary"]:hover p,
        .reset-btn-container button:not([kind="primary"]):hover p {
            color: #0F172A !important;
        }

        /* Textarea Focus & Styling */
        div[data-testid="stTextArea"] textarea {
            border-radius: 10px !important;
            background-color: #FFFFFF !important;
            border: 1px solid #CBD5E1 !important;
            padding: 12px 14px !important;
            font-size: 0.92rem !important;
            color: #17233C !important;
            transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
        }

        div[data-testid="stTextArea"] textarea:focus {
            border-color: #F15A24 !important;
            box-shadow: 0 0 0 2px rgba(241, 90, 36, 0.15) !important;
        }

        /* Text Input & Selectbox */
        div[data-testid="stTextInput"] input {
            border-radius: 8px !important;
            background-color: #FFFFFF !important;
            border: 1px solid #CBD5E1 !important;
            font-size: 0.9rem !important;
            color: #17233C !important;
        }

        div[data-testid="stTextInput"] input:focus {
            border-color: #F15A24 !important;
            box-shadow: 0 0 0 2px rgba(241, 90, 36, 0.15) !important;
        }

        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            border-radius: 8px !important;
            background-color: #FFFFFF !important;
            border: 1px solid #CBD5E1 !important;
        }

        /* File Uploader */
        div[data-testid="stFileUploader"] section {
            background-color: #FFFFFF !important;
            border: 1.5px dashed #CBD5E1 !important;
            border-radius: 10px !important;
            padding: 0.85rem !important;
            min-height: auto !important;
        }

        div[data-testid="stFileUploader"] section:hover {
            border-color: #F15A24 !important;
        }

        div[data-testid="stFileUploader"] small {
            color: #94A3B8 !important;
            font-size: 11px !important;
        }

        /* Sidebar Navigation Menu Buttons - 100% Modern Menu, No Form Controls */
        section[data-testid="stSidebar"] div.stButton {
            margin-bottom: 6px !important;
        }

        section[data-testid="stSidebar"] div.stButton > button {
            height: 44px !important;
            min-height: 44px !important;
            border-radius: 8px !important;
            padding: 0 1rem !important;
            font-size: 0.92rem !important;
            font-weight: 500 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: flex-start !important;
            gap: 12px !important;
            width: 100% !important;
            text-align: left !important;
            transition: all 0.15s ease-in-out !important;
            box-shadow: none !important;
            border: none !important;
            border-left: 3px solid transparent !important;
        }

        /* Inactive Sidebar Nav Button */
        section[data-testid="stSidebar"] div.stButton > button[kind="secondary"],
        section[data-testid="stSidebar"] div.stButton > button:not([kind="primary"]) {
            background: transparent !important;
            color: #334155 !important;
            border: none !important;
            border-left: 3px solid transparent !important;
        }

        section[data-testid="stSidebar"] div.stButton > button[kind="secondary"] p,
        section[data-testid="stSidebar"] div.stButton > button:not([kind="primary"]) p {
            color: #334155 !important;
            font-weight: 500 !important;
        }

        section[data-testid="stSidebar"] div.stButton > button[kind="secondary"] span[data-testid="stIconMaterial"],
        section[data-testid="stSidebar"] div.stButton > button:not([kind="primary"]) span[data-testid="stIconMaterial"] {
            color: #64748B !important;
            font-size: 1.25rem !important;
            line-height: 1 !important;
        }

        /* Inactive Hover */
        section[data-testid="stSidebar"] div.stButton > button[kind="secondary"]:hover,
        section[data-testid="stSidebar"] div.stButton > button:not([kind="primary"]):hover {
            background: #FFF7F2 !important;
            color: #F15A24 !important;
            border-left: 3px solid transparent !important;
        }

        section[data-testid="stSidebar"] div.stButton > button[kind="secondary"]:hover p,
        section[data-testid="stSidebar"] div.stButton > button:not([kind="primary"]):hover p {
            color: #F15A24 !important;
        }

        section[data-testid="stSidebar"] div.stButton > button[kind="secondary"]:hover span[data-testid="stIconMaterial"],
        section[data-testid="stSidebar"] div.stButton > button:not([kind="primary"]):hover span[data-testid="stIconMaterial"] {
            color: #F15A24 !important;
        }

        /* Active Sidebar Nav Button */
        section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
            background: #FFF0E8 !important;
            color: #F15A24 !important;
            font-weight: 600 !important;
            border: none !important;
            border-left: 3px solid #F15A24 !important;
            border-radius: 8px !important;
            box-shadow: none !important;
        }

        section[data-testid="stSidebar"] div.stButton > button[kind="primary"] p {
            color: #F15A24 !important;
            font-weight: 600 !important;
        }

        section[data-testid="stSidebar"] div.stButton > button[kind="primary"] span[data-testid="stIconMaterial"] {
            color: #F15A24 !important;
            font-size: 1.25rem !important;
            line-height: 1 !important;
        }

        /* Suggestion Chip Buttons */
        .stChipButton button {
            background-color: #FFF7F2 !important;
            color: #C2410C !important;
            border: 1px solid #FED7C2 !important;
            border-radius: 20px !important;
            font-size: 0.8rem !important;
            font-weight: 600 !important;
            height: 34px !important;
            padding: 0.25rem 0.85rem !important;
            box-shadow: none !important;
        }

        .stChipButton button:hover {
            background-color: #FFEBE0 !important;
            border-color: #F15A24 !important;
            color: #F15A24 !important;
        }

        /* Card Container */
        .sentinel-card-container {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 14px;
            padding: 1.25rem;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
            margin-bottom: 1.25rem;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def render_global_header(active_page_name: str = "Home"):
    """Render persistent global top header across all pages."""
    st.markdown(
        """
        <div class="global-header">
            <div>
                <div class="header-main-title">
                    <span>SENTINEL</span>
                    <span style="font-weight: 400; color: #CBD5E1; font-size: 1.1rem;">|</span>
                    <span style="font-size: 1.05rem; font-weight: 600; color: #F15A24;">AI Complaint Intelligence</span>
                </div>
                <div class="header-sub-title">Manipal Academy of Higher Education Dubai Campus</div>
            </div>
            <div class="header-user-avatar" title="Campus User Account">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#F15A24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_sidebar():
    """Render branded sidebar with logo, modern menu navigation, and footer."""
    inject_custom_css()
    
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "manipal_logo.png")
    
    with st.sidebar:
        # 1. Manipal logo at top
        if os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)
            st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)
        else:
            st.markdown("<h2 style='color:#F15A24; margin-bottom:1.5rem;'>MANIPAL DUBAI</h2>", unsafe_allow_html=True)
            
        # 2. Four navigation items directly (No "NAVIGATION" title, No emojis, No radio buttons)
        current_page = st.session_state.get("nav_page", "Home")
        
        nav_items = [
            ("Home", ":material/home:"),
            ("Submit Complaint", ":material/edit_note:"),
            ("Dashboard", ":material/grid_view:"),
            ("History", ":material/history:")
        ]
        
        for page_name, icon_name in nav_items:
            is_active = (current_page == page_name)
            btn_type = "primary" if is_active else "secondary"
            btn_key = f"sidebar_nav_{page_name.lower().replace(' ', '_')}"
            
            if st.button(page_name, icon=icon_name, type=btn_type, key=btn_key, use_container_width=True):
                if not is_active:
                    st.session_state["nav_page"] = page_name
                    st.rerun()

        st.markdown("<div style='margin-top: 5rem;'></div>", unsafe_allow_html=True)
        
        # 3. Bottom Sidebar Branding (No emojis)
        st.markdown(
            """
            <div style="border-top: 1px solid #E2E8F0; padding-top: 0.85rem; text-align: left;">
                <div style="font-weight: 800; color: #17233C; font-size: 0.85rem;">SENTINEL</div>
                <div style="font-size: 0.75rem; color: #64748B;">AI Complaint Intelligence System</div>
                <div style="font-size: 0.75rem; color: #F15A24; margin-top: 0.35rem; font-weight: 600;">
                    For a better campus, together.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    return st.session_state.get("nav_page", "Home")


