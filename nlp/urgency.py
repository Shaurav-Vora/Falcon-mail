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

def predict_ml_urgency(text: str) -> dict:
    """Predict urgency using only the trained statistical model."""
    processed = preprocess_text(text)["processed_text"]
    model = get_urgency_model()

    probabilities = model.predict_proba([processed])[0]
    classes = model.classes_

    best_idx = np.argmax(probabilities)
    ml_urgency = str(classes[best_idx])
    ml_confidence = float(probabilities[best_idx])

    return {
        "urgency": ml_urgency,
        "final_urgency": ml_urgency,
        "ml_prediction": ml_urgency,
        "ml_confidence": round(ml_confidence, 4),
        "confidence": round(ml_confidence, 4),
        "ml_predicted_urgency": ml_urgency,
    }


def apply_safety_rules(text: str, ml_result: dict) -> dict:
    """Apply transparent deterministic safety elevation to an ML prediction."""
    ml_urgency = str(ml_result["ml_prediction"])
    ml_confidence = float(ml_result["ml_confidence"])
    text_lower = text.lower()
    matched_keyword = None
    rule_elevated = False
    final_urgency = ml_urgency
    decision_source = "ml"
    
    for kw in EMERGENCY_KEYWORDS:
        if kw in text_lower:
            matched_keyword = kw
            rule_elevated = True
            final_urgency = "Critical"
            decision_source = "safety_rule"
            break
            
    if final_urgency not in ["Critical", "High"]:
        for kw in HIGH_URGENCY_KEYWORDS:
            if kw in text_lower:
                matched_keyword = kw
                rule_elevated = True
                final_urgency = "High"
                decision_source = "safety_rule"
                break
            
    return {
        "urgency": final_urgency,
        "final_urgency": final_urgency,
        "ml_prediction": ml_urgency,
        "ml_confidence": round(ml_confidence, 4),
        "rule_elevated": rule_elevated,
        "rule_trigger": matched_keyword,
        "decision_source": decision_source,
        "confidence": round(ml_confidence, 4),
        "ml_predicted_urgency": ml_urgency,
        "matched_emergency_keyword": matched_keyword
    }


def predict_urgency(text: str) -> dict:
    """Backward-compatible wrapper for ML prediction plus safety elevation."""
    return apply_safety_rules(text, predict_ml_urgency(text))

if __name__ == "__main__":
    sample = "There is smoke coming from the electrical panel near Block A ground floor."
    result = predict_urgency(sample)
    print("Final Urgency:", result["final_urgency"])
    print("ML Prediction:", result["ml_prediction"], f"({result['ml_confidence']*100:.1f}%)")
    print("Decision Source:", result["decision_source"])
    print("Rule Elevated:", result["rule_elevated"])
    print("Rule Trigger:", result["rule_trigger"])
