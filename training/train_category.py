import os
import sys
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import COMPLAINTS_CSV_PATH, CATEGORY_MODEL_PATH
from nlp.preprocessing import preprocess_text

def train_category_classifier():
    """
    Train TF-IDF + Logistic Regression Pipeline for Complaint Category Classification.
    
    Academic ML Principles Applied:
    - Stratified Train/Test split (80/20) to maintain class proportions.
    - Scikit-Learn Pipeline fits TfidfVectorizer strictly on training split to prevent Data Leakage.
    - Evaluates performance on unseen test split.
    - Saves trained pipeline artifact to models/category_classifier.pkl.
    """
    print("--- Phase 4: Training Complaint Category Classifier ---")
    
    if not os.path.exists(COMPLAINTS_CSV_PATH):
        raise FileNotFoundError(f"Dataset not found at {COMPLAINTS_CSV_PATH}. Run dataset_generator.py first.")

    df = pd.read_csv(COMPLAINTS_CSV_PATH)
    
    # Preprocess text
    df['processed_text'] = df['text'].apply(lambda x: preprocess_text(x)['processed_text'])
    
    X = df['processed_text']
    y = df['category']
    
    # Stratified Train/Test split (80% Train, 20% Test)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    
    print(f"Total dataset size: {len(df)}")
    print(f"Training samples: {len(X_train)}, Testing samples: {len(X_test)}")
    
    # Construct Scikit-Learn ML Pipeline
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=1
        )),
        ('clf', LogisticRegression(
            C=2.0,
            max_iter=1000,
            class_weight='balanced',
            random_state=42
        ))
    ])
    
    # Train model (Fit only on training set!)
    pipeline.fit(X_train, y_train)
    
    # Evaluate on unseen test set
    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    
    print(f"\nCategory Classification Accuracy: {acc * 100:.2f}%\n")
    print("Classification Report:")
    print(classification_report(y_test, y_pred))
    
    cm = confusion_matrix(y_test, y_pred)
    print("Confusion Matrix shape:", cm.shape)
    
    # Save model pipeline artifact
    joblib.dump(pipeline, CATEGORY_MODEL_PATH)
    print(f"Saved Category Classifier Pipeline to: {CATEGORY_MODEL_PATH}")
    
    return pipeline, acc

if __name__ == "__main__":
    train_category_classifier()
