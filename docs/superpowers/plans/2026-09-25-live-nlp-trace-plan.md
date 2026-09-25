# Falcon Mail Live NLP Trace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record every real NLP stage in Firestore, retain tickets when analysis fails, and expose repository operations required by the live admin inbox.

**Architecture:** A repository-backed tracer records stage state while `process_complaint()` executes the existing NLP functions. A minimal complaint record is created before analysis, finalized after success, and marked `Needs Review` after a recoverable NLP failure. Firestore remains authoritative; SQLite receives compatible support for explicit offline use.

**Tech Stack:** Python 3.14, Streamlit, Firebase Admin SDK, Cloud Firestore, SQLite, scikit-learn, spaCy, Sentence Transformers

**Spec:** `docs/superpowers/specs/2026-09-25-minimal-ui-live-nlp-corpus-design.md`

## Global Constraints

- The product name in user-facing copy is `Falcon Mail`.
- Keep `SENTINEL_STORAGE_BACKEND` and `database/sentinel.db` as compatibility aliases; do not migrate or discard existing data.
- Do not add automated tests, a test framework, CI configuration, mocks, or test-only infrastructure.
- Leave the existing `tests/` directory unchanged.
- Do not store dense embeddings, credentials, tokens, stack traces, or duplicate complaint text in processing traces.
- Students may read only their own simplified run state; detailed traces are administrator-only.
- A recoverable NLP failure must retain the ticket as `Needs Review`.

## Review Focus

- Empty complaint text must be rejected before a ticket is created.
- A model-loading failure after intake must retain one ticket and mark one run `needs_review`.
- A retry must reuse the ticket ID and must not create a second complaint.
- A student must not retrieve another student's run or detailed stage evidence.
- Failure to write optional trace detail must not erase an otherwise valid complaint result.

---

### Task 1: Shared identifiers and processing-run contract

**Files:**
- Create: `database/identifiers.py`
- Modify: `database/base_repository.py`

**Interfaces:**
- Produces: `generate_complaint_id() -> str`, `generate_processing_run_id() -> str`
- Produces repository methods listed below for both storage implementations.

- [ ] **Step 1: Add shared ID generation**

```python
import uuid

def generate_complaint_id() -> str:
    return f"CMP-{uuid.uuid4().hex[:8].upper()}"

def generate_processing_run_id() -> str:
    return f"RUN-{uuid.uuid4().hex[:10].upper()}"
```

- [ ] **Step 2: Extend `BaseComplaintRepository` with exact trace operations**

```python
def create_processing_run(self, run: Dict[str, Any], actor: AuthenticatedUser) -> str: ...
def update_processing_stage(self, run_id: str, stage: str, data: Dict[str, Any], actor: AuthenticatedUser) -> None: ...
def finish_processing_run(self, run_id: str, status: str, data: Dict[str, Any], actor: AuthenticatedUser) -> None: ...
def get_processing_run(self, run_id: str, actor: AuthenticatedUser) -> Optional[Dict[str, Any]]: ...
def list_processing_runs(self, actor: AuthenticatedUser, limit: int = 100) -> List[Dict[str, Any]]: ...
def finalize_complaint_analysis(self, complaint_id: str, data: Dict[str, Any], actor: AuthenticatedUser) -> None: ...
def mark_complaint_needs_review(self, complaint_id: str, safe_error: str, diagnostic_code: str, actor: AuthenticatedUser) -> None: ...
def override_complaint_prediction(self, complaint_id: str, field: str, new_value: Any, reason: str, actor: AuthenticatedUser) -> None: ...
```

- [ ] **Step 3: Replace repository-local UUID generation with `generate_complaint_id()`**

- [ ] **Step 4: Manually inspect both repositories and confirm the shared ID format remains `CMP-XXXXXXXX`**

- [ ] **Step 5: Commit**

```powershell
git add database/identifiers.py database/base_repository.py database/firestore_repository.py database/sqlite_repository.py
git commit -m "refactor: centralize Falcon Mail ticket identifiers"
```

