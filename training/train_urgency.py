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
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, accuracy_score, precision_recall_fscore_support, confusion_matrix

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import COMPLAINTS_CSV_PATH, URGENCY_MODEL_PATH, RANDOM_SEED, MODELS_DIR
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

def train_urgency_classifier():
    """
    Train TF-IDF + Classifier Pipeline for Urgency Detection.
    
    Academic ML Principles Applied:
    - GroupShuffleSplit on `template_group_id` with central RANDOM_SEED.
    - Zero data leakage between train and test.
    - Compares Logistic Regression vs Random Forest.
    - Evaluates macro F1, weighted F1, and critical safety class recall (Critical & High).
    - Selects superior model based on multi-metric evaluation, not just raw accuracy.
    - Saves winning model artifact and detailed metadata.
    """
    print("==========================================================")
    print("      PHASE 5: TRAINING COMPLAINT URGENCY CLASSIFIER      ")
    print("==========================================================")
    
    if not os.path.exists(COMPLAINTS_CSV_PATH):
        raise FileNotFoundError(f"Dataset not found at {COMPLAINTS_CSV_PATH}. Run dataset_generator.py first.")

    df = pd.read_csv(COMPLAINTS_CSV_PATH)
    
    with open(COMPLAINTS_CSV_PATH, "rb") as f:
        dataset_hash = hashlib.sha256(f.read()).hexdigest()
        
    print("Preprocessing complaint text...")
    df['processed_text'] = df['text'].apply(lambda x: preprocess_text(x)['processed_text'])
    
    # Group-aware train/test split
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
    print(f"Train groups:  {len(train_groups)} | Test groups:  {len(test_groups)}")
    print(f"Group Overlap: {overlap} (Count: {len(overlap)})")
    assert len(overlap) == 0, "Data leakage detected in urgency training split!"
    print("[VERIFIED] Disjoint groups: zero data leakage.\n")
    
    X_train = train_df['processed_text']
    y_train = train_df['urgency']
    X_test = test_df['processed_text']
    y_test = test_df['urgency']
    
    # Candidate 1: TF-IDF + Logistic Regression
    print("Evaluating Candidate 1: Logistic Regression...")
    lr_pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
        ('clf', LogisticRegression(C=2.0, max_iter=1000, class_weight='balanced', random_state=RANDOM_SEED))
    ])
    lr_pipeline.fit(X_train, y_train)
    lr_preds = lr_pipeline.predict(X_test)
    
    lr_acc = accuracy_score(y_test, lr_preds)
    lr_macro_p, lr_macro_r, lr_macro_f1, _ = precision_recall_fscore_support(y_test, lr_preds, average='macro', zero_division=0)
    lr_wt_p, lr_wt_r, lr_wt_f1, _ = precision_recall_fscore_support(y_test, lr_preds, average='weighted', zero_division=0)
    lr_report = classification_report(y_test, lr_preds, output_dict=True, zero_division=0)
    
    lr_crit_rec = lr_report.get('Critical', {}).get('recall', 0.0)
    lr_high_rec = lr_report.get('High', {}).get('recall', 0.0)
    
    # Candidate 2: TF-IDF + Calibrated LinearSVC
    print("Evaluating Candidate 2: Calibrated LinearSVC...")
    svc_pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
        ('clf', CalibratedClassifierCV(LinearSVC(C=1.0, class_weight='balanced', random_state=RANDOM_SEED)))
    ])
    svc_pipeline.fit(X_train, y_train)
    svc_preds = svc_pipeline.predict(X_test)
    
    svc_acc = accuracy_score(y_test, svc_preds)
    svc_macro_p, svc_macro_r, svc_macro_f1, _ = precision_recall_fscore_support(y_test, svc_preds, average='macro', zero_division=0)
    svc_wt_p, svc_wt_r, svc_wt_f1, _ = precision_recall_fscore_support(y_test, svc_preds, average='weighted', zero_division=0)
    svc_report = classification_report(y_test, svc_preds, output_dict=True, zero_division=0)
    svc_crit_rec = svc_report.get('Critical', {}).get('recall', 0.0)
    svc_high_rec = svc_report.get('High', {}).get('recall', 0.0)

    # Candidate 3: TF-IDF + Random Forest Classifier
    print("Evaluating Candidate 3: Random Forest Classifier...")
    rf_pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
        ('clf', RandomForestClassifier(n_estimators=150, class_weight='balanced', random_state=RANDOM_SEED))
    ])
    rf_pipeline.fit(X_train, y_train)
    rf_preds = rf_pipeline.predict(X_test)
    
    rf_acc = accuracy_score(y_test, rf_preds)
    rf_macro_p, rf_macro_r, rf_macro_f1, _ = precision_recall_fscore_support(y_test, rf_preds, average='macro', zero_division=0)
    rf_wt_p, rf_wt_r, rf_wt_f1, _ = precision_recall_fscore_support(y_test, rf_preds, average='weighted', zero_division=0)
    rf_report = classification_report(y_test, rf_preds, output_dict=True, zero_division=0)
    
    rf_crit_rec = rf_report.get('Critical', {}).get('recall', 0.0)
    rf_high_rec = rf_report.get('High', {}).get('recall', 0.0)
    
    print("\n--- Model Comparison Summary ---")
    print(f"1. Logistic Regression -> Acc: {lr_acc*100:.2f}% | Macro F1: {lr_macro_f1:.4f} | Wt F1: {lr_wt_f1:.4f} | Crit Rec: {lr_crit_rec*100:.1f}% | High Rec: {lr_high_rec*100:.1f}%")
    print(f"2. Calibrated LinearSVC -> Acc: {svc_acc*100:.2f}% | Macro F1: {svc_macro_f1:.4f} | Wt F1: {svc_wt_f1:.4f} | Crit Rec: {svc_crit_rec*100:.1f}% | High Rec: {svc_high_rec*100:.1f}%")
    print(f"3. Random Forest       -> Acc: {rf_acc*100:.2f}% | Macro F1: {rf_macro_f1:.4f} | Wt F1: {rf_wt_f1:.4f} | Crit Rec: {rf_crit_rec*100:.1f}% | High Rec: {rf_high_rec*100:.1f}%")
    
    # Model Selection Logic (Weighted priority on Macro F1 and Critical/High safety recall)
    lr_safety_score = (lr_macro_f1 * 0.4) + (lr_wt_f1 * 0.3) + (lr_crit_rec * 0.2) + (lr_high_rec * 0.1)
    svc_safety_score = (svc_macro_f1 * 0.4) + (svc_wt_f1 * 0.3) + (svc_crit_rec * 0.2) + (svc_high_rec * 0.1)
    rf_safety_score = (rf_macro_f1 * 0.4) + (rf_wt_f1 * 0.3) + (rf_crit_rec * 0.2) + (rf_high_rec * 0.1)
    
    candidates = [
        ("Logistic Regression", lr_pipeline, lr_acc, lr_macro_f1, lr_wt_f1, lr_preds, lr_crit_rec, lr_high_rec, lr_safety_score),
        ("Calibrated LinearSVC", svc_pipeline, svc_acc, svc_macro_f1, svc_wt_f1, svc_preds, svc_crit_rec, svc_high_rec, svc_safety_score),
        ("Random Forest", rf_pipeline, rf_acc, rf_macro_f1, rf_wt_f1, rf_preds, rf_crit_rec, rf_high_rec, rf_safety_score),
    ]
    candidates.sort(key=lambda c: c[8], reverse=True)
    best_name, best_pipeline, best_acc, best_macro_f1, best_wt_f1, best_preds, best_crit_rec, best_high_rec, best_safety_score = candidates[0]
    
    selection_reason = (
        f"{best_name} achieved superior safety-weighted score ({best_safety_score:.4f}) "
        f"with Macro F1: {best_macro_f1:.4f}, Critical Recall: {best_crit_rec*100:.1f}%, and High Recall: {best_high_rec*100:.1f}%."
    )
        
    print(f"\n>>> Selected Model: {best_name}")
    print(f"Selection Reason: {selection_reason}\n")
    print("Classification Report of Selected Model:")
    print(classification_report(y_test, best_preds, zero_division=0))
    
    cm = confusion_matrix(y_test, best_preds, labels=best_pipeline.classes_)
    print("Confusion Matrix:")
    print(cm)
    
    # Save selected pipeline
    joblib.dump(best_pipeline, URGENCY_MODEL_PATH)
    print(f"\nSaved Urgency Classifier Pipeline to: {URGENCY_MODEL_PATH}")
    
    # Save training metadata
    meta = {
        "algorithm": f"TF-IDF + {best_name}",
        "selection_reason": selection_reason,
        "models_compared": {
            "Logistic Regression": {
                "accuracy": round(float(lr_acc), 4),
                "macro_f1": round(float(lr_macro_f1), 4),
                "weighted_f1": round(float(lr_wt_f1), 4),
                "critical_recall": round(float(lr_crit_rec), 4),
                "high_recall": round(float(lr_high_rec), 4),
                "safety_score": round(float(lr_safety_score), 4)
            },
            "Random Forest": {
                "accuracy": round(float(rf_acc), 4),
                "macro_f1": round(float(rf_macro_f1), 4),
                "weighted_f1": round(float(rf_wt_f1), 4),
                "critical_recall": round(float(rf_crit_rec), 4),
                "high_recall": round(float(rf_high_rec), 4),
                "safety_score": round(float(rf_safety_score), 4)
            }
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
            "weighted_f1": round(float(best_wt_f1), 4),
            "critical_recall": round(float(best_crit_rec), 4),
            "high_recall": round(float(best_high_rec), 4)
        }
    }
    update_metadata("urgency_model", meta)
    print(f"Updated metadata in: {METADATA_PATH}")
    
    return best_pipeline, best_acc

if __name__ == "__main__":
    train_urgency_classifier()
