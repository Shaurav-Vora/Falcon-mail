import os
import sys
import pandas as pd

# Fix Windows console UTF-8 stdout encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import init_db, insert_complaint, get_all_complaints, update_complaint_status
from nlp.pipeline import process_complaint

def run_smoke_test():
    """Automated Smoke Test covering end-to-end backend functionality."""
    print("==========================================================")
    print("           SENTINEL END-TO-END SMOKE TEST                 ")
    print("==========================================================")
    
    # 1. Initialize Database
    init_db()
    print("[PASS] 1. Database Initialization: SUCCESS")
    
    # 2. Process Sample Complaint A
    c_a = "Water is leaking from the ceiling near the cafeteria."
    res_a = process_complaint(c_a, store_in_db=True)
    assert res_a["complaint_id"] is not None, "Complaint A ID is None"
    print(f"[PASS] 2. Process Complaint A: SUCCESS (Assigned ID #{res_a['complaint_id']}, Category: {res_a['category']}, Urgency: {res_a['urgency']})")
    
    # 3. Process Sample Complaint B (Duplicate of A)
    c_b = "There is water all over the cafeteria floor because one of the pipes is leaking."
    res_b = process_complaint(c_b, store_in_db=True)
    assert res_b["duplicate"]["is_duplicate"] == True, f"Duplicate check failed for Complaint B: {res_b['duplicate']}"
    print(f"[PASS] 3. Duplicate Detection: SUCCESS (Flagged duplicate of #{res_b['duplicate']['matched_id']} with {res_b['duplicate']['similarity']*100:.1f}% similarity)")
    
    # 4. Query All Database Records
    records = get_all_complaints()
    assert len(records) >= 2, f"Expected at least 2 records in DB, found {len(records)}"
    print(f"[PASS] 4. Database Query: SUCCESS (Total records in DB: {len(records)})")
    
    # 5. Update Status Test
    test_id = res_a["complaint_id"]
    updated = update_complaint_status(test_id, "Resolved")
    assert updated == True, "Failed to update status in SQLite DB"
    
    re_check = get_all_complaints()
    target_rec = [r for r in re_check if r["id"] == test_id][0]
    assert target_rec["status"] == "Resolved", f"Status update mismatch: {target_rec['status']}"
    print(f"[PASS] 5. Status Management: SUCCESS (Updated status of #{test_id} to 'Resolved')")
    
    print("\n==========================================================")
    print("             ALL SMOKE TESTS PASSED CLEANLY!              ")
    print("==========================================================")

if __name__ == "__main__":
    run_smoke_test()
