# SENTINEL Minimal UI, Live NLP Trace, and Corpus Design

**Date:** 2026-09-25
**Status:** Approved design awaiting implementation planning

## 1. Purpose

SENTINEL is an online campus ticketing system. A student raises a ticket through a web form, the NLP pipeline classifies and prioritizes it, extracts operational details, checks for repeated incidents, and routes it to the responsible department. Administrators manage the resulting ticket queue.

This design simplifies the student interface, adds an administrator-only live view of genuine NLP processing, and replaces the current undocumented synthetic-only corpus workflow with a traceable corpus that combines reviewed external campus complaints and existing SENTINEL examples.

The project remains a Streamlit application backed by Firebase Authentication and Cloud Firestore. It will not add email, WhatsApp, chat, or other ingestion channels.

## 2. Goals

- Make raising and tracking a ticket straightforward for students.
- Give administrators a live inbox where each incoming ticket progresses through the actual NLP stages.
- Preserve the existing administrator assignment, status, resolution, notification, and analytics functions.
- Retain a submitted ticket even when an NLP component fails.
- Expose corpus composition, provenance, model versions, evaluation results, and known limitations to administrators.
- Improve the training corpus using a reviewed external university-complaints dataset without obscuring which records are synthetic.
- Keep the implementation within the existing Streamlit, Python, Firebase, scikit-learn, spaCy, and Sentence Transformers stack.

## 3. Non-goals

- Email, WhatsApp, social-media, or messaging-platform ingestion.
- A React, Vue, or other separate frontend.
- A FastAPI service, worker queue, message broker, or microservice deployment.
- Automatic continuous retraining.
- Exposing embeddings, secrets, stack traces, or unrestricted complaint data in the UI.
- Adding a new automated test suite, UI test framework, CI pipeline, mocks, or test-only infrastructure.
- Deleting the existing `tests/` directory. Existing tests remain untouched and are not expanded by this work.

## 4. Users and permissions

### Student

A student can:

- Raise a ticket.
- Review the description and location they entered before final submission.
- See detected category, urgency, location, and destination department after the ticket is sent and processed.
- See a simple processing state and final ticket number.
- View only their own submitted tickets, notifications, status history, and resolution notes.
- Receive a privacy-safe duplicate notice without learning another student's identity or complaint text.

A student cannot:

- Access detailed NLP traces, model evidence, corpus records, campus-wide analytics, or other students' tickets.
- Assign, reroute, override, resolve, or reject a ticket.

### Administrator

An administrator can:

- View a live inbox of processing, completed, failed, and unresolved tickets.
- Inspect each NLP stage, its result, confidence, duration, model or rule source, and concise evidence.
- Retry failed processing.
- Correct category, urgency, location, and routing results while preserving an audit record.
- Use the existing assignment, status, resolution, notification, analytics, and archive features.
- Inspect corpus composition, data provenance, model metadata, evaluation results, and known limitations.

Administrator access continues to use the Firebase custom claim set by `scripts/set_admin_role.py` and server-side repository authorization.

## 5. Chosen architecture

The approved approach is in-place Streamlit and Firestore observability.

The existing NLP functions remain the source of predictions. The master pipeline gains an optional trace interface that records stage transitions. A no-operation trace implementation preserves ordinary programmatic use, while a Firestore trace implementation publishes live operational state.

The flow is:

```text
Student submits ticket
        |
Generate ticket ID and processing-run ID
        |
Create Firestore processing record
        |
Run each existing NLP stage
        |
Record genuine stage start, completion, output, and duration
        |
Persist final complaint and routing result
        |
Mark processing run completed
        |
Admin inbox and student confirmation update
```

The admin UI polls Firestore through a Streamlit fragment at approximately one- to two-second intervals. It displays stored state; it does not simulate progress.

## 6. NLP stages

The observable stages are:

1. `received` — validate and accept the submitted fields.
2. `preprocessing` — normalize the complaint text.
3. `category` — predict the complaint category and confidence.
4. `urgency` — predict ML urgency and confidence.
5. `safety_rules` — evaluate deterministic critical-incident rules and determine final urgency.
6. `extraction` — resolve location, building, room, dates, times, and other supported entities.
7. `duplicates` — create a MiniLM embedding and compare it with eligible active complaints.
8. `summary` — create the structured operational summary.
9. `routing` — map the final category to a responsible department.
10. `persistence` — save the complaint and notification state.

Each stage may be `pending`, `running`, `completed`, `failed`, or `skipped`.

The trace records concise operational results. It must not store the dense MiniLM vector, Firebase credentials, authentication tokens, Python stack traces, or an unnecessary copy of the complaint text.

## 7. Trace interface

The pipeline receives an optional tracer with these responsibilities:

