import os
import sys
import re
import spacy

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SPACY_MODEL_NAME

# Global spaCy model instance
_nlp = None

def get_spacy_nlp():
    """Lazy load spaCy model without silent runtime network downloads."""
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load(SPACY_MODEL_NAME)
        except Exception as e:
            raise RuntimeError(
                f"spaCy model '{SPACY_MODEL_NAME}' is not installed.\n"
                f"Please run the following command in your terminal:\n"
                f"python -m spacy download {SPACY_MODEL_NAME}"
            ) from e
    return _nlp

def preprocess_text(text: str) -> dict:
    """
    Carefully preprocess complaint text for NLP analysis.
    
    Preserves:
    - Room numbers (Room 204, Lab 3)
    - Building names (Block A, Building B)
    - Dates and times
    - Important negations (not, no, never) which impact issue & urgency
    
    Returns:
        dict: {
            "original_text": str,
            "processed_text": str,
            "tokens": list[str]
        }
    """
    if not text or not isinstance(text, str):
        return {"original_text": "", "processed_text": "", "tokens": []}

    original_text = text.strip()
    cleaned = re.sub(r'\s+', ' ', original_text)
    
    nlp = get_spacy_nlp()
    doc = nlp(cleaned)
    
    tokens = []
    processed_tokens = []
    
    NEGATIONS = {"not", "no", "never", "none", "cannot", "n't"}
    
    for token in doc:
        if token.is_space:
            continue
            
        token_text = token.text
        token_lower = token.lower_
        lemma = token.lemma_.lower()
        
        tokens.append(token_text)
        
        if token.is_stop and token_lower not in NEGATIONS:
            continue
            
        if not token.is_punct or token_text in ["-", "_"]:
            processed_tokens.append(lemma)
            
    processed_text = " ".join(processed_tokens)
    
    return {
        "original_text": original_text,
        "processed_text": processed_text if processed_text else cleaned.lower(),
        "tokens": tokens
    }

if __name__ == "__main__":
    test_sample = "There is water leaking from the ceiling near the cafeteria and the floor is very slippery."
    result = preprocess_text(test_sample)
    print("Original:", result["original_text"])
    print("Processed:", result["processed_text"])
