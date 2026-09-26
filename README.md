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

## Models and corpus

The pipeline runs locally; it does not send complaint text to a hosted language-model API.

| Component | Implementation |
| --- | --- |
| Category | Word and character TF-IDF `FeatureUnion` with Logistic Regression |
| Urgency | TF-IDF with Logistic Regression |
| Safety elevation | Deterministic keyword rules |
| Extraction | `en_core_web_sm` plus campus regex patterns |
| Duplicate detection | `all-MiniLM-L6-v2` embeddings plus category/location signals |
| Summary | Deterministic operational template |

The main labeled corpus is [`data/complaints.csv`](data/complaints.csv). Duplicate evaluation pairs are in [`data/duplicate_eval_pairs.csv`](data/duplicate_eval_pairs.csv), and manually written holdout examples are in [`data/unseen_test_cases.csv`](data/unseen_test_cases.csv). Training provenance, dataset hashes, versions, split sizes, and evaluation metrics are recorded in [`models/training_metadata.json`](models/training_metadata.json).

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
4. Provision administrators from the server:

```powershell
python scripts/set_admin_role.py --email admin@manipal.edu
```

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

## Manual verification walkthrough

Restart Streamlit before the walkthrough so model and repository singletons begin cleanly.

1. Register or sign in as a student.
2. Submit an ordinary ticket such as: `The Wi-Fi in the library keeps disconnecting since this morning.`
3. Submit a safety ticket such as: `There is smoke and fire coming from the electrical room in Block B.` Confirm the final urgency is `Critical` and the decision source is the safety rule.
4. Submit the ordinary ticket again. Confirm it receives a privacy-safe repeated-incident notice.
5. Temporarily make one model unavailable, submit another ticket, and confirm the ticket remains visible as `Needs Review` with no invented category or urgency.
6. Sign in as an administrator and inspect each processing run. Confirm the stage order matches this README, timings are real, and no dense embedding or matched complaint text appears in the trace.
7. Retry the failed ticket. Confirm the same ticket and run IDs are reused, `retry_count` increases, and the previous attempt appears in `attempt_history`.
8. Correct one prediction and confirm the old value, new value, administrator, reason, and timestamp are preserved.
9. Assign and resolve a ticket with a resolution note, then confirm the student timeline updates.

Falcon Mail intentionally relies on this manual application walkthrough rather than adding automated test infrastructure.

## Authors

Falcon Mail project team — Manipal Academy of Higher Education, Dubai Campus.
