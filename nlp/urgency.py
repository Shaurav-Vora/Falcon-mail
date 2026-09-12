import os
import sys
import joblib
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import URGENCY_MODEL_PATH, EMERGENCY_KEYWORDS, HIGH_URGENCY_KEYWORDS
from nlp.preprocessing import preprocess_text

_urgency_model = None

def get_urgency_model():
    """Lazy load urgency classification ML pipeline."""
    global _urgency_model
    if _urgency_model is None:
        if not os.path.exists(URGENCY_MODEL_PATH):
            raise FileNotFoundError(f"Urgency model artifact missing at {URGENCY_MODEL_PATH}. Run training/train_urgency.py first.")
        _urgency_model = joblib.load(URGENCY_MODEL_PATH)
    return _urgency_model

def predict_urgency(text: str) -> dict:
    """
    Predict complaint urgency level using ML model + Rule Elevation Layer.
    
    Rule Layers:
    1. Critical emergency keywords (fire, smoke, electric shock) -> Elevate to Critical.
    2. High urgency keywords (exam tomorrow, very urgent, asap, immediately) -> Elevate to High.
    """
    processed = preprocess_text(text)["processed_text"]
    model = get_urgency_model()
    
    probabilities = model.predict_proba([processed])[0]
    classes = model.classes_
    
    best_idx = np.argmax(probabilities)
    ml_urgency = str(classes[best_idx])
    confidence = float(probabilities[best_idx])
    
    # Safety & Priority Rule Elevation Check
    text_lower = text.lower()
    matched_keyword = None
    rule_elevated = False
    final_urgency = ml_urgency
    
    # 1. Critical Rule Check
    for kw in EMERGENCY_KEYWORDS:
        if kw in text_lower:
            matched_keyword = kw
            rule_elevated = True
            final_urgency = "Critical"
            break
            
    # 2. High Priority Time-Sensitive Rule Check (if not already Critical)
    if final_urgency not in ["Critical", "High"]:
        for kw in HIGH_URGENCY_KEYWORDS:
            if kw in text_lower:
                matched_keyword = kw
                rule_elevated = True
                final_urgency = "High"
                break
            
    return {
        "urgency": final_urgency,
        "confidence": confidence,
        "ml_predicted_urgency": ml_urgency,
        "rule_elevated": rule_elevated,
        "matched_emergency_keyword": matched_keyword
    }

if __name__ == "__main__":
    sample = "My learning platform is not showing my courses/subjects. i have exam tomorrow. please fix it. it's very urgent"
    result = predict_urgency(sample)
    print("Final Urgency:", result["urgency"])
    print("Rule Elevated:", result["rule_elevated"])
    print("Matched Keyword:", result["matched_emergency_keyword"])
