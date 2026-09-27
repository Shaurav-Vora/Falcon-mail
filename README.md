# Falcon Mail

Falcon Mail is a student-friendly online ticketing system for campus complaints. A student submits one ticket through the web application; the local NLP pipeline categorizes it, estimates urgency, applies safety rules, extracts useful details, checks for repeated incidents, summarizes it, and routes it to the responsible department.

Administrators can inspect the genuine stored pipeline trace. Progress is not simulated.

## What the pipeline does

Every submitted ticket moves through these stages in order:

| Stage | Purpose |
| --- | --- |
| `received` | Validate the request and retain the initial ticket. |
| `preprocessing` | Normalize and lemmatize text with spaCy. |
| `category` | Predict one of the Falcon Mail complaint categories. |
| `urgency` | Produce the statistical ML urgency prediction. |
| `safety_rules` | Elevate fire, smoke, injury, and other safety incidents deterministically. |
| `extraction` | Resolve location, room, building, dates, times, and supported entities. |
| `duplicates` | Create a MiniLM embedding and compare eligible active tickets. |
| `summary` | Generate a short operational summary. |
| `routing` | Map the category to the responsible department. |
| `persistence` | Save the final analysis and ticket state. |

A stage can be `pending`, `running`, `completed`, `failed`, or `skipped`. Stored stage records include start and completion timestamps, duration, concise result, confidence when available, model or rule source, and administrator-only evidence.

## Current models and corpus

The pipeline runs locally; it does not send complaint text to a hosted language-model API.

| Component | Implementation |
| --- | --- |
| Category | Word and character TF-IDF `FeatureUnion` with Logistic Regression |
| Urgency | TF-IDF with Logistic Regression |
| Safety elevation | Deterministic keyword rules |
| Extraction | `en_core_web_sm` plus campus regex patterns |
| Duplicate detection | `all-MiniLM-L6-v2` embeddings plus category/location signals |
| Summary | Deterministic operational template |

The currently published training corpus is [`data/complaints.csv`](data/complaints.csv): 585 synthetic, labeled campus complaints arranged into 255 template groups. The model metadata records a group-aware 467/118 train/test split and reports no template-group leakage. Duplicate evaluation uses 60 labeled pairs in [`data/duplicate_eval_pairs.csv`](data/duplicate_eval_pairs.csv); [`data/unseen_test_cases.csv`](data/unseen_test_cases.csv) contains 26 manually written holdout examples.

Training provenance, dataset hashes, versions, split sizes, and recorded evaluation metrics are in [`models/training_metadata.json`](models/training_metadata.json). The administrator Models page reads this file directly and says when an expected measurement is absent.

### Recorded model results

These are the values currently stored in `models/training_metadata.json`; they were not re-measured during the interface work.

| Model | Accuracy | Macro F1 | Weighted F1 | Safety-class recall |
| --- | ---: | ---: | ---: | --- |
| Category `category-2026-09-12-v1` | 31.36% | 32.54% | 31.63% | Not applicable |
| Urgency `urgency-2026-09-12-v1` | 41.53% | 36.79% | 41.15% | Critical 21.43%; High 30.00% |

The configured MiniLM duplicate threshold is `0.60`. The project configuration records F1 `0.9123`, zero false positives, and recall `83.9%` on the 60 labeled duplicate pairs. Those figures describe that small curated set only.

### Important limitations

- The current 585-record corpus is synthetic. Performance on naturally written student tickets has not been measured separately.
- Current metadata does not contain per-class category/urgency tables, confusion matrices, or separate synthetic/external scores. The Models page labels these gaps instead of estimating them.
- Category and urgency scores are modest. Predictions should assist routing, not replace administrator review.
- Deterministic safety rules can elevate known emergency phrases after ML urgency prediction, but keyword coverage is not a guarantee that every emergency will be detected.
- MiniLM similarity is evidence for possible duplication, not proof that two reports describe the same incident.

### Corpus v2 status

The approved Corpus v2 design adds the reviewed `alaminxpro/university-students-complaints` dataset (332 publisher-described records, CC BY 4.0) while preserving source labels, attribution, review decisions, group-safe splits, and separate source metrics. Its preparation scripts and generated `data/processed/corpus_v2.csv` and `data/metadata/corpus_v2_summary.json` are not present in this branch yet. Until they are generated, the administrator Corpus page deliberately shows a preparation notice.

After the separate Corpus v2 implementation lands, its workflow is:

