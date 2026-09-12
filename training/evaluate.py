import os
import sys
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, precision_recall_fscore_support, confusion_matrix

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import COMPLAINTS_CSV_PATH, CATEGORY_MODEL_PATH, URGENCY_MODEL_PATH, DEFAULT_DUPLICATE_THRESHOLD
from nlp.preprocessing import preprocess_text
from nlp.duplicate_detection import generate_embedding, check_duplicate_complaint

def run_evaluation():
    """
    Complete Academic Model Evaluation Script for SENTINEL.
    Evaluates locally trained Category Classifier, Urgency Classifier, and Duplicate Detection.
    """
    print("==========================================================")
    print("      SENTINEL NLP SYSTEM - ACADEMIC EVALUATION REPORT    ")
    print("==========================================================\n")
    
    if not os.path.exists(COMPLAINTS_CSV_PATH):
        raise FileNotFoundError(f"Dataset not found at {COMPLAINTS_CSV_PATH}. Run dataset_generator.py first.")
        
    df = pd.read_csv(COMPLAINTS_CSV_PATH)
    df['processed_text'] = df['text'].apply(lambda x: preprocess_text(x)['processed_text'])

    # ----------------------------------------------------
    # 1. CATEGORY CLASSIFIER EVALUATION
    # ----------------------------------------------------
    print("1. EVALUATING COMPLAINT CATEGORY CLASSIFIER")
    print("----------------------------------------------------------")
    if not os.path.exists(CATEGORY_MODEL_PATH):
        raise FileNotFoundError("Category model not found. Train model first using train_category.py.")
        
    cat_pipeline = joblib.load(CATEGORY_MODEL_PATH)
    
    X_cat = df['processed_text']
    y_cat = df['category']
    
    X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(
        X_cat, y_cat, test_size=0.20, random_state=42, stratify=y_cat
    )
    
    y_pred_cat = cat_pipeline.predict(X_test_c)
    cat_acc = accuracy_score(y_test_c, y_pred_cat)
    p_c, r_c, f1_c, _ = precision_recall_fscore_support(y_test_c, y_pred_cat, average='weighted')
    
    print(f"Accuracy:  {cat_acc * 100:.2f}%")
    print(f"Precision: {p_c * 100:.2f}%")
    print(f"Recall:    {r_c * 100:.2f}%")
    print(f"F1-Score:  {f1_c * 100:.2f}%\n")
    print("Detailed Classification Report (Category):")
    print(classification_report(y_test_c, y_pred_cat))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test_c, y_pred_cat))

    # ----------------------------------------------------
    # 2. URGENCY CLASSIFIER EVALUATION
    # ----------------------------------------------------
    print("\n\n2. EVALUATING URGENCY CLASSIFIER")
    print("----------------------------------------------------------")
    if not os.path.exists(URGENCY_MODEL_PATH):
        raise FileNotFoundError("Urgency model not found. Train model first using train_urgency.py.")
        
    urg_pipeline = joblib.load(URGENCY_MODEL_PATH)
    
    X_urg = df['processed_text']
    y_urg = df['urgency']
    
    X_train_u, X_test_u, y_train_u, y_test_u = train_test_split(
        X_urg, y_urg, test_size=0.20, random_state=42, stratify=y_urg
    )
    
    y_pred_urg = urg_pipeline.predict(X_test_u)
    urg_acc = accuracy_score(y_test_u, y_pred_urg)
    p_u, r_u, f1_u, _ = precision_recall_fscore_support(y_test_u, y_pred_urg, average='weighted')
    
    print(f"Accuracy:  {urg_acc * 100:.2f}%")
    print(f"Precision: {p_u * 100:.2f}%")
    print(f"Recall:    {r_u * 100:.2f}%")
    print(f"F1-Score:  {f1_u * 100:.2f}%\n")
    print("Detailed Classification Report (Urgency):")
    print(classification_report(y_test_u, y_pred_urg))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test_u, y_pred_urg))

    # ----------------------------------------------------
    # 3. DUPLICATE DETECTION SIMILARITY EVALUATION
    # ----------------------------------------------------
    print("\n\n3. EVALUATING DUPLICATE DETECTION (SENTENCE TRANSFORMERS)")
    print("----------------------------------------------------------")
    
    test_pairs = [
        ("Water is leaking from the ceiling near the cafeteria.", 
         "There is water all over the cafeteria floor because one of the pipes is leaking.", True),
        ("The Wi-Fi in Lab 205 is disconnected.", 
         "Wi-Fi in Lab 205 is not working.", True),
        ("The classroom projector in Room 304 is not working.", 
         "Restroom near cafeteria has not been cleaned since yesterday.", False)
    ]
    
    print(f"{'Complaint A':<45} | {'Complaint B':<45} | {'Sim Score':<10} | Result")
    print("-" * 115)
    
    for c_a, c_b, expected in test_pairs:
        v_a = generate_embedding(c_a)
        db_record = [{"id": 101, "text": c_a, "embedding": v_a}]
        res = check_duplicate_complaint(c_b, db_record, threshold=DEFAULT_DUPLICATE_THRESHOLD)
        sim = res["similarity"]
        is_dup = res["is_duplicate"]
        status_str = "MATCH (PASS)" if is_dup == expected else "MISMATCH (FAIL)"
        print(f"{c_a[:44]:<45} | {c_b[:44]:<45} | {sim*100:.1f}%     | {status_str}")

    print("\n==========================================================")
    print("                 END OF ACADEMIC EVALUATION               ")
    print("==========================================================")

if __name__ == "__main__":
    run_evaluation()
