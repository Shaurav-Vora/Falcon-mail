"""
SENTINEL - SQLite to Firestore Migration Utility
Migrates legacy local SQLite records from database/sentinel.db to Cloud Firestore.

SAFETY DIRECTIVE:
This script must NOT be executed automatically.
Existing SQLite records remain unchanged.
Execute only upon explicit confirmation from the user/lead administrator.

Usage:
    python scripts/migrate_sqlite_to_firestore.py --dry-run
    python scripts/migrate_sqlite_to_firestore.py --execute
"""

import argparse
import logging
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from database.auth_context import AuthenticatedUser
from database.firestore_repository import FirestoreRepository

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sentinel.migration")


def inspect_sqlite_records(db_path: str = config.DB_PATH) -> list:
    """Read all legacy records from sentinel.db."""
    if not os.path.exists(db_path):
        logger.warning(f"No SQLite database found at {db_path}")
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM complaints ORDER BY id ASC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Error querying SQLite database: {e}")
        return []
    finally:
        conn.close()


def run_migration(dry_run: bool = True):
    records = inspect_sqlite_records()
    logger.info(f"Found {len(records)} existing complaints in SQLite database.")

    if not records:
        logger.info("Nothing to migrate.")
        return

    if dry_run:
        logger.info("[DRY RUN MODE] No changes will be written to Cloud Firestore.")
        for r in records[:5]:
            logger.info(f"  Sample ID: {r.get('id')} | Text: {r.get('complaint_text')[:60]}... | Status: {r.get('status')}")
        logger.info("To perform actual migration, run with: python scripts/migrate_sqlite_to_firestore.py --execute")
        return

    # Execute actual migration
    logger.info("Initializing Cloud Firestore connection for migration...")
    repo = FirestoreRepository()

    # System migration actor with admin privileges
    migration_actor = AuthenticatedUser(
        uid="system-migration-admin",
        email="migration@sentinel.manipal.edu",
        full_name="System Migration Utility",
        role="admin",
        student_id=None,
    )

    migrated_count = 0
    for r in records:
        complaint_id = f"CMP-LEGACY-{r['id']}"
        complaint_data = {
            "complaint_id": complaint_id,
            "title": r.get("issue") or r.get("complaint_text", "")[:50],
            "description": r.get("complaint_text", ""),
            "category": r.get("category", "Other"),
            "category_confidence": float(r.get("category_confidence") or 1.0),
            "urgency": r.get("urgency", "Medium"),
            "urgency_confidence": float(r.get("urgency_confidence") or 1.0),
            "department": r.get("recommended_department", "General Services"),
            "location": r.get("user_location") or r.get("location") or "Campus",
            "status": r.get("status", "Open"),
        }
        try:
            repo.create_complaint(complaint_data, migration_actor)
            migrated_count += 1
        except Exception as e:
            logger.error(f"Failed to migrate record {r['id']}: {e}")

    logger.info(f"Migration completed. Successfully migrated {migrated_count}/{len(records)} records to Firestore.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate SQLite complaints to Firestore")
    parser.add_argument("--execute", action="store_true", help="Execute actual migration to Cloud Firestore")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Inspect records without writing")
    args = parser.parse_args()

    if args.execute:
        run_migration(dry_run=False)
    else:
        run_migration(dry_run=True)
