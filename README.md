# SENTINEL – NLP-Based Complaint & Incident Intelligence System

**SENTINEL** is an end-to-end, locally executed Natural Language Processing (NLP) and Machine Learning (ML) system designed for intelligent university campus complaint triage, prioritization, and resolution management.

The platform processes raw, unstructured complaint text through an academic NLP pipeline: cleaning, categorizing into 11 campus domains, assessing urgency with safety rule overrides, extracting entities and locations, generating executive summaries, detecting duplicates via dense semantic embeddings, and routing incidents to appropriate departments.

---

## 🏛️ System Architecture & Design Principles

```
                              [ Raw Complaint Text ]
                                        │
                                        ▼
                            [ Text Preprocessing ]
                     (Tokenization, Stopwords, Negation)
                                        │
               ┌────────────────────────┼────────────────────────┐
               ▼                        ▼                        ▼
     [ Category Classifier ]  [ Urgency Classifier ]   [ Information Extraction ]
      (TF-IDF + LogReg Pipeline) (TF-IDF + ML Model)   (spaCy NER + Regex)
               │                        │                        │
               │                        ▼                        ▼
               │              [ Safety Rule Override ]     [ Location & Issue ]
               │             (Emergency Keyword Layer)           │
               │                        │                        │
               └────────────────────────┼────────────────────────┘
                                        │
                                        ▼
                          [ Semantic Embedding Engine ]
                        (Sentence-Transformers MiniLM)
                                        │
                                        ▼
                       [ Multi-Signal Duplicate Detection ]
                    (Cosine Sim + Category/Location Bonus)
                                        │
                                        ▼
                      [ Dynamic Structured Summarization ]
                     (Extractive Domain-Routed Summary)
                                        │
                                        ▼
                        [ SQLite Database Persistence ]
                         (Complaints, Embeddings, Status)
                                        │
                                        ▼
                        [ Streamlit Dashboard & Analytics ]
```

---

## 🔍 Model Classification & Component Types

| Component | Architecture / Model | Origin / Type | External Cloud API |
| :--- | :--- | :--- | :--- |
| **Category Classification** | TF-IDF + Logistic Regression Pipeline | **Trained locally by us** | None (Local) |
| **Urgency Classification** | TF-IDF + Logistic Regression (Selected over RF) | **Trained locally by us** | None (Local) |
| **Safety Urgency Override** | Emergency / Time-Sensitive Keyword Rules | **Custom Deterministic Logic** | None (Local) |
| **Entity & Location Extraction** | spaCy `en_core_web_sm` NER + Regex Matchers | **Pretrained Model + Custom Rules** | None (Local) |
| **Semantic Embeddings** | Sentence-Transformers (`all-MiniLM-L6-v2`) | **Pretrained Open-Source** | None (Local) |
| **Duplicate Incident Detection** | Cosine Sim + Composite Category/Location Signals | **Custom Multi-Signal Logic** | None (Local) |
| **Department Routing** | Category-to-Department Mapping | **Custom Deterministic Logic** | None (Local) |
| **Summarization** | Structured Extractive Synthesis | **Custom Modular Logic** | None (Local) |
| **Data Persistence** | SQLite with BLOB vector embeddings | **Database Layer** | None (Local) |
| **User Interface** | Streamlit + Plotly Visualizations | **Custom UI** | None (Local) |

> **Academic Note**: SENTINEL operates **100% locally** without any dependency on external paid cloud APIs (OpenAI, Gemini, Claude, or Hugging Face cloud inference).

---

## 🛡️ Preventing Data Leakage in Dataset Generation & Splitting

### The Problem in Naive Dataset Augmentation
When synthetic datasets generate variations of base complaint templates, a random `train_test_split` creates severe **data leakage**: one variation of a template appears in training while a near-identical paraphrase appears in testing. This inflates accuracy artificially and masks true generalization.

### The SENTINEL Solution
1. **Explicit Template Groups**: Each base complaint is assigned a permanent `template_group_id` (e.g. `T_IT_001`, `T_SAF_005`).
2. **Group-Aware Splitting**: Data splitting is executed strictly via `GroupShuffleSplit(groups=df['template_group_id'])`.
3. **Formal Disjointness Verification**: Training scripts programmatically assert:
   $$\text{train\_template\_groups} \cap \text{test\_template\_groups} = \emptyset$$
   Variants of the same template group never appear in both splits.
