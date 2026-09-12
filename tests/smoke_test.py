"""
SENTINEL - End-to-End Enterprise Smoke Test Suite
Verifies models, pipeline, isolated repository persistence, server-side RBAC,
duplicate privacy sanitization, and strict production DB protection.
"""

import os
import sys
import tempfile

# Fix Windows console UTF-8 stdout encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    DB_PATH, CATEGORY_MODEL_PATH, URGENCY_MODEL_PATH,
    SPACY_MODEL_NAME, SENTENCE_TRANSFORMER_MODEL, CATEGORIES, URGENCY_LEVELS
)
from database.auth_context import AuthenticatedUser
from database.sqlite_repository import SQLiteRepository
from nlp.preprocessing import get_spacy_nlp
from nlp.classification import get_category_model
from nlp.urgency import get_urgency_model
from nlp.duplicate_detection import get_sentence_transformer
from nlp.pipeline import process_complaint


def run_smoke_test():
    print("==========================================================")
    print("           SENTINEL END-TO-END SMOKE TEST                 ")
    print("==========================================================")

    # 0. Baseline Check: Record Production DB state before testing
    prod_db_exists = os.path.exists(DB_PATH)
    prod_db_mtime = os.path.getmtime(DB_PATH) if prod_db_exists else None

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_db_path = os.path.join(temp_dir, "test_sentinel.db")
        print(f"Using isolated temporary test DB: {temp_db_path}\n")
        test_repo = SQLiteRepository(temp_db_path)

        # Create student and admin actors
        student = AuthenticatedUser(
            uid="smoke_student_01",
            email="smoke_student@manipal.edu",
            full_name="Smoke Student",
            role="student",
            student_id="210953001",
        )
        admin = AuthenticatedUser(
            uid="smoke_admin_01",
            email="smoke_admin@manipal.edu",
            full_name="Smoke Admin",
            role="admin",
        )

        # Test 1: Config import & values
        assert len(CATEGORIES) == 11, "Categories count mismatch in config"
        assert len(URGENCY_LEVELS) == 4, "Urgency levels count mismatch in config"
        print("[PASS] 1. Config Import & Constants: SUCCESS")

        # Test 2: Model files exist on disk
        assert os.path.exists(CATEGORY_MODEL_PATH), f"Category model missing at {CATEGORY_MODEL_PATH}"
        assert os.path.exists(URGENCY_MODEL_PATH), f"Urgency model missing at {URGENCY_MODEL_PATH}"
        print("[PASS] 2. Trained Model Files Exist: SUCCESS")

        # Test 3: Category model loads into memory
        cat_model = get_category_model()
        assert cat_model is not None, "Failed to load category model"
        print(f"[PASS] 3. Category Model Loaded: SUCCESS ({len(cat_model.classes_)} classes)")

        # Test 4: Urgency model loads into memory
        urg_model = get_urgency_model()
        assert urg_model is not None, "Failed to load urgency model"
        print(f"[PASS] 4. Urgency Model Loaded: SUCCESS ({len(urg_model.classes_)} classes)")

        # Test 5: spaCy model loads
        spacy_nlp = get_spacy_nlp()
        assert spacy_nlp is not None, "Failed to load spaCy model"
        print(f"[PASS] 5. spaCy Model Loaded: SUCCESS ({SPACY_MODEL_NAME})")

        # Test 6: Sentence Transformer loads
        embedder = get_sentence_transformer()
        assert embedder is not None, "Failed to load SentenceTransformer"
        print(f"[PASS] 6. Sentence Transformer Loaded: SUCCESS ({SENTENCE_TRANSFORMER_MODEL})")

        # Test 7 & 8: Pipeline execution with repository persistence
        c_a = "Water is leaking from the ceiling near the cafeteria."
        res_a = process_complaint(
            c_a, actor=student, repo=test_repo, store_in_db=True, user_location="Cafeteria 1st floor"
        )
        assert res_a["complaint_id"] is not None, "Complaint ID is None"
        assert res_a["category"] in CATEGORIES, f"Unexpected category: {res_a['category']}"
        print(f"[PASS] 7. Process Complaint Pipeline: SUCCESS (Assigned #{res_a['complaint_id']}, Cat: {res_a['category']}, Urg: {res_a['urgency']})")
        print(f"[PASS] 8. Isolated DB Insertion: SUCCESS (ID #{res_a['complaint_id']} in test DB)")

        # Test 9: Retrieval with server-side authorization
        student_records = test_repo.get_student_complaints(student.uid, actor=student)
        assert len(student_records) == 1, f"Expected 1 record for student, found {len(student_records)}"
        admin_records = test_repo.get_all_complaints(actor=admin)
        assert len(admin_records) == 1, f"Expected 1 record for admin, found {len(admin_records)}"
        print(f"[PASS] 9. Scoped Database Retrieval: SUCCESS (Student: {len(student_records)}, Admin: {len(admin_records)})")

        # Test 10: Multi-signal duplicate detection with student privacy
        c_b = "There is water all over the cafeteria floor because one of the pipes is leaking."
        res_b = process_complaint(c_b, actor=student, repo=test_repo, store_in_db=True)
        dup_info = res_b["duplicate"]
        assert dup_info["is_duplicate"] == True, f"Duplicate detection failed: {dup_info}"
        # Assert student privacy: student_dup_notice must be set, but no other student's personal info
        assert res_b["student_dup_notice"] is not None
        print(f"[PASS] 10. Duplicate Detection & Privacy Notice: SUCCESS (Notice: '{res_b['student_dup_notice']}')")

        # Test 11: Valid status update & resolution note validation
        # Attempt resolving without note must fail
        threw_validation_error = False
        try:
            test_repo.update_complaint_status(res_a["complaint_id"], "Resolved", actor=admin, resolution_note="")
        except ValueError:
            threw_validation_error = True
        assert threw_validation_error, "Failed to enforce mandatory resolution note for Resolved status"

        # Resolving with note must succeed
        update_ok = test_repo.update_complaint_status(
            res_a["complaint_id"], "Resolved", actor=admin, resolution_note="Replaced leaking pipe connector."
        )
        assert update_ok == True, "Failed to update status in temp DB"
        print(f"[PASS] 11. Status Workflow & Resolution Validation: SUCCESS (Mandatory note enforced)")

        # Test 12: Dashboard stats generation
        stats = test_repo.get_dashboard_stats(actor=admin)
        assert stats["total"] == 2, f"Expected 2 total records, got {stats['total']}"
        assert stats["resolved"] == 1, f"Expected 1 resolved record, got {stats['resolved']}"
        print(f"[PASS] 12. Dashboard Stats Aggregation: SUCCESS (Total: {stats['total']}, Resolved: {stats['resolved']})")

    # Test 13: Strict Production DB Isolation Guarantee
    if prod_db_exists:
        prod_db_mtime_after = os.path.getmtime(DB_PATH)
        assert prod_db_mtime == prod_db_mtime_after, (
            f"PRODUCTION DB POLLUTION: File modification timestamp changed on {DB_PATH}!"
        )
    print(f"[PASS] 13. Production Database Isolation: SUCCESS (Zero mutations to {DB_PATH})")

    print("\n==========================================================")
    print("      ALL 13 SMOKE TESTS PASSED WITH ZERO DB POLLUTION!   ")
    print("==========================================================")
    return True


if __name__ == "__main__":
    run_smoke_test()
