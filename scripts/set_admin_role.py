"""
SENTINEL - Administrator Role Provisioning Utility
Grants administrator privileges to a Firebase user by setting the custom user claim:
    {"admin": True}
and updating their Firestore profile in users/{uid}.

USAGE:
    python scripts/set_admin_role.py --email admin@manipal.edu
    python scripts/set_admin_role.py --uid <FIREBASE_USER_UID>

SECURITY DIRECTIVE:
This tool must only be executed by authorized system administrators via server CLI.
It is never exposed in the client or student UI.
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import firebase_admin
from firebase_admin import auth as admin_auth
from firebase_admin import credentials, firestore

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sentinel.set_admin")


def init_firebase_admin():
    try:
        return firebase_admin.get_app()
    except ValueError:
        cert_path = config.FIREBASE_SERVICE_ACCOUNT_PATH
        if not os.path.exists(cert_path):
            logger.error(f"Service account credential file not found at: {cert_path}")
            sys.exit(1)
        cred = credentials.Certificate(cert_path)
        return firebase_admin.initialize_app(cred)


def set_admin_role(email: str = None, uid: str = None):
    app = init_firebase_admin()
    db = firestore.client(app=app)

    # 1. Lookup user
    user_record = None
    try:
        if email:
            logger.info(f"Looking up Firebase account by email: {email}")
            user_record = admin_auth.get_user_by_email(email.strip().lower())
        elif uid:
            logger.info(f"Looking up Firebase account by UID: {uid}")
            user_record = admin_auth.get_user(uid.strip())
        else:
            logger.error("Either --email or --uid must be provided.")
            sys.exit(1)
    except admin_auth.UserNotFoundError:
        logger.error(f"User not found in Firebase Authentication! Identifier: {email or uid}")
        logger.info("Please ensure the user has signed up / registered an account first.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to lookup user: {e}")
        sys.exit(1)

    target_uid = user_record.uid
    target_email = user_record.email
    logger.info(f"Target user identified: UID={target_uid}, Email={target_email}")

    # 2. Set Custom User Claim: admin = True
    try:
        current_claims = user_record.custom_claims or {}
        new_claims = dict(current_claims)
        new_claims["admin"] = True

        admin_auth.set_custom_user_claims(target_uid, new_claims)
        logger.info(f"Custom user claim successfully applied: {new_claims}")
    except Exception as e:
        logger.error(f"Failed to set custom user claims: {e}")
        sys.exit(1)

    # 3. Update Firestore users/{uid} document
    try:
        user_doc_ref = db.collection("users").document(target_uid)
        user_doc_ref.set({
            "uid": target_uid,
            "email": target_email,
            "role": "admin",
            "active": True,
        }, merge=True)
        logger.info(f"Firestore document users/{target_uid} updated with role='admin'.")
    except Exception as e:
        logger.warning(f"Could not update Firestore user document ({e}), but custom claim was set.")

    # 4. Critical Reminder
    print("\n" + "=" * 70)
    print("SUCCESS: Administrator privileges successfully granted!")
    print(f"User UID:   {target_uid}")
    print(f"User Email: {target_email}")
    print("Custom Claims: {'admin': True}")
    print("=" * 70)
    print("IMPORTANT REMINDER:")
    print("Firebase custom claims are embedded in the user's JWT ID token.")
    print("If the user is currently logged in, they MUST sign out and sign in again,")
    print("or wait for their token to refresh before the 'admin' claim takes effect.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Grant Admin role to a Firebase user")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--email", type=str, help="Email address of the target account")
    group.add_argument("--uid", type=str, help="Firebase UID of the target account")

    args = parser.parse_args()
    set_admin_role(email=args.email, uid=args.uid)