4. **Pipeline Encapsulation**: TF-IDF vocabulary and IDF weights are fitted **strictly on the training partition** using `sklearn.pipeline.Pipeline`, preventing vocabulary leakage.

---

## 📊 Evaluation & Empirical Results

### 1. Complaint Category Classification
- **Algorithm**: TF-IDF Vectorizer (`ngram_range=(1, 2)`, sublinear TF) + `LogisticRegression(C=2.5, class_weight='balanced')`
- **Evaluation Partition**: Genuinely unseen template groups (104 samples across 44 disjoint groups)
- **Accuracy**: `29.81%` (honest evaluation on completely novel phrasing across 11 classes; random chance = 9.09%)
- **Macro Precision**: `34.54%` | **Macro Recall**: `35.95%` | **Macro F1**: `32.41%`
- **Weighted Precision**: `35.69%` | **Weighted Recall**: `29.81%` | **Weighted F1**: `29.15%`

### 2. Urgency Classification
- **Algorithm Comparison**:
  - *Logistic Regression*: Accuracy: `40.38%`, Macro F1: `0.3157`, Weighted F1: `0.3911`, High Recall: `48.3%`, Safety Score: `0.2919`
  - *Random Forest*: Accuracy: `36.54%`, Macro F1: `0.2525`, Weighted F1: `0.3206`, High Recall: `13.8%`, Safety Score: `0.2110`
- **Selected Model**: **Logistic Regression** (selected for superior safety-weighted recall and macro F1).
- **Safety Rule Elevation**: Because pure statistical ML classifiers have limited training examples for rare critical emergencies (e.g. gas leaks, live wires), SENTINEL layers a deterministic safety rule override that elevates critical keywords to `Critical` or `High` while preserving the ML model's true statistical confidence transparently.

### 3. Duplicate Detection Threshold Evaluation
Evaluated against 60 labeled sentence pairs spanning duplicates, paraphrases, cross-category incidents, same-location/different-problem cases, and short queries:

| Threshold | Precision | Recall | F1-Score | TP | FP | TN | FN |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0.60 | 100.0% | 83.9% | 0.9123 | 26 | 0 | 29 | 5 |
| **0.65** | **100.0%** | **77.4%** | **0.8727** | **24** | **0** | **29** | **7** |
| 0.70 | 100.0% | 67.7% | 0.8077 | 21 | 0 | 29 | 10 |
| 0.75 | 100.0% | 54.8% | 0.7083 | 17 | 0 | 29 | 14 |
| 0.80 | 100.0% | 32.3% | 0.4878 | 10 | 0 | 29 | 21 |
| 0.85 | 100.0% | 6.5% | 0.1212 | 2 | 0 | 29 | 29 |

- **Selected Validation Threshold**: **0.65** (balances high precision, 0 false alarms, and 77.4% recall).
- **Status-Aware Categorization**:
  - Matched with `Open` or `In Progress` complaints $\rightarrow$ `active_duplicate`
  - Matched with `Resolved` complaints $\rightarrow$ `related_historical`

### 4. Generalization on Human-Written Unseen Holdout Set
Tested on 26 manually authored campus complaints never seen during training or dataset generation:
- **Category Generalization Accuracy**: `65.4%` (17 / 26 correct)
- **Urgency Generalization Accuracy**: `50.0%` (13 / 26 correct)

---

## 📁 Repository Structure

