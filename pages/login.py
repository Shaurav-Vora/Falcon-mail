"""
SENTINEL - Authentication Page
Renders the Manipal Academy of Higher Education / SENTINEL login, registration,
and password reset interfaces for unauthenticated sessions.

SECURITY DIRECTIVE:
1. Public registration provisions ONLY role = 'student'.
2. Passwords are never logged or echoed back.
3. No sidebar or privileged application views render before authentication.
"""

import streamlit as st
import config
from utils.auth import sign_in_with_email_password, sign_up_student, send_password_reset


def render_login_page():
    """Render the authentication portal."""
    # Hide sidebar for unauthenticated visitors
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        display: none !important;
    }
    .auth-container {
        max-width: 480px;
        margin: 2rem auto;
        padding: 2.5rem;
        background: #ffffff;
        border-radius: 12px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
        border: 1px solid #e2e8f0;
    }
    .auth-brand {
        text-align: center;
        margin-bottom: 2rem;
    }
    .auth-title {
        font-size: 1.75rem;
        font-weight: 700;
        color: #0f172a;
        letter-spacing: -0.025em;
        margin: 0;
    }
    .auth-subtitle {
        font-size: 0.875rem;
        color: #64748b;
        margin-top: 0.35rem;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("""
        <div class="auth-brand">
            <div style="font-size: 2.5rem; margin-bottom: 0.5rem; color: #1e3a8a;">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#1e3a8a" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                </svg>
            </div>
            <h1 class="auth-title">SENTINEL</h1>
            <p class="auth-subtitle">Campus Incident & Complaint Intelligence Platform</p>
        </div>
        """, unsafe_allow_html=True)

        tab_signin, tab_signup, tab_reset = st.tabs(["Sign In", "Student Registration", "Forgot Password"])

        # ----------------------------------------------------------------------
        # Tab 1: Sign In
        # ----------------------------------------------------------------------
        with tab_signin:
            with st.form("signin_form", clear_on_submit=False):
                st.markdown("##### Account Login")
                email = st.text_input("University / Manipal Email", placeholder="student@manipal.edu")
                password = st.text_input("Password", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

                if submitted:
                    if not email or not password:
                        st.error("Please provide both email and password.")
                    else:
                        with st.spinner("Authenticating credentials..."):
                            success, user, message = sign_in_with_email_password(email, password)
                            if success:
                                st.success(f"Welcome back, {user.full_name}!")
                                st.rerun()
                            else:
                                st.error(message)

        # ----------------------------------------------------------------------
        # Tab 2: Student Registration
        # ----------------------------------------------------------------------
        with tab_signup:
            with st.form("signup_form", clear_on_submit=False):
                st.markdown("##### New Student Registration")
                st.caption("Public registration is restricted to Students. Staff roles are provisioned by IT Administration.")

                full_name = st.text_input("Full Name", placeholder="e.g. Rahul Sharma")
                student_email = st.text_input("Student Email Address", placeholder="name@manipal.edu")
                student_id = st.text_input("Student Registration / ID Number", placeholder="e.g. 210953042")
                programme = st.selectbox("Academic Programme", [
                    "B.Tech Computer Science & Engineering",
                    "B.Tech Information Technology",
                    "B.Tech Electronics & Communication",
                    "B.Tech Mechanical Engineering",
                    "BBA / Business Administration",
                    "B.Sc Psychology",
                    "M.Tech / Postgraduate",
                    "Other Programme",
                ])
                new_password = st.text_input("Create Password (min. 6 characters)", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")

                reg_submitted = st.form_submit_button("Create Student Account", use_container_width=True, type="primary")

                if reg_submitted:
                    with st.spinner("Registering student account..."):
                        success, user, message = sign_up_student(
                            full_name=full_name,
                            email=student_email,
                            student_id=student_id,
                            programme=programme,
                            password=new_password,
                            confirm_password=confirm_password,
                        )
                        if success:
                            st.success("Account created successfully! Redirecting...")
                            st.rerun()
                        else:
                            st.error(message)

        # ----------------------------------------------------------------------
        # Tab 3: Forgot Password
        # ----------------------------------------------------------------------
        with tab_reset:
            with st.form("reset_form"):
                st.markdown("##### Reset Password")
                st.caption("Enter your registered email address to receive a password reset link.")
                reset_email = st.text_input("Registered Email Address")
                reset_submitted = st.form_submit_button("Send Reset Link", use_container_width=True)

                if reset_submitted:
                    if not reset_email:
                        st.error("Please enter your email address.")
                    else:
                        with st.spinner("Sending reset instructions..."):
                            ok, reset_msg = send_password_reset(reset_email)
                            if ok:
                                st.success(reset_msg)
                            else:
                                st.error(reset_msg)
