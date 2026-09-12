import os
import sys
import joblib
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import CATEGORY_MODEL_PATH
from nlp.preprocessing import preprocess_text

_category_model = None

def get_category_model():
    """Lazy load category classification ML pipeline."""
    global _category_model
    if _category_model is None:
        if not os.path.exists(CATEGORY_MODEL_PATH):
            raise FileNotFoundError(f"Category classifier model artifact missing at {CATEGORY_MODEL_PATH}. Run training/train_category.py first.")
        _category_model = joblib.load(CATEGORY_MODEL_PATH)
    return _category_model

def predict_category(text: str) -> dict:
    """
    Predict complaint category using our locally trained TF-IDF + Logistic Regression pipeline.
    
    Returns:
        dict: {
            "category": str,
            "confidence": float,
            "probabilities": dict[str, float]
        }
    """
    processed = preprocess_text(text)["processed_text"]
    model = get_category_model()
    
    # Predict category probabilities
    probabilities = model.predict_proba([processed])[0]
    classes = model.classes_
    
    best_idx = np.argmax(probabilities)
    predicted_category = classes[best_idx]
    confidence = float(probabilities[best_idx])
    
    prob_dict = {cls: float(prob) for cls, prob in zip(classes, probabilities)}
    
    return {
        "category": str(predicted_category),
        "confidence": confidence,
        "probabilities": prob_dict
    }

if __name__ == "__main__":
    sample = "The Wi-Fi network in computer lab 4 keeps disconnecting."
    result = predict_category(sample)
    print("Predicted Category:", result["category"])
    print("Confidence:", f"{result['confidence']*100:.1f}%")