```
NLP Project/
├── assets/
│   ├── manipal_logo.png           # Campus branding logo
│   └── style.css                  # Design system CSS tokens & styles
├── config.py                      # Central configuration, paths, constants, random seed
├── data/
│   ├── complaints.csv             # Labeled dataset with template_group_id (510 samples)
│   ├── duplicate_eval_pairs.csv   # 60 labeled duplicate evaluation pairs
│   └── unseen_test_cases.csv      # 26 hand-written holdout test cases
├── database/
│   ├── database.py                # SQLite layer with connection safety & test isolation
│   └── sentinel.db                # Production/demo SQLite database
├── models/
│   ├── category_classifier.pkl    # Trained Category ML Pipeline
│   ├── urgency_classifier.pkl     # Trained Urgency ML Pipeline
│   └── training_metadata.json     # Audit trail of training parameters & metrics
├── nlp/
│   ├── classification.py          # Category inference module
│   ├── duplicate_detection.py     # SentenceTransformer dense embeddings & composite duplicate logic
│   ├── entity_extraction.py       # spaCy NER, campus location regex & problem pattern parsing
│   ├── pipeline.py                # Master SENTINEL NLP orchestration pipeline
│   ├── preprocessing.py           # Text cleaning, lemmatization & non-download spaCy loader
│   ├── summarization.py           # Dynamic department-routed extractive summarization
│   └── urgency.py                 # ML urgency prediction + Safety rule elevation
├── pages/
│   ├── dashboard.py               # Analytical charts & KPI metrics
│   ├── history.py                 # Filterable incident table & status manager
│   ├── home.py                    # Landing view with quick submission & live insight
│   └── submit_complaint.py        # Detailed submission with chips, tips, and AI audit
├── scripts/
│   └── reset_demo_db.py           # Safe interactive database reset utility
├── tests/
│   └── smoke_test.py              # 13-point automated test suite with temporary DB isolation
├── training/
│   ├── dataset_generator.py       # Group-aware balanced dataset generator
│   ├── evaluate.py                # Multi-component academic evaluation suite
│   ├── train_category.py          # Category classifier training with GroupShuffleSplit
│   └── train_urgency.py           # Urgency classifier training & model selection
├── utils/
│   ├── helpers.py                 # Department mapping helpers
│   └── ui.py                      # Reusable UI components & persistent sidebar collapse
├── app.py                         # Streamlit application entry point
├── README.md                      # Comprehensive project documentation
└── requirements.txt               # Pinned dependencies
```

---

## 🚀 Setup & Execution Guide

### 1. Prerequisites
- Python `3.10` to `3.14`
- Pip package manager

### 2. Install Pinned Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install spaCy Language Model
```bash
python -m spacy download en_core_web_sm
```

### 4. Reproduce Dataset & Models
```bash
# 1. Generate clean dataset with template groups
python training/dataset_generator.py

# 2. Train category classifier
python training/train_category.py

# 3. Train urgency classifier (compares LR vs RF)
python training/train_urgency.py

# 4. Run full academic evaluation (Category, Urgency, 60 Duplicate pairs, Unseen holdout)
python training/evaluate.py
```

### 5. Execute Automated Smoke Test Suite
```bash
# Verifies all 13 components using isolated temporary DB (zero production DB mutations)
python tests/smoke_test.py
```

### 6. Launch Application
```bash
streamlit run app.py
```

---

## 🎓 Viva Questions & Key Explanations

1. **How was data leakage prevented?**
   In natural language generation with augmented templates, randomly splitting sentences causes near-identical phrases to appear in both train and test partitions. We solved this by tagging every base template with a `template_group_id` and splitting exclusively via `GroupShuffleSplit`. We programmatically proved zero overlap between training and testing group IDs.

2. **Why does the urgency model use a hybrid ML + rule approach?**
   Statistical ML classifiers rely on frequency. Life-threatening events (e.g., electrical fires, gas leaks) are inherently rare in campus incident logs. Relying purely on ML risks misclassifying a critical fire hazard as medium or low. SENTINEL pairs a statistical classifier for general incidents with an immediate safety override layer for critical life-safety triggers.

3. **Why is the rule override not reported as 100% confidence?**
   A keyword rule trigger is a deterministic safety policy, not a calibrated statistical probability. Reporting 100% confidence would be mathematically misleading. SENTINEL reports the true ML model probability separately from the rule elevation flag.

4. **Why not use an external LLM API (like GPT-4 or Claude)?**
   Universities and institutions handle private student and staff records. Local models guarantee zero data exfiltration, zero latency from network calls, zero cost per token, and deterministic reproducible behavior suitable for campus deployment.

---

## 🔮 Limitations & Future Work

- **Multi-lingual Support**: Current models process English complaints; future versions can incorporate multilingual models (`paraphrase-multilingual-MiniLM-L12-v2`).
- **File & Image Attachments**: True optical character recognition (OCR) and damage assessment via computer vision can be integrated in future phases.
- **Automated Reopening Workflows**: Status lifecycle enforcement (e.g. reopenings requiring administrative notes).

---

## 👥 Authors
SENTINEL Project Team – University NLP & ML Engineering Laboratory
