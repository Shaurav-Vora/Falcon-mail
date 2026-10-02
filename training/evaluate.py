import os
import sys
import json
import datetime
from pathlib import Path
import pandas as pd
import joblib
from sklearn.metrics import classification_report, accuracy_score, precision_recall_fscore_support, confusion_matrix

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    CORPUS_V2_PATH, CORPUS_V2_SUMMARY_PATH, CATEGORY_MODEL_PATH, URGENCY_MODEL_PATH,
    DEFAULT_DUPLICATE_THRESHOLD, DATA_DIR, MODELS_DIR, UNSEEN_TEST_CSV_PATH
)
from nlp.preprocessing import preprocess_text
from nlp.duplicate_detection import generate_embedding, calculate_similarity
from nlp.urgency import predict_urgency
from nlp.classification import predict_category

DUPLICATE_EVAL_CSV = os.path.join(DATA_DIR, "duplicate_eval_pairs.csv")
METADATA_PATH = Path(MODELS_DIR) / "training_metadata.json"

def evaluate_duplicate_thresholds():
    """
    Evaluate duplicate detection across multiple similarity thresholds on labeled pairs.
    Tests thresholds: 0.60, 0.65, 0.70, 0.75, 0.80, 0.85.
    Calculates TP, FP, TN, FN, Precision, Recall, and F1 for each threshold.
    """
    print("\n==========================================================")
    print(" 3. DUPLICATE DETECTION THRESHOLD EVALUATION (60 PAIRS)   ")
    print("==========================================================")
    
    if not os.path.exists(DUPLICATE_EVAL_CSV):
        print(f"[WARN] Labeled duplicate evaluation file not found at {DUPLICATE_EVAL_CSV}")
        return None
        
    df_pairs = pd.read_csv(DUPLICATE_EVAL_CSV)
    print(f"Loaded {len(df_pairs)} labeled evaluation pairs.")
    print(f"Ground-truth duplicates (label=1): {sum(df_pairs['label'] == 1)}")
    print(f"Ground-truth non-duplicates (label=0): {sum(df_pairs['label'] == 0)}\n")
    
    # Pre-calculate similarity scores for all pairs to be fast
    similarities = []
    for _, row in df_pairs.iterrows():
        sim = calculate_similarity(row['text_a'], row['text_b'])
        similarities.append(sim)
        
    df_pairs['similarity'] = similarities
    
    thresholds = [0.60, 0.65, 0.70, 0.75, 0.80, 0.85]
    results = []
    
    print(f"{'Threshold':<10} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'TP':<4} | {'FP':<4} | {'TN':<4} | {'FN':<4}")
    print("-" * 75)
    
    best_f1 = -1.0
    best_thresh = DEFAULT_DUPLICATE_THRESHOLD
    
    for th in thresholds:
        tp = sum((df_pairs['similarity'] >= th) & (df_pairs['label'] == 1))
        fp = sum((df_pairs['similarity'] >= th) & (df_pairs['label'] == 0))
        tn = sum((df_pairs['similarity'] < th) & (df_pairs['label'] == 0))
        fn = sum((df_pairs['similarity'] < th) & (df_pairs['label'] == 1))
        
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        
        results.append({
            "threshold": th,
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "tp": tp, "fp": fp, "tn": tn, "fn": fn
        })
        
        if f1 > best_f1:
            best_f1 = f1
            best_thresh = th
            
        print(f"{th:<10.2f} | {prec*100:<9.1f}% | {rec*100:<9.1f}% | {f1:<10.4f} | {tp:<4} | {fp:<4} | {tn:<4} | {fn:<4}")
        
    print("-" * 75)
    print(f"\n>>> Selected Validation Threshold: {best_thresh:.2f} (F1-Score: {best_f1:.4f})")
    
    # Error Analysis: Show FP and FN at best threshold
    print(f"\n--- Error Analysis at Selected Threshold ({best_thresh:.2f}) ---")
    fps = df_pairs[(df_pairs['similarity'] >= best_thresh) & (df_pairs['label'] == 0)]
    fns = df_pairs[(df_pairs['similarity'] < best_thresh) & (df_pairs['label'] == 1)]
    
    if len(fps) > 0:
        print(f"False Positives ({len(fps)}):")
        for _, r in fps.head(3).iterrows():
            print(f"  - [{r['similarity']:.2f}] \"{r['text_a'][:35]}...\" vs \"{r['text_b'][:35]}...\" ({r.get('notes', '')})")
    else:
        print("False Positives: 0 (Zero false alarms!)")
        
    if len(fns) > 0:
        print(f"\nFalse Negatives ({len(fns)}):")
        for _, r in fns.head(3).iterrows():
            print(f"  - [{r['similarity']:.2f}] \"{r['text_a'][:35]}...\" vs \"{r['text_b'][:35]}...\" ({r.get('notes', '')})")
    else:
        print("False Negatives: 0")
        
    return results, best_thresh

