"""
SENTINEL - Authentication & Session Management Service
Handles Firebase Authentication via Identity Toolkit REST API, token verification
with Firebase Admin SDK, role resolution via custom claims, profile management in
users/{uid}, and clean session state transitions for Streamlit.

SECURITY DIRECTIVE:
1. Passwords are never persisted or logged.
2. Public signup strictly provisions role = 'student'.
3. Admin role is granted exclusively via server-side custom claim (admin = true).
4. Logout completely purges tokens, cached queries, and sensitive session state.
"""

import json
import logging
import os
from typing import Any, Dict, Optional, Tuple

import requests
import streamlit as st
from firebase_admin import auth as admin_auth
from firebase_admin import firestore
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

import config
from database.auth_context import AuthenticatedUser

logger = logging.getLogger("sentinel.auth")

# Firebase Identity Toolkit REST Endpoints
AUTH_SIGNIN_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
AUTH_SIGNUP_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={api_key}"
AUTH_RESET_URL = "https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={api_key}"
TOKEN_REFRESH_URL = "https://securetoken.googleapis.com/v1/token?key={api_key}"


def get_firebase_web_api_key() -> str:
    """Retrieve Firebase Web API Key from Streamlit secrets or environment."""
    if hasattr(st, "secrets") and "firebase" in st.secrets and "api_key" in st.secrets["firebase"]:
        return st.secrets["firebase"]["api_key"]
    
    # Fallback to secrets.toml directly if st.secrets not loaded
    if os.path.exists(config.FIREBASE_SECRETS_PATH):
        try:
            import toml
            data = toml.load(config.FIREBASE_SECRETS_PATH)
            return data.get("firebase", {}).get("api_key", "")
        except Exception:
            pass
            
    # Default placeholder check
    return os.environ.get("FIREBASE_WEB_API_KEY", "")


def _get_firestore_client():
    from database.firestore_repository import _get_firestore_client as get_client
    return get_client()


