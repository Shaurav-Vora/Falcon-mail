# 🛡️ SENTINEL – NLP-Based Complaint & Incident Intelligence System

**SENTINEL** is an NLP-driven complaint and incident management system designed for university campuses (and adaptable to municipal, corporate, hospital, and school environments).

The platform allows users to submit raw natural language complaint text, which is processed locally using machine learning and NLP techniques (scikit-learn, spaCy, Sentence Transformers) without relying on external cloud LLM APIs.

---

## 🌟 Key Features

1. **Text Preprocessing & Lemmatization**: Standard cleaning while preserving critical room numbers, building names, dates, times, and negation keywords.
2. **Locally Trained Category Classification**: TF-IDF Vectorizer + Logistic Regression pipeline classifying complaints into 11 categories (*IT, Maintenance, Safety, Academic, Administration, Transport, Facilities, Cleanliness, Electrical, Plumbing, Other*).
3. **Locally Trained Urgency Classification**: ML classifier predicting priority levels (*Low, Medium, High, Critical*) combined with a safety rule override layer for dangerous emergencies (*fire, smoke, electric shock*).
4. **Entity & Information Extraction**: spaCy Named Entity Recognition combined with custom Matchers for room labels (*Room 204, Lab 3*), building names (*Block A*), dates, times, and main issue phrases.
5. **Semantic Duplicate Complaint Detection**: Sentence-Transformers (`all-MiniLM-L6-v2`) generating 384-dimensional dense vector embeddings compared against existing database complaints via Cosine Similarity with configurable thresholds.
6. **Structured Summarization**: Automated concise summary generation.
7. **Automated Department Routing**: Maps complaint category to the responsible campus department.
8. **SQLite Persistence**: Stores complaints, NLP analysis metadata, and binary BLOB vector embeddings.
9. **Interactive Admin Dashboard & Plotly Analytics**: Real-time KPI metrics, filterable table, complaint status updating (*Open, In Progress, Resolved, Rejected*), and visual analytical charts.

---

## 📊 Model & Component Architecture

| Component | Architecture / Model | Source / Type |
| :--- | :--- | :--- |
| **Category Classification** | TF-IDF + Logistic Regression Pipeline | **Trained Locally by Us** |
| **Urgency Detection** | TF-IDF + Logistic Regression / Random Forest | **Trained Locally by Us** |
| **Safety Override** | Keyword Rule Elevation Layer (*fire, smoke, shock*) | **Custom Rule Logic** |
| **Information Extraction** | spaCy `en_core_web_sm` NER + Regex Matcher | **Pretrained + Custom Rules** |
| **Duplicate Detection** | Sentence Transformer (`all-MiniLM-L6-v2`) + Cosine Sim | **Pretrained Embedding Model** |
| **Department Routing** | Category-to-Department Mapping | **Custom Rule Logic** |
| **Summarization** | Structured Extractive Synthesis | **Custom Modular Logic** |

---

## 🔬 Academic ML Performance Summary

- **Category Classifier Accuracy**: `83.91%` (Precision: `86.97%`, Recall: `83.91%`, F1-Score: `83.47%`)
- **Urgency Classifier Accuracy**: `88.51%` (Precision: `89.47%`, Recall: `88.51%`, F1-Score: `88.31%`)
- **Train / Test Split**: 80% Training / 20% Stratified Test Split (preventing data leakage by fitting TF-IDF strictly on training data).

---

## ⚙️ Installation & Running Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Download spaCy English Language Model
```bash
python -m spacy download en_core_web_sm
```

### 3. Generate Dataset & Train Models
```bash
# Generate synthetic dataset (data/complaints.csv)
python training/dataset_generator.py

# Train Category Classifier (models/category_classifier.pkl)
python training/train_category.py

# Train Urgency Classifier (models/urgency_classifier.pkl)
python training/train_urgency.py

# Run Academic Evaluation Report
python training/evaluate.py
```

### 4. Launch Streamlit Application
```bash
streamlit run app.py
```

---

## 🧪 Test Cases & Expected Outputs

### Test Case 1 (Safety / Critical - Rule Override)
- **Input**: `"There is smoke coming from an electrical panel near Block A ground floor."`
- **Expected Category**: `Safety` or `Electrical`
- **Expected Urgency**: `Critical` (Triggered by safety rule override keyword *smoke*)
- **Extracted Location**: `Block A`

### Test Case 2 (IT / Medium)
- **Input**: `"The Wi-Fi in Computer Lab 3 keeps disconnecting every few minutes."`
- **Expected Category**: `IT`
- **Expected Urgency**: `Medium`
- **Extracted Location**: `Computer Lab 3`

### Test Case 3 (Cleanliness / Medium)
- **Input**: `"Restroom near the main cafeteria has not been cleaned since yesterday."`
- **Expected Category**: `Cleanliness`
- **Expected Urgency**: `Medium`
- **Extracted Location**: `Cafeteria`

### Test Case 4 (IT / High - Time Sensitivity)
- **Input**: `"The classroom projector in Room 304 is not working and our presentation starts in 20 minutes."`
- **Expected Category**: `IT`
- **Expected Urgency**: `High`
- **Extracted Location**: `Room 304`

### Test Case 5 (Duplicate Complaint Detection Pair)
- **Complaint 1**: `"Water is leaking from the ceiling near the cafeteria and the floor is very slippery."`
- **Complaint 2**: `"There is water all over the cafeteria floor because one of the pipes is leaking."`
- **Expected Result**: Semantic similarity `~87.0%` (Flagged as **Duplicate Complaint**).

---

## 🎓 Viva & Project Presentation Guide

### 1. How does TF-IDF work?
TF-IDF (*Term Frequency - Inverse Document Frequency*) converts raw text into numerical feature vectors.
- **Term Frequency (TF)** measures how often a word appears in a specific complaint.
- **Inverse Document Frequency (IDF)** penalizes common words (like *the, is, at*) that appear across many complaints, emphasizing unique domain words (like *projector, leaking, Wi-Fi*).

### 2. How does Logistic Regression learn?
Logistic Regression fits a linear decision boundary across TF-IDF feature space using the softmax/sigmoid function to output class probabilities for each category.

### 3. What prevents Data Leakage in our ML pipeline?
We use Scikit-Learn `Pipeline([('tfidf', TfidfVectorizer()), ('clf', LogisticRegression())])` combined with `train_test_split(stratify=y)`. Fitting TF-IDF only on `X_train` ensures vocabulary and document frequencies from `X_test` remain completely unseen until evaluation.

### 4. How does Duplicate Detection work without exact keyword matching?
We use Sentence Transformer model `all-MiniLM-L6-v2` to map complaint sentences into 384-dimensional dense vector space embeddings. Cosine similarity measures the angle between vectors, identifying semantic similarity even when different words are used (*e.g., "water leaking" vs "pipe spraying water"*).

---

## 👥 Authors
University NLP Project Team – **SENTINEL**
>>>>>>> cd4cff8 (Initial commit: SENTINEL AI Complaint Intelligence Portal)