### Task 2: Firestore processing-run persistence and authorization

**Files:**
- Modify: `database/firestore_repository.py`
- Modify: `firestore.rules`

**Interfaces:**
- Consumes: Task 1 repository contract.
- Produces: Firestore documents under `processing_runs/{run_id}` and finalization methods for `complaints/{complaint_id}`.

- [ ] **Step 1: Implement `create_processing_run()`**

Validate that `actor.uid == reporter_uid` unless `actor.is_admin`, initialize `overall_status="processing"`, `current_stage="received"`, `stages={}`, `retry_count=0`, and server timestamps.

- [ ] **Step 2: Implement stage updates using dotted Firestore fields**

```python
updates = {
    "current_stage": stage,
    "updated_at": SERVER_TIMESTAMP,
    f"stages.{stage}": data,
}
self.db.collection("processing_runs").document(run_id).update(updates)
```

Before updating, load the run and permit only its reporter or an administrator.

- [ ] **Step 3: Implement run retrieval**

`get_processing_run()` returns full stages to admins and removes `evidence`, `safe_error`, and `diagnostic_code` from the student response. `list_processing_runs()` rejects non-admin actors and returns newest-first records.

- [ ] **Step 4: Implement complaint finalization**

Allow `create_complaint()` to preserve explicit nullable analysis fields and caller-provided `Processing` status. `finalize_complaint_analysis()` updates analysis fields, sets `status="Open"`, `processing_status="completed"`, `needs_manual_review=False`, and `updated_at`. `mark_complaint_needs_review()` sets `status="Needs Review"`, null category/urgency confidence values, `processing_status="needs_review"`, and the safe diagnostic fields. `override_complaint_prediction()` permits only category, urgency, location, and department; requires an administrator and non-empty reason; and appends an immutable override entry.

- [ ] **Step 5: Add defense-in-depth Firestore rules**

```text
match /processing_runs/{runId} {
  allow read: if isAdmin();
  allow create, update, delete: if false;
}
```

The server uses Admin SDK and still performs repository authorization. Student progress is returned only through the Streamlit server after `get_processing_run()` removes administrator evidence and diagnostics.

- [ ] **Step 6: Start the app, submit one ticket, and inspect Firestore to confirm the run owner and timestamps**

- [ ] **Step 7: Commit**

```powershell
git add database/firestore_repository.py firestore.rules
git commit -m "feat: persist authorized NLP processing runs"
```

### Task 3: SQLite compatibility

**Files:**
- Modify: `database/sqlite_repository.py`

**Interfaces:**
- Consumes: Task 1 repository contract.
- Produces: the same run dictionaries as Firestore for explicit offline mode.

- [ ] **Step 1: Add a `processing_runs` table**

Use columns `run_id`, `ticket_id`, `reporter_uid`, `reporter_name`, `title`, `submitted_location`, `overall_status`, `current_stage`, `stages_json`, `retry_count`, `safe_error`, `diagnostic_code`, `created_at`, `updated_at`, and `completed_at`.

- [ ] **Step 2: Add complaint columns safely**

Use `PRAGMA table_info(complaints)` before individual `ALTER TABLE` statements for `processing_run_id`, `processing_status`, `needs_manual_review`, `model_versions_json`, `prediction_overrides_json`, `safe_error`, and `diagnostic_code`.

- [ ] **Step 3: Implement all Task 1 methods with the same authorization rules**

Serialize stages as JSON and deserialize them in returned dictionaries. Admin-only listing sorts `updated_at DESC` and applies `limit`.

- [ ] **Step 4: Run Falcon Mail with `$env:SENTINEL_STORAGE_BACKEND='sqlite'` and manually inspect one processing row**

- [ ] **Step 5: Commit**

```powershell
git add database/sqlite_repository.py
git commit -m "feat: support NLP traces in offline storage"
```

### Task 4: Trace implementation and pipeline instrumentation

