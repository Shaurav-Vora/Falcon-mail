# SENTINEL – Enterprise Campus Incident Intelligence & Resolution Platform
### NLP-Driven Complaint Intelligence, Firebase Auth, Cloud Firestore & Server-Side RBAC
**Manipal Academy of Higher Education Dubai Campus**

---

## 🏛️ Executive Overview

**SENTINEL** is an enterprise-grade multi-user intelligence platform for university campus incident reporting, automated natural language triage, and administrative resolution workflows.

The system bridges classical machine learning with secure cloud persistence:
1. **100% Local NLP Pipeline**: Category classification (`FeatureUnion` word+char n-grams), urgency assessment with deterministic safety rule elevation, spaCy named entity and campus location extraction, dense semantic vector embeddings (`all-MiniLM-L6-v2`), multi-signal duplicate detection with student privacy preservation, and domain-routed summarization.
2. **Multi-User Security & Server-Side RBAC**: Firebase Authentication with custom user claims. Public registration is strictly restricted to students; staff roles are provisioned through server CLI. Every backend repository function validates `actor: AuthenticatedUser` server-side, ensuring students can never view or modify another student's complaints.
3. **Shared Cloud Firestore Persistence**: Cloud Firestore serves as the single source of truth (`SENTINEL_STORAGE_BACKEND = "firestore"`), with atomic transactions for administrator assignments, server timestamps (`firestore.SERVER_TIMESTAMP`), and immutable audit logging.
4. **Near-Real-Time Synchronization**: Live 1–2 second synchronization across active student and administrator browser sessions powered by Streamlit `@st.fragment(run_every="2s")` without full-app reload loops.

---

## 📐 System Architecture

```
                          [ Client Browser Session (Student / Admin) ]
                                                │
                                    (Email/Password Auth)
                                                ▼
                                    [ Firebase Auth REST ]
                                     (ID Token + Refresh)
                                                │
                                                ▼
                                   [ AuthenticatedUser Context ]
                             { uid, email, full_name, role, student_id }
                                                │
                    ┌───────────────────────────┴───────────────────────────┐
                    ▼                                                       ▼
         [ Student Workflow ]                                    [ Admin Workflow ]
       - Home (Personal KPIs)                                  - Operations Dashboard
       - Submit Complaint                                      - Prioritized Queue (P0->P3)
       - My Complaints (Own records only)                       - Atomic "Assign to Myself"
       - In-App Notifications                                  - Mandatory Resolution Notes
                    │                                          - Resolved Cases Archive
                    └───────────────────────────┬───────────────────────────┘
                                                │
                                                ▼
                                  [ Server-Side RBAC Guard ]
                        - Enforces: actor.role == "admin" for Admin APIs
                        - Enforces: actor.uid == complaint.reporter_uid
                        - Sanitizes duplicate notifications for Students
                                                │
                                                ▼
                                   [ Master NLP Pipeline ]
                               (100% Local Python Execution)
                        ├─ Preprocessing & Lemmatization
                        ├─ Word + Char FeatureUnion Category ML
                        ├─ Balanced Urgency ML + Safety Rule Elevation
                        ├─ spaCy NER + Problem Pattern Extraction
                        ├─ MiniLM Dense Semantic Embeddings (384 dims)
                        └─ Extractive Domain-Routed Summarization
                                                │
                                                ▼
                                  [ Cloud Firestore Backend ]
                         - users/{uid}
                         - complaints/{id}
                         - complaints/{id}/events/{id} (Audit Subcollection)
                         - notifications/{id}
```

---

## 🛡️ Security Model & Role-Based Access Control (RBAC)

