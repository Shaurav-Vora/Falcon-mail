# Falcon Mail

Falcon Mail is a campus ticketing project for students. A student submits a problem through the web app, and an NLP pipeline automatically categorizes it, estimates its urgency, extracts its location, checks for similar incidents, summarizes it, and routes it to the right department.

Administrators can see the saved result of every pipeline stage. The trace is real data from the processing run, not an animation.

## NLP pipeline

1. **Preprocess** the complaint with spaCy.
2. **Classify the category** with a TF-IDF + calibrated LinearSVC model.
3. **Classify urgency** with a second TF-IDF + calibrated LinearSVC model.
4. **Apply safety rules** so words such as `fire` and `smoke` can elevate a ticket to Critical.
5. **Extract details** using spaCy and campus-specific location patterns.
6. **Detect duplicates** using `all-MiniLM-L6-v2` embeddings and ticket context.
7. **Create a summary** using an operational template.
8. **Route and save** the ticket in Firebase Cloud Firestore.

The application supports one source: tickets raised directly in the web portal.

## Corpus

The main reviewed corpus is [`data/processed/corpus_v2.csv`](data/processed/corpus_v2.csv). It contains 917 approved complaints across 441 incident groups. Related versions of the same incident stay in the same train, validation, or test split to reduce data leakage.

The data folders are:

- `data/raw/falcon_mail_v1/` — the original project dataset kept as an immutable source.
- `data/raw/university_students_complaints/` — imported public student-complaint data.
- `data/processed/corpus_v2.csv` — the clean training corpus.
- `data/processed/corpus_v2_review.csv` — row-level review record.
- `data/metadata/corpus_v2_summary.json` — sources, counts, review decisions, and limitations.
- `data/unseen_test_cases.csv` — 26 manually written generalization examples.
- `data/duplicate_eval_pairs.csv` — labeled pairs for the duplicate threshold.

The Corpus page in the admin account provides a visual summary. The dataset is intentionally modest and imbalanced, so it is suitable for a student project rather than a production deployment.

Current untouched test-split results:

| Model | Accuracy | Macro F1 |
| --- | ---: | ---: |
| Category | 60.74% | 0.5073 |
| Urgency | 47.41% | 0.3621 |

On the 26 handwritten examples, category accuracy is 69.2% and urgency accuracy is 50.0%. Critical safety cases are also protected by explicit safety rules.

## Project structure

```text
Falcon-mail/
├── app.py                 # Streamlit entry point
├── config.py              # paths, categories, rules, and routing
├── assets/                # logo and app styling
├── data/                  # raw, reviewed, and evaluation data
├── database/              # Firebase repository and data contracts
├── models/                # trained category and urgency models
├── nlp/                   # the NLP pipeline and its stages
├── pages/                 # student and administrator screens
├── scripts/               # administrator setup helper
├── training/              # corpus preparation, training, and evaluation
└── utils/                 # authentication and shared UI code
```

## Setup on Windows

Python 3.14 is the currently tested environment.

```powershell
cd C:\dev\Falcon-mail
uv python install 3.14
uv venv --python 3.14 .venv
.venv\Scripts\Activate.ps1
$env:UV_LINK_MODE = "copy"
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
uv run --python .venv\Scripts\python.exe python -m spacy download en_core_web_sm
```

`UV_LINK_MODE=copy` avoids Windows/OneDrive hard-link error 396.

## Firebase setup

Falcon Mail uses Firebase Authentication and Cloud Firestore.

1. Register a Firebase web app and copy its configuration values.
2. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in the web-app values.
3. In Firebase Console, open **Project settings → Service accounts → Firebase Admin SDK** and generate a private key.
4. Save the downloaded file as `serviceAccountKey.json` in the project root.
5. Enable Email/Password authentication and create a Cloud Firestore database.

The Firebase web configuration is safe to use in a client, but never commit `serviceAccountKey.json` or `.streamlit/secrets.toml`.

To give an existing Firebase user administrator access:

```powershell
python scripts/set_admin_role.py student@example.com
```

Sign out and back in after changing the role.

## Run the application

```powershell
.venv\Scripts\Activate.ps1
streamlit run app.py
```

Open the local address printed by Streamlit, normally `http://localhost:8501`.

## Manual testing

Create a student account and try these tickets:

| Purpose | Example complaint | Expected result |
| --- | --- | --- |
| IT | `The internet keeps dropping every few minutes in the engineering lab.` | IT, routed to IT Support & Services |
| Safety | `There is smoke and fire coming from the electrical room in Block B.` | Safety, Critical |
| Duplicate | Submit a close variation of the fire ticket | Related active incident warning |
| Extraction | `The projector in Room 206, Block A is flickering.` | Room and block extracted |

Then sign in as an administrator and check:

- **Live tickets** — select a ticket and inspect each saved NLP stage.
- **Dashboard** — view category, urgency, status, and department totals.
- **Corpus** — inspect dataset sources and class balance.
- **Models** — view model methods and measured results.
- **Resolved** — review completed cases and correction history.

## Retraining

The committed model files are ready to use. To rebuild them from the reviewed corpus:

```powershell
python training/prepare_corpus_v2.py
python training/train_category.py
python training/train_urgency.py
python training/evaluate.py
```

Review `data/processed/corpus_v2_review.csv` before retraining if the source data changes.

## Important limitation

Falcon Mail is an academic prototype. Predictions support administrators; they should not replace human review. Safety keywords intentionally take priority over the statistical urgency model, and uncertain tickets can be corrected by an administrator so future corpus versions can incorporate those decisions.
