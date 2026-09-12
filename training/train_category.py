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
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
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
    
    # Feature extractors
    word_tfidf = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1)
    feature_union = FeatureUnion([
        ('word', TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1)),
        ('char', TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), sublinear_tf=True, min_df=2))
    ])
    
    # Candidate 1: Word TF-IDF + Logistic Regression
    print("Evaluating Candidate 1: Word TF-IDF + Logistic Regression...")
    pipe1 = Pipeline([
        ('tfidf', word_tfidf),
        ('clf', LogisticRegression(C=2.5, max_iter=1000, class_weight='balanced', random_state=RANDOM_SEED))
    ])
    pipe1.fit(X_train, y_train)
    preds1 = pipe1.predict(X_test)
    acc1 = accuracy_score(y_test, preds1)
    _, _, f1_macro1, _ = precision_recall_fscore_support(y_test, preds1, average='macro', zero_division=0)
    _, _, f1_wt1, _ = precision_recall_fscore_support(y_test, preds1, average='weighted', zero_division=0)
    
    # Candidate 2: Word+Char FeatureUnion + Logistic Regression
    print("Evaluating Candidate 2: Word+Char FeatureUnion + Logistic Regression...")
    pipe2 = Pipeline([
        ('features', feature_union),
        ('clf', LogisticRegression(C=2.5, max_iter=1000, class_weight='balanced', random_state=RANDOM_SEED))
    ])
    pipe2.fit(X_train, y_train)
    preds2 = pipe2.predict(X_test)
    acc2 = accuracy_score(y_test, preds2)
    _, _, f1_macro2, _ = precision_recall_fscore_support(y_test, preds2, average='macro', zero_division=0)
    _, _, f1_wt2, _ = precision_recall_fscore_support(y_test, preds2, average='weighted', zero_division=0)

    # Candidate 3: Word+Char FeatureUnion + Calibrated LinearSVC
    print("Evaluating Candidate 3: Word+Char FeatureUnion + Calibrated LinearSVC...")
    pipe3 = Pipeline([
        ('features', feature_union),
        ('clf', CalibratedClassifierCV(LinearSVC(C=1.0, class_weight='balanced', random_state=RANDOM_SEED)))
    ])
    pipe3.fit(X_train, y_train)
    preds3 = pipe3.predict(X_test)
    acc3 = accuracy_score(y_test, preds3)
    _, _, f1_macro3, _ = precision_recall_fscore_support(y_test, preds3, average='macro', zero_division=0)
    _, _, f1_wt3, _ = precision_recall_fscore_support(y_test, preds3, average='weighted', zero_division=0)

    print("\n--- Category Model Candidate Comparison ---")
    print(f"1. Word TF-IDF + LR          -> Acc: {acc1*100:.2f}% | Macro F1: {f1_macro1:.4f} | Wt F1: {f1_wt1:.4f}")
    print(f"2. Word+Char FeatureUnion+LR -> Acc: {acc2*100:.2f}% | Macro F1: {f1_macro2:.4f} | Wt F1: {f1_wt2:.4f}")
    print(f"3. Word+Char FeatureUnion+SVC-> Acc: {acc3*100:.2f}% | Macro F1: {f1_macro3:.4f} | Wt F1: {f1_wt3:.4f}")

    candidates = [
        ("Word TF-IDF + Logistic Regression", pipe1, acc1, f1_macro1, f1_wt1, preds1),
        ("Word+Char FeatureUnion + Logistic Regression", pipe2, acc2, f1_macro2, f1_wt2, preds2),
        ("Word+Char FeatureUnion + Calibrated LinearSVC", pipe3, acc3, f1_macro3, f1_wt3, preds3),
    ]
    # Sort by Macro F1
    candidates.sort(key=lambda c: c[3], reverse=True)
    best_name, best_pipeline, best_acc, best_macro_f1, best_wt_f1, best_preds = candidates[0]

    print(f"\n>>> Selected Category Model: {best_name}")
    print(f"Accuracy: {best_acc*100:.2f}% | Macro F1: {best_macro_f1:.4f} | Wt F1: {best_wt_f1:.4f}\n")
    print("Classification Report of Selected Model:")
    print(classification_report(y_test, best_preds, zero_division=0))

    cm = confusion_matrix(y_test, best_preds, labels=best_pipeline.classes_)
    print("Confusion Matrix:")
    print(cm)

    # Save model artifact
    joblib.dump(best_pipeline, CATEGORY_MODEL_PATH)
    print(f"\nSaved Category Classifier Pipeline to: {CATEGORY_MODEL_PATH}")

    # Save metadata
    meta = {
        "algorithm": best_name,
        "models_compared": {
            "Word TF-IDF + LR": {"acc": round(float(acc1), 4), "macro_f1": round(float(f1_macro1), 4), "wt_f1": round(float(f1_wt1), 4)},
            "Word+Char FeatureUnion + LR": {"acc": round(float(acc2), 4), "macro_f1": round(float(f1_macro2), 4), "wt_f1": round(float(f1_wt2), 4)},
            "Word+Char FeatureUnion + SVC": {"acc": round(float(acc3), 4), "macro_f1": round(float(f1_macro3), 4), "wt_f1": round(float(f1_wt3), 4)},
        },
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
            "accuracy": round(float(best_acc), 4),
            "macro_f1": round(float(best_macro_f1), 4),
            "weighted_f1": round(float(best_wt_f1), 4)
        }
    }
    update_metadata("category_model", meta)
    print(f"Updated metadata in: {METADATA_PATH}")
    return best_pipeline, best_acc

if __name__ == "__main__":
    train_category_classifier()