def evaluate_unseen_handwritten_cases():
    """Evaluate pipeline on hand-written, genuine unseen cases."""
    print("\n==========================================================")
    print(" 4. UNSEEN HUMAN-WRITTEN GENERALIZATION EVALUATION        ")
    print("==========================================================")
    
    if not os.path.exists(UNSEEN_TEST_CSV_PATH):
        print(f"[WARN] Unseen test cases file not found at {UNSEEN_TEST_CSV_PATH}")
        return
        
    df_unseen = pd.read_csv(UNSEEN_TEST_CSV_PATH)
    print(f"Loaded {len(df_unseen)} hand-written holdout test cases.\n")
    
    cat_correct = 0
    urg_correct = 0
    
    print(f"{'Complaint (Snippet)':<40} | {'Exp Cat':<12} | {'Pred Cat':<12} | {'Exp Urg':<8} | {'Pred Urg':<8} | Status")
    print("-" * 105)
    
    for _, row in df_unseen.iterrows():
        txt = row['text']
        exp_c = row['expected_category']
        exp_u = row['expected_urgency']
        
        c_res = predict_category(txt)
        u_res = predict_urgency(txt)
        
        pred_c = c_res['category']
        pred_u = u_res['urgency']
        
        c_match = (pred_c.lower() == exp_c.lower())
        u_match = (pred_u.lower() == exp_u.lower())
        
        if c_match:
            cat_correct += 1
        if u_match:
            urg_correct += 1
            
        status = "EXACT" if (c_match and u_match) else ("CAT_OK" if c_match else ("URG_OK" if u_match else "DIFF"))
        print(f"{txt[:38]:<40} | {exp_c:<12} | {pred_c:<12} | {exp_u:<8} | {pred_u:<8} | {status}")
        
    print("-" * 105)
    print(f"Unseen Holdout Category Accuracy: {cat_correct}/{len(df_unseen)} ({cat_correct/len(df_unseen)*100:.1f}%)")
    print(f"Unseen Holdout Urgency Accuracy:  {urg_correct}/{len(df_unseen)} ({urg_correct/len(df_unseen)*100:.1f}%)")

def _classifier_metrics(y_true, y_pred, include_safety=False):
    _, _, macro_f1, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    _, _, weighted_f1, _ = precision_recall_fscore_support(y_true, y_pred, average="weighted", zero_division=0)
    values = {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "macro_f1": round(float(macro_f1), 4),
        "weighted_f1": round(float(weighted_f1), 4),
    }
    if include_safety:
        report = classification_report(y_true, y_pred, output_dict=True, zero_division=0)
        observed = set(y_true)
        values["critical_recall"] = (
            round(float(report.get("Critical", {}).get("recall", 0.0)), 4)
            if "Critical" in observed else None
        )
        values["high_recall"] = (
            round(float(report.get("High", {}).get("recall", 0.0)), 4)
            if "High" in observed else None
        )
    return values


