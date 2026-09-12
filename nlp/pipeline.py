import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DEFAULT_DUPLICATE_THRESHOLD, DB_PATH
from nlp.preprocessing import preprocess_text
from nlp.classification import predict_category
from nlp.urgency import predict_urgency
from nlp.entity_extraction import extract_information
from nlp.duplicate_detection import generate_embedding, check_duplicate_complaint
from nlp.summarization import generate_summary
from utils.helpers import get_recommended_department
from database.database import init_db, get_all_complaints, insert_complaint

def process_complaint(
    text: str,
    store_in_db: bool = True,
    duplicate_threshold: float = DEFAULT_DUPLICATE_THRESHOLD,
    user_location: str | None = None,
    user_category: str | None = None,
    db_path: str = DB_PATH
) -> dict:
    """
    Master SENTINEL NLP Pipeline.
    
    Academic Engineering Principles:
    - Does NOT mutate original complaint text with location prefixes (prevents classification distortion).
    - Preserves user_location and user_category as separate structured metadata.
    - Transparently separates statistical ML urgency confidence from safety rule overrides.
    - Uses multi-signal composite duplicate detection (semantic + location/category bonuses + status).
    - Database target is injectable for 100% test isolation (prevents test DB pollution).
    """
    if not text or not text.strip():
        raise ValueError("Complaint text cannot be empty.")
        
    # Ensure DB is initialized
    init_db(db_path=db_path)
    
    # 1. Preprocessing (cleaning, tokenization, lemmatization)
    preprocessed = preprocess_text(text)
    
    # 2. Category ML Classification (TF-IDF + Logistic Regression)
    cat_res = predict_category(text)
    category = cat_res["category"]
    category_confidence = cat_res["confidence"]
    
    # 3. Urgency Detection (ML Classifier + Safety Rule Elevation)
    urg_res = predict_urgency(text)
    final_urgency = urg_res["final_urgency"]
    ml_prediction = urg_res["ml_prediction"]
    ml_confidence = urg_res["ml_confidence"]
    rule_elevated = urg_res["rule_elevated"]
    rule_trigger = urg_res["rule_trigger"]
    decision_source = urg_res["decision_source"]
    
    # 4. Information & Entity Extraction (Passing user_location separately)
    entities = extract_information(text, user_provided_location=user_location)
    
    # 5. Semantic Vector Embedding (all-MiniLM-L6-v2)
    embedding = generate_embedding(text)
    
    # 6. Multi-Signal Duplicate Complaint Detection
    existing_records = get_all_complaints(db_path=db_path)
    dup_res = check_duplicate_complaint(
        text,
        existing_records,
        threshold=duplicate_threshold,
        new_category=category,
        new_location=entities["location"]
    )
    
    # 7. Department Routing Recommendation
    rec_dept = get_recommended_department(category)
    
    # 8. Structured Summarization
    summary = generate_summary(text, category, final_urgency, entities)
    
    payload = {
        "original_text": text,
        "processed_text": preprocessed["processed_text"],
        "category": category,
        "category_confidence": round(category_confidence, 4),
        "user_category": user_category,
        "urgency": final_urgency,
        "final_urgency": final_urgency,
        "urgency_confidence": round(ml_confidence, 4),
        "ml_prediction": ml_prediction,
        "ml_confidence": round(ml_confidence, 4),
        "rule_elevated": rule_elevated,
        "rule_trigger": rule_trigger,
        "decision_source": decision_source,
        "entities": entities,
        "location": entities["location"],
        "user_location": user_location,
        "issue": entities["issue"],
        "summary": summary,
        "recommended_department": rec_dept,
        "duplicate": dup_res,
        "embedding": embedding,
        "status": "Open"
    }
    
    # 9. Store in Database
    if store_in_db:
        complaint_id = insert_complaint(payload, db_path=db_path)
        payload["complaint_id"] = complaint_id
    else:
        payload["complaint_id"] = None
        
    return payload

if __name__ == "__main__":
    sample = "There is smoke coming from the electrical panel near Block A ground floor."
    result = process_complaint(sample, store_in_db=False, user_location="Block A Ground Floor")
    print("\n--- Pipeline Execution Test ---")
    print("Category:", result["category"], f"({result['category_confidence']*100:.1f}%)")
    print("Urgency:", result["urgency"], f"(ML was {result['ml_prediction']} at {result['ml_confidence']*100:.1f}%)")
    print("Rule Elevated:", result["rule_elevated"], f"[{result['rule_trigger']}]")
    print("Location:", result["location"])
    print("Summary:", result["summary"])
    print("Duplicate:", result["duplicate"]["duplicate_type"])