**Files:**
- Create: `nlp/tracing.py`
- Modify: `nlp/pipeline.py`
- Modify: `nlp/urgency.py`
- Modify: `models/training_metadata.json` only when model metadata needs a stable version field

**Interfaces:**
- Produces: `NullPipelineTracer`, `RepositoryPipelineTracer`, and `retry_complaint_processing()`.
- Preserves: existing `process_complaint()` callers and return keys.

- [ ] **Step 1: Implement tracer classes**

`RepositoryPipelineTracer` records `started_at`, `completed_at`, `duration_ms`, status, result, confidence, `model_or_rule`, evidence, and sanitized error. Use `time.perf_counter()` for duration and UTC ISO timestamps for SQLite-compatible payloads.

- [ ] **Step 2: Extend `process_complaint()` without breaking existing callers**

```python
def process_complaint(
    text: str,
    actor: Optional[AuthenticatedUser] = None,
    repo: Optional[BaseComplaintRepository] = None,
    store_in_db: bool = True,
    duplicate_threshold: float = DEFAULT_DUPLICATE_THRESHOLD,
    user_location: Optional[str] = None,
    user_category: Optional[str] = None,
    complaint_id: Optional[str] = None,
    processing_run_id: Optional[str] = None,
) -> Dict[str, Any]:
```

- [ ] **Step 3: Persist intake before model work**

For stored authenticated submissions, generate IDs, create a minimal complaint with `status="Processing"`, then create the processing run. Do not create a second complaint during persistence.

- [ ] **Step 4: Separate urgency prediction from safety elevation**

Expose `predict_ml_urgency(text: str) -> dict` and `apply_safety_rules(text: str, ml_result: dict) -> dict` in `nlp/urgency.py`. Keep `predict_urgency(text)` as a compatibility wrapper that calls both. The pipeline traces `urgency` around the first call and `safety_rules` around the second call.

- [ ] **Step 5: Wrap each approved NLP stage with start/complete/fail trace calls**

Use the exact stage names from the specification. Store only short scalar/dictionary results; omit `dense_embedding` and matched complaint text.

- [ ] **Step 6: Finalize successful analysis**

Call `finalize_complaint_analysis()`, finish the run as `completed`, retain the existing return payload, and attach `processing_run_id` plus `processing_status="completed"`.

- [ ] **Step 7: Retain recoverable failures**

After intake exists, catch NLP exceptions, convert them to a stable diagnostic code such as `MODEL_LOAD_FAILED`, mark the complaint and run `needs_review`, and return a payload containing the original ticket ID and safe message. Continue raising validation errors that occur before intake.

- [ ] **Step 8: Implement administrator retry**

```python
def retry_complaint_processing(
    complaint_id: str,
    actor: AuthenticatedUser,
    repo: BaseComplaintRepository,
) -> Dict[str, Any]:
```

Require `actor.is_admin`, reload the original description/location/category context, increment the existing run's retry count, and finalize the same complaint ID. Before resetting stages, append the prior stages, status, error, and timestamps to `attempt_history`.

- [ ] **Step 9: Manually run four submissions**

Run a normal ticket, a fire ticket, a duplicate, and a ticket with a temporarily unavailable model. Confirm stage order, no embedding in the trace, and one retained `Needs Review` ticket for the failure.

- [ ] **Step 10: Commit**

```powershell
git add nlp/tracing.py nlp/pipeline.py nlp/urgency.py models/training_metadata.json
git commit -m "feat: trace real NLP stages and retain failed tickets"
```

### Task 5: Backend handoff documentation

**Files:**
- Modify: `README.md`

**Interfaces:**
- Documents the persisted schema consumed by the UI plan.

- [ ] **Step 1: Document run states, stage names, failure retention, retry behavior, and Firestore collection**

- [ ] **Step 2: Document that internal legacy storage names remain compatibility details while the product is Falcon Mail**

- [ ] **Step 3: Follow the manual four-case verification once more after restarting Streamlit**

- [ ] **Step 4: Commit**

```powershell
git add README.md
git commit -m "docs: explain Falcon Mail processing traces"
```