```python
start_stage(stage_name, metadata=None)
complete_stage(stage_name, result=None, confidence=None, evidence=None)
fail_stage(stage_name, safe_error, diagnostic_code=None)
complete_run(final_result)
fail_run(safe_error, diagnostic_code=None)
```

The tracer owns timing so NLP components do not duplicate duration logic. Trace failures must not hide the original NLP result; a trace-write failure is logged and processing continues when safe.

Evidence is intentionally short. Examples include:

- Category: highest predicted label and confidence.
- Urgency: ML prediction and whether a safety rule changed it.
- Safety: matched safe rule name, not an internal stack trace.
- Extraction: resolved location and whether it came from the form or complaint text.
- Duplicate: highest similarity, threshold, and privacy-safe match identifier for admins.
- Routing: final department and rule used.

## 8. Firestore data model

### Processing run

```text
processing_runs/{run_id}
    run_id
    ticket_id
    reporter_uid
    reporter_name
    title
    submitted_location
    overall_status          processing | completed | failed | needs_review
    current_stage
    created_at
    updated_at
    completed_at
    retry_count
    diagnostic_code
    safe_error
    stages:
        <stage_name>:
            status
            started_at
            completed_at
            duration_ms
            result
            confidence
            model_or_rule
            evidence
            safe_error
```

The title and limited submitter metadata support the live inbox. The authoritative full ticket text remains in the complaint record rather than being duplicated in every stage.

### Complaint additions

The existing complaint record gains only the fields required to connect it to processing and manual review:

```text
processing_run_id
processing_status
needs_manual_review
model_versions
prediction_overrides
```

Each prediction override records the previous value, new value, administrator UID, administrator name, timestamp, and optional reason.

## 9. Failure behaviour

A submitted ticket must not disappear because a model, model download, database query, or trace stage fails.

On a recoverable NLP failure:

- Retain the submitted title, description, location, reporter, and ticket ID.
- Mark the run `needs_review` and the failed stage `failed`.
- Create or retain a complaint record visible in the admin inbox.
- Do not invent a category or urgency prediction.
- Show the student a neutral message explaining that the ticket was received and will be reviewed manually.
- Show administrators the failed stage, a sanitized explanation, and a retry action.

On retry, retain the previous attempt metadata, increment `retry_count`, and update the same ticket rather than creating a duplicate complaint.

## 10. Student interface

The student application uses a compact top navigation instead of a visually dominant sidebar where Streamlit permits it. Primary destinations are `Raise a ticket`, `My tickets`, and `Notifications`.

### Raise a ticket

The page contains one narrow reading column and no promotional hero. It asks:

- What happened?
- Where did it happen?
- Optional category context.

The primary action is `Review ticket`. The review state confirms the student's own description and location; it does not run or preview the NLP pipeline. The final action is `Send ticket`. Sending creates the processing run and starts the genuine pipeline exactly once. When processing completes, the result state shows category, urgency, resolved location, and department in plain language.

Emergency output is direct and calm. Decorative AI marketing copy, duplicate help panels, and repeated instructional cards are removed.

### Confirmation and tracking

After submission the student sees:

- Ticket number.
- Received time.
- Destination department when available.
- Simple state: `Processing`, `Received`, `In progress`, `Resolved`, or `Needs staff review`.
- A link to `My tickets`.

Students do not see confidence scores, model names, trace timings, embeddings, other complaint IDs, or admin diagnostics.

## 11. Administrator interface

The administrator shell uses three functional regions on desktop:

```text
Navigation | Live ticket inbox | Selected ticket and NLP trace
```

On narrower screens the detail region opens below the inbox or as a full-width view.

### Live ticket inbox

Each row shows:

- Ticket title and ID.
- Submitted location.
- Overall status.
- Current NLP stage.
- Elapsed processing time.
- Final urgency when known.

Critical incidents are placed first after the safety stage establishes critical urgency. Running and failed tickets remain visible instead of disappearing from the queue.

### Pipeline inspector

Selecting a row opens the real trace. Completed stages show output, confidence, duration, source model or rule, and concise evidence. The current stage is visibly active. Pending stages are quiet. Failed stages show the safe error and retry control.

After processing, the panel exposes correction, assignment, status, and resolution controls. The existing requirement for resolution notes remains.

### Corpus and model pages

The admin navigation gains `Corpus` and `Models` views.

`Corpus` shows:

- Total records.
- Synthetic and external counts.
- Category and urgency distributions.
- Complaint length and duplicate-group summaries.
- Source, license, citation, and review status.
- A privacy-safe sample browser.

`Models` shows:

- Current category and urgency model versions.
- Training date and corpus version.
- Per-class precision, recall, and F1 when available.
- Confusion matrices generated during model evaluation.
- MiniLM model and configured duplicate threshold.
- Known limitations, including separate synthetic and external performance.

## 12. Visual design system

The interface uses restraint rather than a rounded-card dashboard kit.

### Palette

