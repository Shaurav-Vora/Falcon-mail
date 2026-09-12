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
    Predict complaint urgency level using ML model + Safety Rule Elevation Layer.
    
    Academic Architecture:
    1. Statistical ML Model: TF-IDF + Classifier generates calibrated class probabilities.
    2. Deterministic Safety Fallback Layer: Checks for life safety / critical keywords (fire, smoke, gas leak)
       or time-sensitive terms (exam tomorrow).
    3. Transparent Metadata: ML prediction & ML confidence are preserved separately from rule elevation.
       Confidence is NOT artificially set to 1.0 on rule overrides.
       
    Returns:
        dict: {
            "urgency": str (final_urgency for backward compatibility),
            "final_urgency": str,
            "ml_prediction": str,
            "ml_confidence": float,
            "rule_elevated": bool,
            "rule_trigger": str | None,
            "decision_source": "safety_rule" | "ml"
        }
    """
    processed = preprocess_text(text)["processed_text"]
    model = get_urgency_model()
    
    probabilities = model.predict_proba([processed])[0]
    classes = model.classes_
    
    best_idx = np.argmax(probabilities)
    ml_urgency = str(classes[best_idx])
    ml_confidence = float(probabilities[best_idx])
    
    # Safety & Priority Rule Elevation Check
    text_lower = text.lower()
    matched_keyword = None
    rule_elevated = False
    final_urgency = ml_urgency
    decision_source = "ml"
    
    # 1. Critical Rule Check (Life safety & severe hazard)
    for kw in EMERGENCY_KEYWORDS:
        if kw in text_lower:
            matched_keyword = kw
            rule_elevated = True
            final_urgency = "Critical"
            decision_source = "safety_rule"
            break
            
    # 2. High Priority Time-Sensitive Rule Check (if not already Critical)
    if final_urgency not in ["Critical", "High"]:
        for kw in HIGH_URGENCY_KEYWORDS:
            if kw in text_lower:
                matched_keyword = kw
                rule_elevated = True
                final_urgency = "High"
                decision_source = "safety_rule"
                break
            
    return {
        # Standardized return structure
        "urgency": final_urgency,
        "final_urgency": final_urgency,
        "ml_prediction": ml_urgency,
        "ml_confidence": round(ml_confidence, 4),
        "rule_elevated": rule_elevated,
        "rule_trigger": matched_keyword,
        "decision_source": decision_source,
        # Backward-compatible fields
        "confidence": round(ml_confidence, 4),
        "ml_predicted_urgency": ml_urgency,
        "matched_emergency_keyword": matched_keyword
    }

if __name__ == "__main__":
    sample = "There is smoke coming from the electrical panel near Block A ground floor."
    result = predict_urgency(sample)
    print("Final Urgency:", result["final_urgency"])
    print("ML Prediction:", result["ml_prediction"], f"({result['ml_confidence']*100:.1f}%)")
    print("Decision Source:", result["decision_source"])
    print("Rule Elevated:", result["rule_elevated"])
    print("Rule Trigger:", result["rule_trigger"])
