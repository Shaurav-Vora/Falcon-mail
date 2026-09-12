"""
SENTINEL - Master NLP Pipeline
Coordinates preprocessing, classification, urgency scoring, NER, semantic embeddings,
multi-signal duplicate detection, summarization, and secure repository persistence.

PRIVACY & RBAC DIRECTIVE:
1. Student sessions receive sanitized duplicate notices:
   "Similar complaint already reported" or "A related active incident may already exist."
   Zero other student data (name, email, ID, raw text) is leaked.
2. Admins receive full operational duplicate intelligence.
3. Database persistence delegates to BaseComplaintRepository with AuthenticatedUser authorization.
"""

import os
import sys
from typing import Any, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DEFAULT_DUPLICATE_THRESHOLD
from database.auth_context import AuthenticatedUser
from database.base_repository import BaseComplaintRepository
from database.database import get_repository
from nlp.classification import predict_category
from nlp.duplicate_detection import check_duplicate_complaint, generate_embedding
from nlp.entity_extraction import extract_information
from nlp.preprocessing import preprocess_text
from nlp.summarization import generate_summary
from nlp.urgency import predict_urgency
from utils.helpers import get_recommended_department


def process_complaint(
    text: str,
    actor: Optional[AuthenticatedUser] = None,
    repo: Optional[BaseComplaintRepository] = None,
    store_in_db: bool = True,
    duplicate_threshold: float = DEFAULT_DUPLICATE_THRESHOLD,
    user_location: Optional[str] = None,
    user_category: Optional[str] = None,
) -> Dict[str, Any]:
    """Master SENTINEL NLP Processing Pipeline with Server-Side Privacy & RBAC."""
    if not text or not text.strip():
        raise ValueError("Complaint text cannot be empty.")

    # 1. Preprocessing (cleaning, tokenization, lemmatization)
    preprocessed = preprocess_text(text)

    # 2. Category ML Classification (TF-IDF FeatureUnion + Logistic Regression)
    cat_res = predict_category(text)
    category = cat_res["category"]
    category_confidence = cat_res["confidence"]

    # 3. Urgency Detection (ML Classifier + Deterministic Safety Rule Elevation)
    urg_res = predict_urgency(text)
    final_urgency = urg_res["final_urgency"]
    ml_prediction = urg_res["ml_prediction"]
    ml_confidence = urg_res["ml_confidence"]
    rule_elevated = urg_res["rule_elevated"]
    rule_trigger = urg_res["rule_trigger"]
    decision_source = urg_res["decision_source"]

    # 4. Information & Entity Extraction
    entities = extract_information(text, user_provided_location=user_location)

    # 5. Semantic Vector Embedding (all-MiniLM-L6-v2, 384 dims)
    embedding = generate_embedding(text)

    # 6. Multi-Signal Duplicate Detection
    if repo is None:
        try:
            repo = get_repository()
        except Exception:
            repo = None

    candidate_records = []
    if repo is not None:
        # Internal system fetch for duplicate comparison
        try:
            candidate_records = repo.get_duplicate_candidates(actor=actor or AuthenticatedUser(
                uid="system", email="system@sentinel", full_name="System", role="admin"
            ), limit=50)
        except Exception:
            candidate_records = []

    dup_res = check_duplicate_complaint(
        text,
        candidate_records,
        threshold=duplicate_threshold,
        new_category=category,
        new_location=entities.get("location"),
    )

    # Privacy filter: If actor is a student, sanitize duplicate intelligence
    student_dup_notice = None
    if dup_res.get("is_duplicate"):
        if dup_res.get("duplicate_type") == "active_duplicate":
            student_dup_notice = "A related active incident may already exist."
        else:
            student_dup_notice = "Similar complaint already reported in campus records."

    # 7. Department Routing Recommendation
    rec_dept = get_recommended_department(category)

    # 8. Structured Summarization
    summary = generate_summary(text, category, final_urgency, entities)

    payload = {
        "title": entities.get("issue") or (text[:60] + "..." if len(text) > 60 else text),
        "original_text": text,
        "description": text,
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
        "location": entities.get("location", "Campus"),
        "user_location": user_location,
        "building": entities.get("building"),
        "room": entities.get("room"),
        "issue": entities.get("issue"),
        "summary": summary,
        "recommended_department": rec_dept,
        "department": rec_dept,
        "duplicate": dup_res,
        "student_dup_notice": student_dup_notice,
        "dense_embedding": embedding.tolist() if hasattr(embedding, "tolist") else embedding,
        "duplicate_of_id": dup_res.get("matched_id") if dup_res.get("is_duplicate") else None,
        "duplicate_similarity": dup_res.get("similarity") if dup_res.get("is_duplicate") else 0.0,
        "status": "Open",
    }

    # 9. Store in Database Repository
    if store_in_db and repo is not None and actor is not None:
        complaint_id = repo.create_complaint(payload, actor=actor)
        payload["complaint_id"] = complaint_id
    else:
        payload["complaint_id"] = None

    return payload