def _evaluation_details(test_df, predictions, target, labels, include_safety=False):
    report = classification_report(
        test_df[target], predictions, labels=labels, output_dict=True, zero_division=0
    )
    per_class = {
        label: {
            "precision": round(float(report[label]["precision"]), 4),
            "recall": round(float(report[label]["recall"]), 4),
            "f1-score": round(float(report[label]["f1-score"]), 4),
            "support": int(report[label]["support"]),
        }
        for label in labels
    }
    predicted = pd.Series(predictions, index=test_df.index)
    by_source = {}
    for source_type, subset in test_df.groupby("source_type"):
        by_source[str(source_type)] = {
            "records": len(subset),
            **_classifier_metrics(
                subset[target], predicted.loc[subset.index], include_safety=include_safety
            ),
        }
    return {
        "metrics": _classifier_metrics(test_df[target], predictions, include_safety=include_safety),
        "per_class_metrics": per_class,
        "confusion_matrix": {
            "labels": labels,
            "values": confusion_matrix(test_df[target], predictions, labels=labels).tolist(),
        },
        "source_metrics": by_source,
        "evaluated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


def _update_evaluation_metadata(category_details, urgency_details, summary):
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    for key, details in (("category_model", category_details), ("urgency_model", urgency_details)):
        if key not in metadata:
            raise ValueError(f"Training metadata is missing {key}; run both trainers first.")
        metadata[key].update(details)
    metadata["corpus_version"] = str(summary.get("corpus_version", "2.0"))
    metadata["source_counts"] = summary.get("source_counts", {})
    metadata["limitations"] = [
        "The external dataset is small and publisher-labelled; its scores are reported separately.",
        "Critical training examples currently come from the synthetic Falcon Mail source.",
        "Category recall is zero for Cleanliness and Other on the current 135-record test split.",
        "External severity wording strongly influences urgency predictions; routine outages may be over-prioritized.",
        "Urgency labels describe operational priority and do not replace staff safety judgement.",
    ]
    temporary = METADATA_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    temporary.replace(METADATA_PATH)


def run_evaluation():
    """Evaluate trained Falcon Mail classifiers on the stored Corpus v2 test split."""
    print("==========================================================")
    print("       FALCON MAIL NLP - CORPUS V2 EVALUATION             ")
    print("==========================================================\n")

    corpus_path = Path(CORPUS_V2_PATH)
    if not corpus_path.exists():
        raise FileNotFoundError(f"Corpus v2 not found at {corpus_path}.")
    if not Path(CATEGORY_MODEL_PATH).exists() or not Path(URGENCY_MODEL_PATH).exists():
        raise FileNotFoundError("Train both classifiers before running evaluation.")

    frame = pd.read_csv(corpus_path)
    if frame.groupby("incident_group_id")["split"].nunique().max() != 1:
        raise ValueError("Corpus v2 contains incident-group leakage between splits.")
    test_df = frame[frame["split"] == "test"].copy()
    if test_df.empty:
        raise ValueError("Corpus v2 contains no test records.")
    print(f"Using stored test split: {len(test_df)} records")
    test_df["processed_text"] = test_df["text"].map(lambda text: preprocess_text(text)["processed_text"])

    category_model = joblib.load(CATEGORY_MODEL_PATH)
    category_predictions = category_model.predict(test_df["processed_text"])
    category_labels = [str(label) for label in category_model.classes_]
    category_details = _evaluation_details(
        test_df, category_predictions, "category", category_labels
    )
    print("\nCategory classifier")
    print(json.dumps(category_details["metrics"], indent=2))
    print(classification_report(test_df["category"], category_predictions, labels=category_labels, zero_division=0))

    urgency_model = joblib.load(URGENCY_MODEL_PATH)
    urgency_predictions = urgency_model.predict(test_df["processed_text"])
    urgency_labels = [str(label) for label in urgency_model.classes_]
    urgency_details = _evaluation_details(
        test_df, urgency_predictions, "urgency", urgency_labels, include_safety=True
    )
    print("\nUrgency classifier")
    print(json.dumps(urgency_details["metrics"], indent=2))
    print(classification_report(test_df["urgency"], urgency_predictions, labels=urgency_labels, zero_division=0))

    summary = json.loads(Path(CORPUS_V2_SUMMARY_PATH).read_text(encoding="utf-8"))
    _update_evaluation_metadata(category_details, urgency_details, summary)
    print("Performance by source:")
    print(json.dumps({
        "category": category_details["source_metrics"],
        "urgency": urgency_details["source_metrics"],
    }, indent=2))

    evaluate_duplicate_thresholds()
    evaluate_unseen_handwritten_cases()

    print("\n==========================================================")
    print("              END OF FALCON MAIL EVALUATION               ")
    print("==========================================================")

if __name__ == "__main__":
    run_evaluation()