### 1. Server-Side Enforcement (Primary Defense)
Because SENTINEL runs as a Python server application using `firebase-admin`, all backend calls bypass Firestore Security Rules automatically. Therefore:
- **Primary Authorization**: Enforced directly inside Python repository methods ([database/firestore_repository.py](file:///c:/NLP%20Project/database/firestore_repository.py)).
- `get_student_complaints(uid, actor)`: Strictly asserts `actor.uid == uid or actor.role == "admin"`. Students cannot access another student's complaints.
- `get_unresolved_complaints(actor)`: Strictly requires `actor.role == "admin"`.
- `update_complaint_status(cid, status, actor, note)`: Strictly requires `actor.role == "admin"`.
- `assign_complaint(cid, actor)`: Strictly requires `actor.role == "admin"`.
- `firestore.rules`: Maintained as defense-in-depth for any future direct web clients. Never contains `allow read, write: if true;`.

### 2. Zero-Trust Identity & Admin Provisioning
- **Public Signup**: Creates user in Firebase Auth and profile in `users/{uid}` strictly with `role = "student"`. Public visitors cannot select an admin role.
- **Admin Provisioning Tool**: Administrators are provisioned strictly via server CLI:
  ```bash
  python scripts/set_admin_role.py --email admin@manipal.edu
  ```
  This sets the Firebase Custom User Claim `{"admin": True}` and updates `users/{uid}.role = "admin"`.
- **Institutional Domain Filtering**: Configurable in `config.py` via `ALLOWED_STUDENT_EMAIL_DOMAINS = ["manipal.edu", "learner.manipal.edu"]`.

### 3. Student Duplicate Privacy Preservation
When duplicate detection identifies an existing active ticket:
- **Student UI**: Displays ONLY: *"Similar complaint already reported in campus records"* or *"A related active incident may already exist."* Zero other student metadata (name, student ID, email, or raw complaint text) is exposed.
- **Admin UI**: Displays full operational duplicate intelligence (similarity score, matched complaint text, and ticket ID).

---

## ⚡ Near-Real-Time Synchronization

SENTINEL implements near-real-time synchronization using Streamlit `@st.fragment(run_every="2s")`:
- **Student My Complaints**: Auto-refreshes complaint status badges and administrator resolution notes every 2 seconds.
- **Student Notifications**: In-app feed polls unread alerts every 2 seconds.
- **Admin Queue**: Unresolved complaints appear automatically within ~1–2 seconds of student submission.
- **Admin KPIs**: Incident count cards update live without full-page reloads.

---

## 🧠 NLP Models & Empirical Evaluation

| Component | Architecture / Model | Origin / Type | External Cloud API |
| :--- | :--- | :--- | :--- |
| **Category Classification** | Word+Char `FeatureUnion` + Logistic Regression | **Trained locally by us** | None (Local) |
| **Urgency Classification** | TF-IDF + Logistic Regression (Balanced Critical) | **Trained locally by us** | None (Local) |
| **Safety Urgency Override** | Emergency Keyword Layer (*fire, gas leak, wire, shock*) | **Custom Deterministic Policy** | None (Local) |
| **Entity & Location Extraction** | spaCy `en_core_web_sm` + Regex Matchers | **Pretrained + Custom Rules** | None (Local) |
| **Semantic Vector Embeddings** | Sentence-Transformers (`all-MiniLM-L6-v2`) | **Pretrained Open-Source** | None (Local) |
| **Duplicate Detection** | Multi-Signal Composite Cosine Similarity | **Custom Multi-Signal Logic** | None (Local) |
| **Summarization** | Extractive Domain-Routed Synthesis | **Custom Modular Logic** | None (Local) |

### Empirical Performance Summary:
1. **Category Classification**: Word+Char `FeatureUnion` achieved **Macro F1: 0.3254** and **Accuracy: 31.36%** on completely unseen template groups (random chance across 11 classes = 9.09%).
2. **Urgency Classification**: Expanded dataset with 35 new diverse Critical campus emergencies (103 Critical samples total). Pure ML Critical recall reached **21.4%** (up from 0.0%), augmented to **100%** on emergency triggers via the deterministic safety override.
3. **Duplicate Detection Threshold**:
   - Evaluated on 60 labeled pairs (31 duplicates, 29 non-duplicates):
     - **Threshold 0.60**: Precision: **100.0%**, Recall: **83.9%**, F1: **0.9123**, FP: **0**, FN: **5**.
     - **Threshold 0.65**: Precision: **100.0%**, Recall: **77.4%**, F1: **0.8727**, FP: **0**, FN: **7**.
   - Threshold **0.60** maintains zero false positives while improving recall (+6.5%), making it the confirmed defensible default.

---

## 📁 Repository Structure

```
NLP Project/
├── assets/
│   ├── manipal_logo.png           # University branding logo
│   └── style.css                  # Custom enterprise design system
├── config.py                      # Central configuration, thresholds, allowed domains
├── data/
│   ├── complaints.csv             # Labeled dataset with template_group_id (585 samples)
│   ├── duplicate_eval_pairs.csv   # 60 labeled duplicate evaluation pairs
│   └── unseen_test_cases.csv      # 26 hand-written holdout test cases
├── database/
│   ├── auth_context.py            # AuthenticatedUser frozen context dataclass
│   ├── base_repository.py         # Abstract base repository defining data contracts
│   ├── database.py                # Central repository factory (no silent fallback)
│   ├── firestore_repository.py    # Cloud Firestore repository with server-side RBAC
│   └── sqlite_repository.py       # Isolated SQLite repository for automated tests
├── models/
│   ├── category_classifier.pkl    # Trained Category FeatureUnion Pipeline
│   ├── urgency_classifier.pkl     # Trained Urgency Pipeline
│   └── training_metadata.json     # Audit trail of model parameters & metrics
├── nlp/
│   ├── classification.py          # Category inference module
│   ├── duplicate_detection.py     # SentenceTransformer embeddings & composite scoring
│   ├── entity_extraction.py       # spaCy NER & campus location extractors
│   ├── pipeline.py                # Master NLP pipeline with duplicate privacy filter
│   ├── preprocessing.py           # Text cleaning, lemmatization & spaCy loader
│   ├── summarization.py           # Domain-routed extractive summarization
│   └── urgency.py                 # ML urgency prediction + safety rule elevation
├── pages/
│   ├── admin_queue.py             # Admin prioritized queue with atomic assignment
│   ├── dashboard.py               # Campus operations analytics & live KPIs
│   ├── home.py                    # Student home with personal KPIs & quick submit
│   ├── login.py                   # Secure login, registration & password reset
│   ├── notifications.py           # Student in-app notifications feed
│   ├── resolved_cases.py          # Closed complaint archive with resolution notes
│   ├── student_complaints.py      # Student "My Complaints" with live status sync
│   └── submit_complaint.py        # Detailed submission with chips, tips & AI audit
├── scripts/
│   ├── migrate_sqlite_to_firestore.py  # Standalone SQLite -> Firestore migration utility
│   ├── reset_demo_db.py           # Safe local SQLite reset utility
│   └── set_admin_role.py          # CLI tool to grant admin custom claim
├── tests/
│   ├── smoke_test.py              # 13-point end-to-end smoke test suite
│   ├── test_auth.py               # Authentication & domain validation tests
│   └── test_rbac.py               # Server-side RBAC and data isolation tests
├── training/
│   ├── dataset_generator.py       # Group-aware balanced dataset generator (255 groups)
│   ├── evaluate.py                # Evaluation suite (Category, Urgency, Duplicates, Holdout)
│   ├── train_category.py          # Category classifier training with FeatureUnion
│   └── train_urgency.py           # Urgency classifier training & model comparison
├── utils/
│   ├── auth.py                    # Firebase Auth REST client & session manager
│   ├── helpers.py                 # Department mapping helpers
│   └── ui.py                      # Dynamic role-based sidebar & persistent collapse
├── app.py                         # Streamlit application entry point & router
├── firestore.rules                # Defense-in-depth Firestore security rules
├── requirements.txt               # Pinned Python dependencies
└── README.md                      # Comprehensive documentation
```

---

## 🚀 Setup & Execution Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Configure Firebase Credentials
1. **Service Account Key**: Place your downloaded Firebase private key in the project root as `serviceAccountKey.json`.
2. **Streamlit Secrets**: Create `.streamlit/secrets.toml` (template provided in `.streamlit/secrets.toml.example`):
   ```toml
   [firebase]
   api_key = "YOUR_FIREBASE_WEB_API_KEY"
   auth_domain = "your-project-id.firebaseapp.com"
   project_id = "your-project-id"
   storage_bucket = "your-project-id.firebasestorage.app"
   messaging_sender_id = "YOUR_SENDER_ID"
   app_id = "YOUR_APP_ID"
   service_account_path = "serviceAccountKey.json"
   ```
   *(Both files are strictly ignored in `.gitignore` to prevent secret leakage).*

### 3. Provision an Administrator Account
```bash
python scripts/set_admin_role.py --email admin@manipal.edu
```
> [!NOTE]
> For evaluation and immediate testing on the configured cloud project, a pre-provisioned administrator account is active:
> - **Email**: `admin@manipal.edu`
> - **Password**: `AdminPassword123!`
> New student accounts can be registered directly through the application login portal.


### 4. Run Automated Test Suites
```bash
# Run unit tests (Auth & RBAC)
python -m unittest discover tests

# Run end-to-end smoke tests (13/13 verified with isolated test DB)
python tests/smoke_test.py
```

### 5. Launch the Application
```bash
streamlit run app.py
```

---

## 👥 Authors
SENTINEL Project Team – University NLP & ML Engineering Laboratory
Manipal Academy of Higher Education Dubai Campus
