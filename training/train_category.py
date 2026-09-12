import os
import sys
import json
import hashlib
import datetime
import joblib
import pandas as pd
import sklearn
from sklearn.model_selection import GroupShuffleSplit
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, accuracy_score, precision_recall_fscore_support, confusion_matrix

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import COMPLAINTS_CSV_PATH, CATEGORY_MODEL_PATH, RANDOM_SEED, MODELS_DIR
from nlp.preprocessing import preprocess_text

METADATA_PATH = os.path.join(MODELS_DIR, "training_metadata.json")

def update_metadata(section_key: str, section_data: dict):
    """Safely update a specific model's metadata in training_metadata.json."""
    existing_meta = {}
    if os.path.exists(METADATA_PATH):
        try:
            with open(METADATA_PATH, "r") as f:
                existing_meta = json.load(f)
        except Exception:
            existing_meta = {}
            
    existing_meta[section_key] = section_data
    with open(METADATA_PATH, "w") as f:
        json.dump(existing_meta, f, indent=2)

def train_category_classifier():
    """
    Train TF-IDF + Logistic Regression Pipeline for Complaint Category Classification.
    
    Academic ML Principles Applied:
    - Group-aware Train/Test split using GroupShuffleSplit on `template_group_id`.
    - Zero data leakage: variants of the same template group never appear in both splits.
    - Scikit-Learn Pipeline fits TfidfVectorizer strictly on training split.
    - Evaluates on genuinely unseen test template groups.
    - Records comprehensive academic metrics and metadata.
    """
    print("==========================================================")
    print("   PHASE 4: TRAINING COMPLAINT CATEGORY CLASSIFIER        ")
    print("==========================================================")
    
    if not os.path.exists(COMPLAINTS_CSV_PATH):
        raise FileNotFoundError(f"Dataset not found at {COMPLAINTS_CSV_PATH}. Run dataset_generator.py first.")

    df = pd.read_csv(COMPLAINTS_CSV_PATH)
    
    # Calculate dataset SHA256 hash for audit trail
    with open(COMPLAINTS_CSV_PATH, "rb") as f:
        dataset_hash = hashlib.sha256(f.read()).hexdigest()
    
    # Preprocess text
    print("Preprocessing complaint text...")
    df['processed_text'] = df['text'].apply(lambda x: preprocess_text(x)['processed_text'])
    
    # Group-aware splitting
    gss = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=RANDOM_SEED)
    train_idx, test_idx = next(gss.split(df, groups=df['template_group_id']))
    
    train_df = df.iloc[train_idx]
    test_df = df.iloc[test_idx]
    
    train_groups = set(train_df['template_group_id'])
    test_groups = set(test_df['template_group_id'])
    overlap = train_groups.intersection(test_groups)
    
    print(f"\n--- Data Leakage Verification ---")
    print(f"Total samples: {len(df)}")
    print(f"Train samples: {len(train_df)} | Test samples: {len(test_df)}")
    print(f"Train template groups: {len(train_groups)} | Test template groups: {len(test_groups)}")
    print(f"Group Overlap: {overlap} (Count: {len(overlap)})")
    
    assert len(overlap) == 0, f"DATA LEAKAGE DETECTED: {len(overlap)} template groups overlap between train and test!"
    print("[VERIFIED] Zero data leakage: Train and test template groups are strictly disjoint.\n")
    
    X_train = train_df['processed_text']
    y_train = train_df['category']
    X_test = test_df['processed_text']
    y_test = test_df['category']
    
    # Construct Scikit-Learn ML Pipeline
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=1
        )),
        ('clf', LogisticRegression(
            C=2.5,
            max_iter=1000,
            class_weight='balanced',
            random_state=RANDOM_SEED
        ))
    ])
    
    # Train pipeline ONLY on training split
    pipeline.fit(X_train, y_train)
    
    # Evaluate on unseen test split
    y_pred = pipeline.predict(X_test)
    
    acc = accuracy_score(y_test, y_pred)
    macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(y_test, y_pred, average='macro', zero_division=0)
    wt_p, wt_r, wt_f1, _ = precision_recall_fscore_support(y_test, y_pred, average='weighted', zero_division=0)
    
    print(f"--- Evaluation on Unseen Test Template Groups ---")
    print(f"Accuracy:           {acc * 100:.2f}%")
    print(f"Macro Precision:    {macro_p * 100:.2f}%")
    print(f"Macro Recall:       {macro_r * 100:.2f}%")
    print(f"Macro F1-Score:     {macro_f1 * 100:.2f}%")
    print(f"Weighted Precision: {wt_p * 100:.2f}%")
    print(f"Weighted Recall:    {wt_r * 100:.2f}%")
    print(f"Weighted F1-Score:  {wt_f1 * 100:.2f}%\n")
    
    print("Classification Report:")
    report_dict = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    print(classification_report(y_test, y_pred, zero_division=0))
    
    cm = confusion_matrix(y_test, y_pred, labels=pipeline.classes_)
    print("Confusion Matrix:")
    print(cm)
    
    # Save model artifact
    joblib.dump(pipeline, CATEGORY_MODEL_PATH)
    print(f"\nSaved Category Classifier Pipeline to: {CATEGORY_MODEL_PATH}")
    
    # Save training metadata
    meta = {
        "algorithm": "TF-IDF + LogisticRegression(C=2.5, class_weight='balanced')",
        "dataset_hash": dataset_hash,
        "dataset_size": len(df),
        "train_size": len(train_df),
        "test_size": len(test_df),
        "train_template_groups": len(train_groups),
        "test_template_groups": len(test_groups),
        "group_leakage_detected": False,
        "random_seed": RANDOM_SEED,
        "python_version": sys.version.split()[0],
        "sklearn_version": sklearn.__version__,
        "timestamp": datetime.datetime.now().isoformat(),
        "metrics": {
            "accuracy": round(float(acc), 4),
            "macro_precision": round(float(macro_p), 4),
            "macro_recall": round(float(macro_r), 4),
            "macro_f1": round(float(macro_f1), 4),
            "weighted_precision": round(float(wt_p), 4),
            "weighted_recall": round(float(wt_r), 4),
            "weighted_f1": round(float(wt_f1), 4)
        }
    }
    update_metadata("category_model", meta)
    print(f"Updated metadata in: {METADATA_PATH}")
    
    return pipeline, acc

if __name__ == "__main__":
    train_category_classifier()