```powershell
python training/fetch_external_corpus.py
python training/prepare_corpus_v2.py --build-review-queue
# Review every pending external row; approve or exclude it explicitly.
python training/prepare_corpus_v2.py --finalize
```

Do not silently map uncertain external labels. Gender, semester, and student department must remain excluded from model features.

## Processing-run storage

Firestore is the shared production source of truth. Each submission creates:

```text
complaints/{ticket_id}
processing_runs/{run_id}
```

The processing-run document has this shape:

```text
run_id
ticket_id
reporter_uid
reporter_name
title
submitted_location
overall_status        processing | completed | failed | needs_review
current_stage
stages                map keyed by the ten stage names
retry_count
attempt_history
safe_error
diagnostic_code
created_at
updated_at
completed_at
```

Each value in `stages` can contain:

```text
status
started_at
completed_at
duration_ms
result
confidence
model_or_rule
evidence
safe_error
diagnostic_code
```

Dense MiniLM vectors, authentication data, stack traces, raw matched-ticket text, and unnecessary copies of the submitted complaint are deliberately excluded from processing traces. The dense vector remains only on the complaint record where duplicate detection needs it.

SQLite implements the same repository contract for explicit offline development. It stores runs in the `processing_runs` table and serializes stages and attempt history as JSON.

## Access boundaries

- Administrators can list complete processing runs, inspect stage evidence and diagnostics, retry failed processing, and correct category, urgency, location, or department with an immutable audit entry.
- Students can see only their own ticket and sanitized progress returned by the Streamlit server.
- Student trace responses remove `evidence`, `safe_error`, and `diagnostic_code`.
- Duplicate responses shown to students do not contain another ticket's ID or complaint text.
- Direct client writes to `processing_runs` are denied by [`firestore.rules`](firestore.rules). The Firebase Admin SDK performs authorized server-side writes.

Every privileged repository method receives an `AuthenticatedUser` and checks ownership or administrator status server-side.

## Failure retention and retry

Falcon Mail creates the minimal complaint record before model execution. If a model, dependency, trace stage, or eligible database operation fails afterward:

1. The original ticket ID and description are retained.
2. The ticket becomes `Needs Review`.
3. Category and urgency remain empty instead of receiving invented fallback predictions.
4. The student receives a neutral confirmation that an administrator will review the ticket.
5. Administrators see the failed stage and a stable diagnostic code.

An administrator retry reuses the same ticket ID and processing-run ID. The previous stages, status, diagnostics, and timestamps are appended to `attempt_history`; `retry_count` is incremented; and the real pipeline starts again. A successful retry returns the existing ticket to `Open` with completed analysis.

## Project structure

```text
data/                       labeled corpus and evaluation records
database/
  base_repository.py        shared persistence contract
  firestore_repository.py   production Firestore implementation
  sqlite_repository.py      explicit offline implementation
models/                     trained classifiers and training metadata
nlp/
  pipeline.py               orchestration, retention, and retry
  tracing.py                real stage timing and privacy filtering
  classification.py         category inference
  urgency.py                ML urgency and separate safety elevation
  entity_extraction.py      entity and campus-location extraction
  duplicate_detection.py    MiniLM embeddings and duplicate scoring
  summarization.py          operational summary generation
pages/                      Streamlit student and administrator screens
app.py                      application entry point
firestore.rules             defense-in-depth client rules
```

## Setup

Use a short local path such as `C:\dev\Falcon-mail` on Windows. Python 3.12 is the conservative choice for the NLP dependency stack.

```powershell
uv python install 3.12
uv venv --python 3.12 .venv
.venv\Scripts\Activate.ps1
uv pip install --link-mode copy -r requirements.txt
uv pip install --link-mode copy "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl"
```

`--link-mode copy` avoids Windows cloud-folder and hardlink error 396.

### Firebase configuration

1. Put the Firebase Admin service-account JSON at `serviceAccountKey.json` in the project root.
2. Create `.streamlit/secrets.toml` from `.streamlit/secrets.toml.example` and enter the Firebase web-app values shown in the Firebase console.
3. Keep both files private; they are excluded by `.gitignore`.
4. Register the intended administrator once through the normal registration screen.
5. Provision that existing account from a trusted server terminal:

```powershell
python scripts/set_admin_role.py --email admin@manipal.edu
```

You can alternatively target an exact Firebase UID:

```powershell
python scripts/set_admin_role.py --uid FIREBASE_USER_UID
```

6. Sign out and sign in again so Firebase issues a token containing the new custom claim.

