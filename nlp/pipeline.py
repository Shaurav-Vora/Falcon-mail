import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DEFAULT_DUPLICATE_THRESHOLD
from nlp.preprocessing import preprocess_text
from nlp.classification import predict_category
from nlp.urgency import predict_urgency
from nlp.entity_extraction import extract_information
from nlp.duplicate_detection import generate_embedding, check_duplicate_complaint
from nlp.summarization import generate_summary
from utils.helpers import get_recommended_department
from database.database import init_db, get_all_complaints, insert_complaint

def process_complaint(text: str, store_in_db: bool = True, duplicate_threshold: float = DEFAULT_DUPLICATE_THRESHOLD) -> dict:
    """
    Master SENTINEL NLP Pipeline.
    
    Pipeline Steps:
    1. Preprocessing (cleaning, tokenization, lemmatization)
    2. Category Classification (TF-IDF + Logistic Regression ML Model)
    3. Urgency Detection (ML Classifier + Safety Rule Elevation)
    4. Information & Entity Extraction (spaCy NER + custom Matcher)
    5. Semantic Embedding Vector Generation (Sentence-Transformers all-MiniLM-L6-v2)
    6. Duplicate Complaint Detection (Cosine Similarity check against DB records)
    7. Recommended Department Mapping
    8. Structured Summarization
    9. SQLite Database Persistence
    """
    if not text or not text.strip():
        raise ValueError("Complaint text cannot be empty.")
        
    # Ensure DB is initialized
    init_db()
    
    # 1. Preprocessing
    preprocessed = preprocess_text(text)
    
    # 2. Category ML Classification
    cat_res = predict_category(text)
    category = cat_res["category"]
    category_confidence = cat_res["confidence"]
    
    # 3. Urgency Detection (ML + Safety Override)
    urg_res = predict_urgency(text)
    urgency = urg_res["urgency"]
    urgency_confidence = urg_res["confidence"]
    rule_elevated = urg_res["rule_elevated"]
    
    # 4. Information & Entity Extraction
    entities = extract_information(text)
    
    # 5. Semantic Vector Embedding
    embedding = generate_embedding(text)
    
    # 6. Duplicate Complaint Detection
    existing_records = get_all_complaints()
    dup_res = check_duplicate_complaint(text, existing_records, threshold=duplicate_threshold)
    
    # 7. Department Routing Recommendation
    rec_dept = get_recommended_department(category)
    
    # 8. Structured Summarization
    summary = generate_summary(text, category, urgency, entities)
    
    payload = {
        "original_text": text,
        "processed_text": preprocessed["processed_text"],
        "category": category,
        "category_confidence": round(category_confidence, 4),
        "urgency": urgency,
        "urgency_confidence": round(urgency_confidence, 4),
        "rule_elevated": rule_elevated,
        "entities": entities,
        "issue": entities["issue"],
        "summary": summary,
        "recommended_department": rec_dept,
        "duplicate": dup_res,
        "embedding": embedding,
        "status": "Open"
    }
    
    # 9. Store in Database
    if store_in_db:
        complaint_id = insert_complaint(payload)
        payload["complaint_id"] = complaint_id
    else:
        payload["complaint_id"] = None
        
    return payload

if __name__ == "__main__":
    sample = "There is water leaking from the ceiling near the cafeteria and the floor is very slippery. Someone almost fell."
    print("\n--- Running Master NLP Pipeline Test ---")
    result = process_complaint(sample, store_in_db=True)
    
    print("\nProcessed Pipeline Payload:")
    print("Complaint ID:", result.get("complaint_id"))
    print("Category:", result["category"], f"({result['category_confidence']*100:.1f}%)")
    print("Urgency:", result["urgency"], f"({result['urgency_confidence']*100:.1f}%)", "Rule Elevated:" if result["rule_elevated"] else "")
    print("Location:", result["entities"]["location"])
    print("Issue:", result["issue"])
    print("Summary:", result["summary"])
    print("Recommended Dept:", result["recommended_department"])
    print("Duplicate Status:", result["duplicate"])
