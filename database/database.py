"""
SENTINEL - Database Repository Factory & Centralized Access
Initializes and provides the active repository backend based on configuration.

CRITICAL ARCHITECTURAL DIRECTIVE:
Firestore is the final shared source of truth (SENTINEL_STORAGE_BACKEND = "firestore").
SQLite is reserved ONLY for isolated tests, local offline development, and historical migration.
Under NO circumstances does SENTINEL silently or automatically fall back from Firestore
to SQLite, as doing so would cause split-brain state and data inconsistency across users.
"""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from database.auth_context import AuthenticatedUser
from database.base_repository import BaseComplaintRepository

logger = logging.getLogger("sentinel.database")

# Cache repository singleton
_REPO_INSTANCE = None


def get_repository() -> BaseComplaintRepository:
    """Return the configured repository instance.
    Raises ConnectionError if Firestore cannot be reached.
    """
    global _REPO_INSTANCE
    if _REPO_INSTANCE is not None:
        return _REPO_INSTANCE

    backend = getattr(config, "SENTINEL_STORAGE_BACKEND", "firestore").lower()

    if backend == "firestore":
        try:
            from database.firestore_repository import FirestoreRepository
            _REPO_INSTANCE = FirestoreRepository()
            logger.info("Active storage backend: Cloud Firestore")
            return _REPO_INSTANCE
        except Exception as exc:
            error_msg = (
                f"FATAL: Cloud Firestore connection failed ({exc}).\n"
                "Automatic SQLite fallback is disabled to prevent database divergence.\n"
                "Verify that serviceAccountKey.json is present and valid."
            )
            logger.critical(error_msg)
            raise ConnectionError(error_msg) from exc

    elif backend == "sqlite":
        from database.sqlite_repository import SQLiteRepository
        logger.warning("Active storage backend: Local SQLite (Explicit Offline/Test Mode)")
        _REPO_INSTANCE = SQLiteRepository(config.DB_PATH)
        return _REPO_INSTANCE

    else:
        raise ValueError(f"Unknown SENTINEL_STORAGE_BACKEND: '{backend}'. Must be 'firestore' or 'sqlite'.")


def reset_repository_instance():
    """Reset repository singleton (useful for test teardown)."""
    global _REPO_INSTANCE
    _REPO_INSTANCE = None


# --------------------------------------------------------------------------
# Legacy SQLite adapter functions for backward-compatibility with tests/scripts
# --------------------------------------------------------------------------
def init_db(db_path: str = config.DB_PATH):
    """Initialize SQLite database for isolated local testing."""
    from database.sqlite_repository import SQLiteRepository
    repo = SQLiteRepository(db_path)
    return repo


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    repo = get_repository()
    print(f"Repository initialized successfully: {type(repo).__name__}")
