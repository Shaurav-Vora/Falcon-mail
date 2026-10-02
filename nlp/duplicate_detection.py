import os
import sys
import re
import numpy as np
from sentence_transformers import SentenceTransformer, util

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SENTENCE_TRANSFORMER_MODEL, DEFAULT_DUPLICATE_THRESHOLD

_embedder = None

CATEGORY_DISAGREEMENT_MIN_SIMILARITY = 0.70

NON_INCIDENT_UPDATE_PATTERNS = [
    r'\b(?:working|operating|functioning)\s+(?:normally\s+)?again\b',
    r'\b(?:is|are|was|were|has been|have been)\s+(?:now\s+)?'
    r'(?:fixed|resolved|restored|repaired)\b',
    r'\bno longer\s+(?:broken|down|offline|leaking|blocked|stuck)\b',
    r'\bearlier report\s+(?:was|is)?\s*incorrect\b',
    r'\bfalse report\b',
    r'\bno\s+(?:smoke|active fire|gas leak|water leak)\s+'
    r'(?:is\s+)?(?:present|remaining|now|anymore)\b',
]

RECURRENCE_PATTERN = re.compile(
    r'\b(?:but|however|yet)\b.*\b'
    r'(?:again|still|continues?|returned|recurred|down|offline|broken|leaking|not working)\b',
    re.IGNORECASE,
)

STRUCTURED_LOCATION_PATTERN = re.compile(
    r'\b(?P<kind>room|lab|hall|block|building)\s*'
    r'(?:(?:number\b|no\.)\s*)?#?\s*'
    r'(?P<identifier>[A-Za-z](?:-?\d{1,4})?|\d{1,4}(?:-?[A-Za-z])?)\b',
    re.IGNORECASE,
)


def _is_non_incident_update(text: str) -> bool:
    """Identify clear resolution/retraction text that should not open a duplicate."""
    if RECURRENCE_PATTERN.search(text):
        return False
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in NON_INCIDENT_UPDATE_PATTERNS)


def _structured_location_ids(location: str | None) -> dict[str, set[str]]:
    """Return comparable room/block identifiers without treating named areas as IDs."""
    identifiers: dict[str, set[str]] = {}
    if not location or location.strip().lower() in {"not specified", "campus"}:
        return identifiers

    for match in STRUCTURED_LOCATION_PATTERN.finditer(location):
        kind = match.group("kind").lower()
        if kind == "building":
            kind = "block"
        identifiers.setdefault(kind, set()).add(match.group("identifier").lower())
    return identifiers


def _has_location_conflict(location_a: str | None, location_b: str | None) -> bool:
    """Reject only explicit conflicts of the same identifier type."""
    ids_a = _structured_location_ids(location_a)
    ids_b = _structured_location_ids(location_b)
    for kind in ids_a.keys() & ids_b.keys():
        if ids_a[kind].isdisjoint(ids_b[kind]):
            return True
    return False

def get_sentence_transformer():
    """Lazy load SentenceTransformer embedding model (all-MiniLM-L6-v2)."""
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)
    return _embedder

def generate_embedding(text: str) -> np.ndarray:
    """Generate 384-dimensional semantic embedding vector for text."""
    model = get_sentence_transformer()
    embedding = model.encode(text, convert_to_tensor=False)
    return embedding

def calculate_similarity(text_a: str, text_b: str) -> float:
    """Calculate cosine similarity between two sentences."""
    v1 = generate_embedding(text_a)
    v2 = generate_embedding(text_b)
    sim = float(util.cos_sim(v1, v2)[0][0])
    return round(sim, 4)

