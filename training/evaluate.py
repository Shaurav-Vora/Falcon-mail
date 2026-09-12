import os
import sys
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import classification_report, accuracy_score, precision_recall_fscore_support, confusion_matrix

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    COMPLAINTS_CSV_PATH, CATEGORY_MODEL_PATH, URGENCY_MODEL_PATH,
    DEFAULT_DUPLICATE_THRESHOLD, RANDOM_SEED, DATA_DIR, UNSEEN_TEST_CSV_PATH
)
from nlp.preprocessing import preprocess_text
from nlp.duplicate_detection import generate_embedding, calculate_similarity
from nlp.urgency import predict_urgency
from nlp.classification import predict_category

DUPLICATE_EVAL_CSV = os.path.join(DATA_DIR, "duplicate_eval_pairs.csv")

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

def run_evaluation():
    """Complete Academic Model Evaluation Script for SENTINEL."""
    print("==========================================================")
    print("      SENTINEL NLP SYSTEM - ACADEMIC EVALUATION REPORT    ")
    print("==========================================================\n")
    
    if not os.path.exists(COMPLAINTS_CSV_PATH):
        raise FileNotFoundError(f"Dataset not found at {COMPLAINTS_CSV_PATH}. Run dataset_generator.py first.")
        
    df = pd.read_csv(COMPLAINTS_CSV_PATH)
    print("Preprocessing text for evaluation...")
    df['processed_text'] = df['text'].apply(lambda x: preprocess_text(x)['processed_text'])

    # Group-aware split
    gss = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=RANDOM_SEED)
    train_idx, test_idx = next(gss.split(df, groups=df['template_group_id']))
    
    test_df = df.iloc[test_idx]
    
    # ----------------------------------------------------
    # 1. CATEGORY CLASSIFIER EVALUATION
    # ----------------------------------------------------
    print("\n==========================================================")
    print(" 1. EVALUATING COMPLAINT CATEGORY CLASSIFIER (UNSEEN)     ")
    print("==========================================================")
    if not os.path.exists(CATEGORY_MODEL_PATH):
        raise FileNotFoundError("Category model not found. Train model first using train_category.py.")
        
    cat_pipeline = joblib.load(CATEGORY_MODEL_PATH)
    
    X_test_c = test_df['processed_text']
    y_test_c = test_df['category']
    
    y_pred_cat = cat_pipeline.predict(X_test_c)
    cat_acc = accuracy_score(y_test_c, y_pred_cat)
    macro_p_c, macro_r_c, macro_f1_c, _ = precision_recall_fscore_support(y_test_c, y_pred_cat, average='macro', zero_division=0)
    wt_p_c, wt_r_c, wt_f1_c, _ = precision_recall_fscore_support(y_test_c, y_pred_cat, average='weighted', zero_division=0)
    
    print(f"Accuracy:           {cat_acc * 100:.2f}%")
    print(f"Macro Precision:    {macro_p_c * 100:.2f}%")
    print(f"Macro Recall:       {macro_r_c * 100:.2f}%")
    print(f"Macro F1-Score:     {macro_f1_c * 100:.2f}%")
    print(f"Weighted Precision: {wt_p_c * 100:.2f}%")
    print(f"Weighted Recall:    {wt_r_c * 100:.2f}%")
    print(f"Weighted F1-Score:  {wt_f1_c * 100:.2f}%\n")
    print("Detailed Classification Report (Category):")
    print(classification_report(y_test_c, y_pred_cat, zero_division=0))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test_c, y_pred_cat, labels=cat_pipeline.classes_))

    # ----------------------------------------------------
    # 2. URGENCY CLASSIFIER EVALUATION
    # ----------------------------------------------------
    print("\n==========================================================")
    print(" 2. EVALUATING URGENCY CLASSIFIER (UNSEEN GROUPS)         ")
    print("==========================================================")
    if not os.path.exists(URGENCY_MODEL_PATH):
        raise FileNotFoundError("Urgency model not found. Train model first using train_urgency.py.")
        
    urg_pipeline = joblib.load(URGENCY_MODEL_PATH)
    
    X_test_u = test_df['processed_text']
    y_test_u = test_df['urgency']
    
    y_pred_urg = urg_pipeline.predict(X_test_u)
    urg_acc = accuracy_score(y_test_u, y_pred_urg)
    macro_p_u, macro_r_u, macro_f1_u, _ = precision_recall_fscore_support(y_test_u, y_pred_urg, average='macro', zero_division=0)
    wt_p_u, wt_r_u, wt_f1_u, _ = precision_recall_fscore_support(y_test_u, y_pred_urg, average='weighted', zero_division=0)
    
    print(f"Accuracy:           {urg_acc * 100:.2f}%")
    print(f"Macro Precision:    {macro_p_u * 100:.2f}%")
    print(f"Macro Recall:       {macro_r_u * 100:.2f}%")
    print(f"Macro F1-Score:     {macro_f1_u * 100:.2f}%")
    print(f"Weighted Precision: {wt_p_u * 100:.2f}%")
    print(f"Weighted Recall:    {wt_r_u * 100:.2f}%")
    print(f"Weighted F1-Score:  {wt_f1_u * 100:.2f}%\n")
    print("Detailed Classification Report (Urgency):")
    print(classification_report(y_test_u, y_pred_urg, zero_division=0))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test_u, y_pred_urg, labels=urg_pipeline.classes_))

    # ----------------------------------------------------
    # 3. DUPLICATE DETECTION EVALUATION
    # ----------------------------------------------------
    evaluate_duplicate_thresholds()

    # ----------------------------------------------------
    # 4. UNSEEN HUMAN-WRITTEN TEST CASES
    # ----------------------------------------------------
    evaluate_unseen_handwritten_cases()

    print("\n==========================================================")
    print("                 END OF ACADEMIC EVALUATION               ")
    print("==========================================================")

if __name__ == "__main__":
    run_evaluation()