- Canvas: `#F6F8FB`
- Surface: `#FFFFFF`
- Primary ink: `#17233C`
- Secondary text: `#64748B`
- Manipal orange: `#F15A24`
- Success: `#138A5B`
- Critical: `#C9362B`

Orange is reserved for primary actions and active navigation. Red is reserved for genuine critical or failed states. Charts use accessible extensions of the palette without assigning arbitrary colors to every category.

### Typography and structure

Instrument Sans is the preferred interface typeface with system sans-serif fallbacks. The layout uses left alignment, readable line lengths, whitespace, and thin dividers. It removes gradients, promotional banners, excessive uppercase labels, repeated shadows, and decorative icons that do not encode state.

The live pipeline rail is the single expressive visual device. Motion occurs only when processing changes state and respects reduced-motion preferences.

## 13. Corpus v2

### Sources

Corpus v2 combines:

1. The current 585-record SENTINEL corpus, retained and marked synthetic.
2. The external `alaminxpro/university-students-complaints` dataset from Hugging Face, described by its publisher as 332 university complaints and released under CC BY 4.0.
3. Manually reviewed additions only when required to cover missing or weak SENTINEL categories.

The external dataset is a domain anchor, not unquestioned ground truth. Its category, severity, department, and aspect labels require review before training.

### Storage

```text
data/
    raw/
        sentinel_v1/
        university_students_complaints/
    processed/
        corpus_v2.csv
    metadata/
        DATA_SOURCES.md
        corpus_v2_summary.json
        label_mapping.json
```

Raw source files remain unchanged. Transformations write new processed artifacts.

### Normalized fields

```text
record_id
text
category
urgency
department
location
incident_group_id
template_group_id
source_dataset
source_record_id
source_type             synthetic | external
original_category
original_urgency
reviewed_category
reviewed_urgency
review_status
split                   train | validation | test
```

Gender, semester, and student department are excluded from model features because they are unnecessary for ticket classification and could introduce unwanted bias.

### Review and splitting

- Map the external five-category taxonomy into SENTINEL's eleven categories using a documented mapping.
- Review urgency against SENTINEL's written urgency rubric; do not map `Urgent` mechanically to `Critical`.
- Preserve the source `Complaint_Group_ID` as `incident_group_id`.
- Keep every record in the same incident or template group within one data split.
- Preserve source and original labels for reproducibility.
- Report synthetic and external evaluation separately.

The external dataset must be attributed in `DATA_SOURCES.md` and in the project documentation.

## 14. Manual verification

No new automated testing infrastructure is part of this work. Verification is performed by running the application and completing this checklist:

1. Register and sign in as a student.
2. Submit an ordinary campus ticket and confirm the review screen.
3. Submit a fire or smoke ticket and confirm the safety rule produces critical urgency.
4. Submit a substantially identical ticket and confirm MiniLM duplicate handling.
5. Sign in as an administrator and observe a new ticket moving through genuine pipeline stages.
6. Inspect outputs, confidence, evidence, timings, and routing in the pipeline inspector.
7. Correct a prediction and confirm the override is recorded.
8. Assign the ticket, move it to `In progress`, resolve it with a note, and verify the student timeline.
9. Force a safe processing failure, confirm the ticket remains available as `Needs review`, and retry it.
10. Confirm a student cannot access admin pages or detailed processing records.
11. Inspect the Corpus and Models pages and verify provenance and license information.
12. Resize the app to a narrow viewport and confirm the student form and admin detail view remain usable.

## 15. Implementation boundaries

Likely areas of change are:

- `nlp/pipeline.py` for trace hooks and stage boundaries.
- A focused trace module under `nlp/` or `services/`.
- Repository interfaces and Firebase implementation for processing runs and prediction overrides.
- `pages/submit_complaint.py` for the simplified student flow.
- `pages/admin_queue.py` for the live inbox and pipeline inspector.
- New administrator corpus and model pages.
- `app.py` and `utils/ui.py` for navigation and the restrained visual system.
- Training and data-preparation scripts for Corpus v2.
- Project documentation for sources, licenses, manual verification, and administrator provisioning.

The work must preserve existing authentication, role checks, complaint persistence, notifications, assignment concurrency, resolution-note validation, and resolved-case history.

## 16. Delivery sequence

Implementation planning should order the work as follows:

1. Add the trace contract and Firestore processing-run operations.
2. Instrument the existing NLP pipeline without changing prediction behavior.
3. Add failure retention and administrator retry.
4. Build the live administrator inbox and pipeline inspector.
5. Simplify the student submission, review, confirmation, and tracking screens.
6. Add Corpus and Models administrator pages.
7. Ingest, attribute, normalize, and review Corpus v2.
8. Retrain and evaluate models while preserving separate source metrics.
9. Complete the approved manual verification checklist.

This sequence makes observability truthful before the UI is built around it and keeps corpus changes distinguishable from interface and pipeline changes.