def check_duplicate_complaint(
    new_text: str,
    existing_complaints: list[dict],
    threshold: float = DEFAULT_DUPLICATE_THRESHOLD,
    new_category: str | None = None,
    new_location: str | None = None
) -> dict:
    """
    Check if a new complaint is an active duplicate or related historical incident.
    
    Academic Multi-Signal Architecture (Issue 8 & Corrections 6 & 7):
    - Primary Signal: Deep semantic similarity using Sentence-Transformers (all-MiniLM-L6-v2).
    - Supporting Signals: Soft category match bonus (+0.03) and location match bonus (+0.05).
      Does NOT strictly filter by category since classification errors can occur.
    - Status Contextual Factor:
      * Matches with 'Open' or 'In Progress' complaints -> 'active_duplicate'
      * Matches with 'Resolved' complaints -> 'related_historical'
      * Below threshold -> 'none'
    
    Returns:
        dict: {
            "is_duplicate": bool,
            "duplicate_type": "active_duplicate" | "related_historical" | "none",
            "matched_id": int | None,
            "matched_text": str | None,
            "similarity": float,
            "composite_score": float,
            "same_category": bool,
            "same_location": bool
        }
    """
    if not existing_complaints or _is_non_incident_update(new_text):
        return {
            "is_duplicate": False,
            "duplicate_type": "none",
            "matched_id": None,
            "matched_text": None,
            "similarity": 0.0,
            "composite_score": 0.0,
            "same_category": False,
            "same_location": False,
            "decision_reason": (
                "resolution_or_retraction"
                if existing_complaints
                else "no_candidates"
            ),
        }
        
    new_vector = generate_embedding(new_text)
    
    best_similarity = 0.0
    best_composite = 0.0
    best_match = None
    best_same_cat = False
    best_same_loc = False
    rejection_reason = None
    
    for item in existing_complaints:
        existing_vector = item.get("embedding") if item.get("embedding") is not None else item.get("dense_embedding")
        if existing_vector is None:
            continue
            
        if isinstance(existing_vector, (bytes, bytearray)):
            existing_vector = np.frombuffer(existing_vector, dtype=np.float32)
        elif isinstance(existing_vector, list):
            existing_vector = np.array(existing_vector, dtype=np.float32)
            
        sim = float(util.cos_sim(new_vector, existing_vector)[0][0])
        
        # Supporting signals
        same_cat = False
        if new_category and item.get("category"):
            same_cat = (new_category.lower() == str(item.get("category")).lower())
            
        same_loc = False
        item_loc = item.get("location")
        if new_location and item_loc and new_location.lower() != "not specified" and item_loc.lower() != "not specified":
            same_loc = (new_location.lower() in item_loc.lower() or item_loc.lower() in new_location.lower())

        if _has_location_conflict(new_location, item_loc):
            rejection_reason = "location_conflict"
            continue

        if (
            new_category
            and item.get("category")
            and not same_cat
            and sim < CATEGORY_DISAGREEMENT_MIN_SIMILARITY
        ):
            rejection_reason = "category_disagreement_low_similarity"
            continue
            
        # Composite score calculation (semantic is primary, bonuses applied only if baseline similarity >= 0.55)
        bonus = 0.0
        if sim >= 0.55:
            if same_cat:
                bonus += 0.03
            if same_loc:
                bonus += 0.05
                
        composite = min(1.0, sim + bonus)
        
        if composite > best_composite:
            best_composite = composite
            best_similarity = sim
            best_match = item
            best_same_cat = same_cat
            best_same_loc = same_loc
            
    # Decision logic based on threshold
    if best_composite >= threshold and best_match is not None:
        status = str(best_match.get("status", "Open")).strip()
        if status.lower() == "resolved":
            dup_type = "related_historical"
            is_dup = False  # Not an active duplicate blocking resolution
            decision_reason = "related_historical"
        else:
            dup_type = "active_duplicate"
            is_dup = True
            decision_reason = "score_at_or_above_threshold"
    else:
        dup_type = "none"
        is_dup = False
        decision_reason = rejection_reason or "below_threshold"
        
    return {
        "is_duplicate": is_dup,
        "duplicate_type": dup_type,
        "matched_id": (
            best_match.get("id") or best_match.get("complaint_id")
            if best_match
            else None
        ),
        "matched_text": best_match.get("complaint_text") or best_match.get("text") if best_match else None,
        "similarity": round(best_similarity, 4),
        "composite_score": round(best_composite, 4),
        "same_category": best_same_cat,
        "same_location": best_same_loc,
        "decision_reason": decision_reason,
    }

if __name__ == "__main__":
    c1 = "Water is leaking from the ceiling near the cafeteria."
    c2 = "There is a leaking pipe causing water on the cafeteria floor."
    
    vec1 = generate_embedding(c1)
    db_mock = [{"id": 1, "text": c1, "embedding": vec1, "category": "Plumbing", "location": "Cafeteria", "status": "Open"}]
    
    res = check_duplicate_complaint(c2, db_mock, threshold=0.75, new_category="Plumbing", new_location="Cafeteria")
    print("Complaint 1:", c1)
    print("Complaint 2:", c2)
    print("Duplicate Check Result:", res)
