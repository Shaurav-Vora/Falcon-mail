import os
import sys
import numpy as np
from sentence_transformers import SentenceTransformer, util

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SENTENCE_TRANSFORMER_MODEL, DEFAULT_DUPLICATE_THRESHOLD

_embedder = None

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

def check_duplicate_complaint(new_text: str, existing_complaints: list[dict], threshold: float = DEFAULT_DUPLICATE_THRESHOLD) -> dict:
    """
    Check if a new complaint is a semantic duplicate of any existing complaint.
    
    Args:
        new_text (str): Raw text of the incoming complaint.
        existing_complaints (list[dict]): List of dicts containing 'id', 'text', and 'embedding'.
        threshold (float): Similarity threshold (default 0.80).
        
    Returns:
        dict: {
            "is_duplicate": bool,
            "similarity": float,
            "matched_id": int | None,
            "matched_text": str | None
        }
    """
    if not existing_complaints:
        return {
            "is_duplicate": False,
            "similarity": 0.0,
            "matched_id": None,
            "matched_text": None
        }
        
    # Generate embedding vector for incoming complaint
    new_vector = generate_embedding(new_text)
    
    best_similarity = 0.0
    matched_complaint = None
    
    for item in existing_complaints:
        existing_vector = item.get("embedding")
        if existing_vector is None:
            continue
            
        # Convert bytes or list back to numpy array if stored serialized
        if isinstance(existing_vector, (bytes, bytearray)):
            existing_vector = np.frombuffer(existing_vector, dtype=np.float32)
        elif isinstance(existing_vector, list):
            existing_vector = np.array(existing_vector, dtype=np.float32)
            
        # Calculate Cosine Similarity
        similarity = float(util.cos_sim(new_vector, existing_vector)[0][0])
        
        if similarity > best_similarity:
            best_similarity = similarity
            matched_complaint = item
            
    is_duplicate = best_similarity >= threshold
    
    return {
        "is_duplicate": is_duplicate,
        "similarity": round(best_similarity, 4),
        "matched_id": matched_complaint["id"] if matched_complaint else None,
        "matched_text": matched_complaint["text"] if matched_complaint else None
    }

if __name__ == "__main__":
    c1 = "Water is leaking from the ceiling near the cafeteria."
    c2 = "There is a leaking pipe causing water on the food court floor."
    
    vec1 = generate_embedding(c1)
    vec2 = generate_embedding(c2)
    
    db_mock = [{"id": 1, "text": c1, "embedding": vec1}]
    dup_res = check_duplicate_complaint(c2, db_mock)
    
    print("Complaint 1:", c1)
    print("Complaint 2:", c2)
    print("Duplicate Check Result:", dup_res)
