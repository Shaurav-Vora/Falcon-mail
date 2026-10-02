"""Shared access to Falcon Mail's Firestore repository."""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.base_repository import BaseComplaintRepository

logger = logging.getLogger("falcon_mail.database")

# Cache repository singleton
_REPO_INSTANCE = None


def get_repository() -> BaseComplaintRepository:
    """Return the shared Firestore repository instance."""
    global _REPO_INSTANCE
    if _REPO_INSTANCE is not None:
        return _REPO_INSTANCE

    try:
        from database.firestore_repository import FirestoreRepository

        _REPO_INSTANCE = FirestoreRepository()
        return _REPO_INSTANCE
    except Exception as exc:
        message = (
            f"Cloud Firestore connection failed ({exc}). "
            "Check serviceAccountKey.json and your internet connection."
        )
        logger.error(message)
        raise ConnectionError(message) from exc


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    repo = get_repository()
    print(f"Repository initialized successfully: {type(repo).__name__}")