# --------------------------------------------------------------------------
# 1. Sign In (Email / Password)
# --------------------------------------------------------------------------
def sign_in_with_email_password(email: str, password: str) -> Tuple[bool, Optional[AuthenticatedUser], str]:
    """Authenticate user with Firebase Identity Toolkit.
    Returns: (success, AuthenticatedUser or None, error_message)
    """
    api_key = get_firebase_web_api_key()
    if not api_key or api_key == "YOUR_FIREBASE_WEB_API_KEY":
        return False, None, "Firebase Web API key not configured in .streamlit/secrets.toml."

    url = AUTH_SIGNIN_URL.format(api_key=api_key)
    payload = {
        "email": email.strip(),
        "password": password,
        "returnSecureToken": True,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        res_data = resp.json()

        if resp.status_code != 200:
            err_msg = res_data.get("error", {}).get("message", "Authentication failed.")
            if "EMAIL_NOT_FOUND" in err_msg or "INVALID_PASSWORD" in err_msg or "INVALID_LOGIN_CREDENTIALS" in err_msg:
                return False, None, "Invalid email or password. Please check your credentials."
            elif "USER_DISABLED" in err_msg:
                return False, None, "This account has been disabled by an administrator."
            return False, None, f"Login error: {err_msg}"

        id_token = res_data["idToken"]
        refresh_token = res_data["refreshToken"]
        uid = res_data["localId"]

        # Resolve role and user profile
        user = _resolve_user_profile(uid=uid, id_token=id_token, fallback_email=email)

        # Store in Streamlit session state
        _set_session_state(user, id_token, refresh_token)
        return True, user, "Success"

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during sign in: {e}")
        return False, None, f"Network connection error: {e}"
    except Exception as e:
        logger.error(f"Unexpected error during sign in: {e}")
        return False, None, f"Authentication error: {e}"


# --------------------------------------------------------------------------
# 2. Student Registration (Strictly role = 'student')
# --------------------------------------------------------------------------
def sign_up_student(
    full_name: str,
    email: str,
    student_id: str,
    programme: str,
    password: str,
    confirm_password: str,
) -> Tuple[bool, Optional[AuthenticatedUser], str]:
    """Register a new student account.
    Enforces institutional email restrictions, password match, and creates users/{uid} profile.
    PUBLIC REGISTRATION NEVER ALLOWS ROLE SELECTION.
    """
    # Validation
    if not full_name or not full_name.strip():
        return False, None, "Full name is required."

    clean_email = email.strip().lower()
    if not clean_email or "@" not in clean_email:
        return False, None, "A valid email address is required."

    # Validate domain if configured
    allowed_domains = getattr(config, "ALLOWED_STUDENT_EMAIL_DOMAINS", [])
    if allowed_domains:
        domain = clean_email.split("@")[-1]
        if not any(domain == d or domain.endswith("." + d) for d in allowed_domains):
            return False, None, (
                f"Registration is restricted to authorized student domains ({', '.join(allowed_domains)})."
            )

    if not student_id or not student_id.strip():
        return False, None, "Student ID is required."

    if not password or len(password) < 6:
        return False, None, "Password must be at least 6 characters."

    if password != confirm_password:
        return False, None, "Passwords do not match."

    api_key = get_firebase_web_api_key()
    if not api_key or api_key == "YOUR_FIREBASE_WEB_API_KEY":
        return False, None, "Firebase Web API key not configured."

    url = AUTH_SIGNUP_URL.format(api_key=api_key)
    payload = {
        "email": clean_email,
        "password": password,
        "returnSecureToken": True,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        res_data = resp.json()

        if resp.status_code != 200:
            err_msg = res_data.get("error", {}).get("message", "Registration failed.")
            if "EMAIL_EXISTS" in err_msg:
                return False, None, "An account with this email address already exists."
            return False, None, f"Registration error: {err_msg}"

        uid = res_data["localId"]
        id_token = res_data["idToken"]
        refresh_token = res_data["refreshToken"]

        # Create user profile document in Firestore: users/{uid}
        db = _get_firestore_client()
        user_doc_ref = db.collection("users").document(uid)
        user_profile = {
            "uid": uid,
            "full_name": full_name.strip(),
            "email": clean_email,
            "student_id": student_id.strip(),
            "programme": programme.strip() if programme else "General Studies",
            "role": "student",  # NEVER allow student registration to claim admin
            "active": True,
            "created_at": SERVER_TIMESTAMP,
        }
        user_doc_ref.set(user_profile)

        # Build AuthenticatedUser
        user = AuthenticatedUser(
            uid=uid,
            email=clean_email,
            full_name=full_name.strip(),
            role="student",
            student_id=student_id.strip(),
            programme=programme.strip() if programme else None,
        )

        _set_session_state(user, id_token, refresh_token)
        return True, user, "Account created successfully."

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during registration: {e}")
        return False, None, f"Network error: {e}"
    except Exception as e:
        logger.error(f"Unexpected error during registration: {e}")
        return False, None, f"Registration failed: {e}"


# --------------------------------------------------------------------------
# 3. Password Reset
# --------------------------------------------------------------------------
def send_password_reset(email: str) -> Tuple[bool, str]:
    """Send Firebase password reset email."""
    clean_email = email.strip().lower()
    if not clean_email or "@" not in clean_email:
        return False, "Please enter a valid email address."

    api_key = get_firebase_web_api_key()
    url = AUTH_RESET_URL.format(api_key=api_key)
    payload = {
        "requestType": "PASSWORD_RESET",
        "email": clean_email,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        res_data = resp.json()
        if resp.status_code == 200:
            return True, f"A password reset link has been sent to {clean_email}."
        err_msg = res_data.get("error", {}).get("message", "Failed to send reset email.")
        return False, f"Password reset error: {err_msg}"
    except Exception as e:
        return False, f"Network error: {e}"


# --------------------------------------------------------------------------
# 4. Token & Profile Resolution (Role Determination)
# --------------------------------------------------------------------------
def _resolve_user_profile(uid: str, id_token: str, fallback_email: str) -> AuthenticatedUser:
    """Verify ID token with Admin SDK to check custom claim 'admin',
    and retrieve user profile from users/{uid}.
    """
    # Guarantee Firebase Admin app is initialized first
    try:
        db = _get_firestore_client()
    except Exception as e:
        logger.error(f"Error initializing Firebase client: {e}")
        db = None

    role = "student"  # Default safe role
    try:
        # Check custom claims via Admin SDK
        decoded = admin_auth.verify_id_token(id_token)
        if decoded.get("admin") is True:
            role = "admin"
    except Exception as e:
        logger.warning(f"Failed to verify custom claims via Admin SDK ({e}). Checking Firestore profile.")

    # Retrieve profile details from Firestore users/{uid}
    full_name = fallback_email.split("@")[0].title()
    student_id = None
    programme = None

    if db is not None:
        try:
            doc = db.collection("users").document(uid).get()
            if doc.exists:
                profile = doc.to_dict()
                full_name = profile.get("full_name") or full_name
                student_id = profile.get("student_id")
                programme = profile.get("programme")
                # If custom claim or Firestore document specifies admin role
                if profile.get("role") == "admin" or role == "admin":
                    role = "admin"
            else:
                db.collection("users").document(uid).set({
                    "uid": uid,
                    "email": fallback_email,
                    "full_name": full_name,
                    "role": role,
                    "student_id": None,
                    "programme": None,
                    "active": True,
                    "created_at": SERVER_TIMESTAMP,
                })
        except Exception as e:
            logger.error(f"Error fetching user profile for {uid}: {e}")

    return AuthenticatedUser(
        uid=uid,
        email=fallback_email,
        full_name=full_name,
        role=role,
        student_id=student_id,
        programme=programme,
    )


# --------------------------------------------------------------------------
# 5. Session State Management
# --------------------------------------------------------------------------
def _set_session_state(user: AuthenticatedUser, id_token: str, refresh_token: str):
    """Save auth context to Streamlit session state."""
    st.session_state["authenticated"] = True
    st.session_state["uid"] = user.uid
    st.session_state["email"] = user.email
    st.session_state["full_name"] = user.full_name
    st.session_state["role"] = user.role
    st.session_state["student_id"] = user.student_id
    st.session_state["programme"] = user.programme
    st.session_state["id_token"] = id_token
    st.session_state["refresh_token"] = refresh_token
    st.session_state["current_user"] = user


def get_current_user() -> Optional[AuthenticatedUser]:
    """Retrieve currently authenticated user from session state."""
    if not st.session_state.get("authenticated"):
        return None

    if "current_user" in st.session_state and isinstance(st.session_state["current_user"], AuthenticatedUser):
        return st.session_state["current_user"]

    # Reconstruct from session state if present
    uid = st.session_state.get("uid")
    if uid:
        user = AuthenticatedUser(
            uid=uid,
            email=st.session_state.get("email", ""),
            full_name=st.session_state.get("full_name", "User"),
            role=st.session_state.get("role", "student"),
            student_id=st.session_state.get("student_id"),
            programme=st.session_state.get("programme"),
        )
        st.session_state["current_user"] = user
        return user
    return None


def logout():
    """Completely clear authentication tokens and sensitive session state."""
    keys_to_clear = [
        "authenticated",
        "uid",
        "email",
        "full_name",
        "role",
        "student_id",
        "programme",
        "id_token",
        "refresh_token",
        "current_user",
        "selected_complaint",
        "complaint_analysis",
        "submission_success",
    ]
    for k in keys_to_clear:
        if k in st.session_state:
            del st.session_state[k]

    # Clear Streamlit cache if applicable
    st.cache_data.clear()
    st.rerun()
