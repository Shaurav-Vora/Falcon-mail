import os
import sys
import tempfile
import pandas as pd

# Fix Windows console UTF-8 stdout encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    DB_PATH, CATEGORY_MODEL_PATH, URGENCY_MODEL_PATH,
    SPACY_MODEL_NAME, SENTENCE_TRANSFORMER_MODEL, CATEGORIES, URGENCY_LEVELS
)
from database.database import init_db, insert_complaint, get_all_complaints, update_complaint_status
from nlp.preprocessing import get_spacy_nlp
from nlp.classification import get_category_model
from nlp.urgency import get_urgency_model
from nlp.duplicate_detection import get_sentence_transformer
from nlp.pipeline import process_complaint

def run_smoke_test():
    """
    Automated Smoke Test covering end-to-end backend functionality with strict DB isolation.
    Tests all 13 requirements:
    1. config import
    2. model files exist
    3. category model loads
    4. urgency model loads
    5. spaCy loads
    6. sentence transformer loads
    7. process_complaint works
    8. temporary DB insertion works
    9. retrieval works
    10. duplicate detection works
    11. status update works
    12. dashboard stats can be generated
    13. no test modifies production DB
    """
    print("==========================================================")
    print("           SENTINEL END-TO-END SMOKE TEST                 ")
    print("==========================================================")
    
    # 13. Baseline Check: Record Production DB state before testing
    prod_db_exists = os.path.exists(DB_PATH)
    prod_db_mtime = os.path.getmtime(DB_PATH) if prod_db_exists else None
    prod_db_records_before = len(get_all_complaints(db_path=DB_PATH)) if prod_db_exists else 0
    print(f"Production DB Baseline: Exists={prod_db_exists}, Records={prod_db_records_before}")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_db_path = os.path.join(temp_dir, "test_sentinel.db")
        print(f"Using isolated temporary test DB: {temp_db_path}\n")
        
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
        
        # Test 5: spaCy model loads without download
        spacy_nlp = get_spacy_nlp()
        assert spacy_nlp is not None, "Failed to load spaCy model"
        print(f"[PASS] 5. spaCy Model Loaded: SUCCESS ({SPACY_MODEL_NAME})")
        
        # Test 6: Sentence Transformer loads
        embedder = get_sentence_transformer()
        assert embedder is not None, "Failed to load SentenceTransformer"
        print(f"[PASS] 6. Sentence Transformer Loaded: SUCCESS ({SENTENCE_TRANSFORMER_MODEL})")
        
        # Test 7 & 8: Temporary DB initialization & process_complaint execution
        init_db(db_path=temp_db_path)
        c_a = "Water is leaking from the ceiling near the cafeteria."
        res_a = process_complaint(c_a, store_in_db=True, db_path=temp_db_path, user_location="Cafeteria 1st floor")
        assert res_a["complaint_id"] is not None, "Complaint ID is None"
        assert res_a["category"] in CATEGORIES, f"Unexpected category: {res_a['category']}"
        print(f"[PASS] 7. Process Complaint Pipeline: SUCCESS (Assigned #{res_a['complaint_id']}, Cat: {res_a['category']}, Urg: {res_a['urgency']})")
        print(f"[PASS] 8. Temporary DB Insertion: SUCCESS (ID #{res_a['complaint_id']} in test DB)")
        
        # Test 9: Retrieval from temporary DB
        records = get_all_complaints(db_path=temp_db_path)
        assert len(records) == 1, f"Expected 1 record in temp DB, found {len(records)}"
        print(f"[PASS] 9. Database Retrieval: SUCCESS (Retrieved {len(records)} record)")
        
        # Test 10: Multi-signal duplicate detection
        c_b = "There is water all over the cafeteria floor because one of the pipes is leaking."
        res_b = process_complaint(c_b, store_in_db=True, db_path=temp_db_path)
        dup_info = res_b["duplicate"]
        assert dup_info["is_duplicate"] == True, f"Duplicate detection failed: {dup_info}"
        print(f"[PASS] 10. Duplicate Detection: SUCCESS (Type: {dup_info['duplicate_type']}, Sim: {dup_info['similarity']*100:.1f}%)")
        
        # Test 11: Valid status update & status validation
        update_ok = update_complaint_status(res_a["complaint_id"], "Resolved", db_path=temp_db_path)
        assert update_ok == True, "Failed to update status in temp DB"
        
        # Test status validation rejects invalid status
        invalid_rejected = False
        try:
            update_complaint_status(res_a["complaint_id"], "INVALID_STATUS_XYZ", db_path=temp_db_path)
        except ValueError:
            invalid_rejected = True
        assert invalid_rejected, "Status validation failed to reject invalid status string"
        print(f"[PASS] 11. Status Management & Validation: SUCCESS (Status updated & invalid transitions blocked)")
        
        # Test 12: Dashboard stats generation from query
        all_recs = get_all_complaints(db_path=temp_db_path)
        df_stats = pd.DataFrame(all_recs)
        total_kpi = len(df_stats)
        open_kpi = len(df_stats[df_stats['status'] == 'Open'])
        resolved_kpi = len(df_stats[df_stats['status'] == 'Resolved'])
        assert total_kpi == 2, f"Expected 2 total records, got {total_kpi}"
        assert resolved_kpi == 1, f"Expected 1 resolved record, got {resolved_kpi}"
        print(f"[PASS] 12. Dashboard Stats Aggregation: SUCCESS (Total: {total_kpi}, Open: {open_kpi}, Resolved: {resolved_kpi})")
        
    # Test 13: Strict Production DB Isolation Guarantee
    if prod_db_exists:
        prod_db_mtime_after = os.path.getmtime(DB_PATH)
        prod_db_records_after = len(get_all_complaints(db_path=DB_PATH))
        assert prod_db_records_before == prod_db_records_after, (
            f"PRODUCTION DB POLLUTION: Record count changed from {prod_db_records_before} to {prod_db_records_after}!"
        )
        assert prod_db_mtime == prod_db_mtime_after, (
            f"PRODUCTION DB POLLUTION: File modification timestamp changed!"
        )
    print(f"[PASS] 13. Production Database Isolation: SUCCESS (Zero mutations to {DB_PATH})")
    
    print("\n==========================================================")
    print("      ALL 13 SMOKE TESTS PASSED WITH ZERO DB POLLUTION!   ")
    print("==========================================================")
    return True

if __name__ == "__main__":
    run_smoke_test()