Never place passwords or private keys in documentation or source control.

### Start Falcon Mail

Production Firestore mode is the default:

```powershell
streamlit run app.py
```

Explicit local SQLite mode:

```powershell
$env:SENTINEL_STORAGE_BACKEND = "sqlite"
streamlit run app.py
```

`SENTINEL_STORAGE_BACKEND` and the historical `sentinel.db` filename remain internal compatibility names so existing environments continue to work. The product name, interface, and documentation are **Falcon Mail**.

### Rebuild the current models

Model training is explicit; starting the web application never retrains models automatically.

```powershell
python training/train_category.py
python training/train_urgency.py
python training/evaluate.py
```

Run these commands only after confirming which corpus path the trainers use. In this branch they train from `data/complaints.csv`; the separate Corpus v2 work must first update them to consume the reviewed split column. Commit the two `.pkl` files and `models/training_metadata.json` together so the artifacts and their evidence cannot drift apart.

## Manual verification walkthrough

Restart Streamlit before the walkthrough so model and repository singletons begin cleanly. Use non-production test accounts and tickets. Do not intentionally break a shared production model file; reproduce the failure-retention step only in an isolated local copy.

1. Register and sign in as a student. Confirm the account cannot choose an administrator role.
2. Enter an ordinary issue such as `The Wi-Fi in the library keeps disconnecting since this morning.` Select **Review ticket**, confirm the text and location, then send it.
3. Submit `There is smoke and fire coming from the electrical room in Block B.` Confirm the result is `Critical` and the administrator trace names the safety rule.
4. Submit a substantially identical version of the ordinary ticket. Confirm the student sees only a privacy-safe repeated-incident notice.
5. Sign in as an administrator. Select **Refresh tickets** after a submission or update, confirm the selected ticket remains stable, and inspect its stored stages in the documented order.
6. Inspect completed stages. Confirm outputs, confidence where available, duration, model/rule and concise evidence are present, while dense embeddings and matched complaint text are absent.
7. Correct one predicted field with a reason. Confirm the ticket changes and the override audit data retains old value, new value, administrator, reason and timestamp.
8. Assign the ticket to yourself, move it to **In progress**, then resolve it with a note. Sign back in as the student and confirm the status timeline and note update.
9. In an isolated local copy, make a model unavailable and submit a ticket. Confirm the ticket remains as **Needs review**, then retry it and confirm the same ticket/run IDs and preserved attempt history.
10. While signed in as a student, attempt to open administrator Corpus, Models and processing-run data. Confirm access is denied and detailed evidence is not returned.
11. As an administrator, inspect Corpus and Models. Confirm source, license and citation information when Corpus v2 artifacts exist; otherwise confirm the exact preparation command appears. Compare displayed metrics with `models/training_metadata.json`.
12. Resize the browser to approximately 430 pixels wide. Confirm the student form remains usable and the administrator inbox/detail layout stacks without hiding actions.

### Verification record for this implementation

The interface pass used the configured application where available and isolated native Streamlit previews for states that should not be induced in shared Firebase data.

| Checklist area | Observed result |
| --- | --- |
| Student authentication and real submissions | The configured application reached login successfully; the student submission/history screens and ordinary and safety-ticket results were exercised during project setup. |
| Review, duplicate notice and safety elevation | The review step did not execute NLP early; duplicate messaging remained privacy-safe; smoke/fire was elevated to `Critical`. |
| Live administrator trace | The explicit refresh action retained the selected ticket. Completed, running, pending, skipped and failed states displayed stored evidence without simulated progress or periodic full-inbox repainting. |
| Correction, assignment and failure retry | Correction controls required a reason; assignment succeeded; failed processing remained visible and retried into the same selected ticket. |
| Authorization | Student previews received `Access Denied` for administrator evidence pages. |
| Corpus and Models | Prepared fixtures displayed distributions, CC BY 4.0 provenance, per-class tables and matrices. Missing/malformed artifacts produced commands rather than exceptions. Current legacy metadata displayed only recorded values and named its missing evidence. |
| Responsive layout | Student and administrator flows were reviewed at desktop width and approximately 430 pixels. |

The final resolution-to-student timeline should be repeated against the actual Firebase project because notifications and shared persistence depend on that external configuration. Falcon Mail intentionally relies on this manual walkthrough rather than adding automated test infrastructure.

## Authors

Falcon Mail project team — Manipal Academy of Higher Education, Dubai Campus.
