import os
import sys
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, accuracy_score, f1_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import COMPLAINTS_CSV_PATH, URGENCY_MODEL_PATH
from nlp.preprocessing import preprocess_text

def train_urgency_classifier():
    """
    Train TF-IDF + Classifier Pipeline for Urgency Detection.
    Compares Logistic Regression vs Random Forest and saves the superior model.
    """
    print("--- Phase 5: Training Urgency Classifier ---")
    
    if not os.path.exists(COMPLAINTS_CSV_PATH):
        raise FileNotFoundError(f"Dataset not found at {COMPLAINTS_CSV_PATH}. Run dataset_generator.py first.")

    df = pd.read_csv(COMPLAINTS_CSV_PATH)
    df['processed_text'] = df['text'].apply(lambda x: preprocess_text(x)['processed_text'])
    
    X = df['processed_text']
    y = df['urgency']
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    
    # Candidate 1: TF-IDF + Logistic Regression
    lr_pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
        ('clf', LogisticRegression(C=2.0, max_iter=1000, class_weight='balanced', random_state=42))
    ])
    lr_pipeline.fit(X_train, y_train)
    lr_preds = lr_pipeline.predict(X_test)
    lr_f1 = f1_score(y_test, lr_preds, average='weighted')
    lr_acc = accuracy_score(y_test, lr_preds)
    
    # Candidate 2: TF-IDF + Random Forest
    rf_pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
        ('clf', RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced'))
    ])
    rf_pipeline.fit(X_train, y_train)
    rf_preds = rf_pipeline.predict(X_test)
    rf_f1 = f1_score(y_test, rf_preds, average='weighted')
    rf_acc = accuracy_score(y_test, rf_preds)
    
    print(f"Logistic Regression -> Acc: {lr_acc*100:.2f}%, F1: {lr_f1:.4f}")
    print(f"Random Forest       -> Acc: {rf_acc*100:.2f}%, F1: {rf_f1:.4f}")
    
    # Select superior pipeline
    if lr_f1 >= rf_f1:
        best_pipeline = lr_pipeline
        best_name = "Logistic Regression"
        best_acc = lr_acc
        best_preds = lr_preds
    else:
        best_pipeline = rf_pipeline
        best_name = "Random Forest"
        best_acc = rf_acc
        best_preds = rf_preds
        
    print(f"\nSelected Model: {best_name} (Accuracy: {best_acc*100:.2f}%)\n")
    print("Classification Report:")
    print(classification_report(y_test, best_preds))
    
    joblib.dump(best_pipeline, URGENCY_MODEL_PATH)
    print(f"Saved Urgency Classifier Pipeline to: {URGENCY_MODEL_PATH}")
    
    return best_pipeline, best_acc

if __name__ == "__main__":
    train_urgency_classifier()
