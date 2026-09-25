# Falcon Mail Minimal Student and Admin UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current promotional card-heavy interface with a minimal student ticket flow and an administrator live inbox with pipeline, corpus, and model inspection.

**Architecture:** Streamlit remains the only frontend. Student submission uses form review followed by one genuine processing run; the admin queue polls repository processing runs and opens a detail inspector without simulating stages. Corpus and model pages read versioned local metadata and never expose raw private tickets.

**Tech Stack:** Streamlit 1.63, Python, HTML/CSS, Plotly, Firestore repository APIs from the live trace plan

**Spec:** `docs/superpowers/specs/2026-09-25-minimal-ui-live-nlp-corpus-design.md`

## Global Constraints

- Use `Falcon Mail` in every user-facing title, message, spinner, and navigation label.
- Do not add a frontend framework, custom JavaScript build, or new UI dependency.
- Use the approved palette and reserve orange for actions, red for real failure/critical states.
- Remove decorative hero banners, gradients, repeated card grids, and unnecessary AI marketing copy.
- Do not add automated tests or modify the existing `tests/` directory.
- Preserve keyboard focus, readable contrast, mobile usability, RBAC, assignment concurrency, and resolution-note validation.

## Review Focus

- Refreshing during form review must not submit or duplicate a ticket.
- A processing failure must show the student a ticket number and `Needs staff review`.
- An admin selecting a run while the inbox refreshes must keep the same selection.
- A student entering an untrusted HTML string must see text, not executable markup.
- Missing corpus/model metadata must show a helpful empty state rather than crash a page.

---

### Task 1: Falcon Mail visual foundation and navigation

**Files:**
- Modify: `assets/style.css`
- Modify: `utils/ui.py`
- Modify: `app.py`
- Modify: `pages/login.py`
- Modify: `pages/home.py`
- Modify: `pages/dashboard.py`
- Modify: `pages/notifications.py`
- Modify: `pages/student_complaints.py`
- Modify: `pages/resolved_cases.py`
- Modify: `pages/history.py`
- Modify: `training/dataset_generator.py`
- Modify: `README.md`

**Interfaces:**
- Produces consistent page shell and navigation for later tasks.

- [ ] **Step 1: Replace user-facing legacy branding with `Falcon Mail`**

Use `rg -n "SENTINEL|Sentinel|sentinel"` to find product copy. Preserve compatibility identifiers such as `SENTINEL_STORAGE_BACKEND` and `sentinel.db`.

- [ ] **Step 2: Replace CSS tokens**

Define canvas `#F6F8FB`, surface `#FFFFFF`, ink `#17233C`, secondary `#64748B`, action `#F15A24`, success `#138A5B`, and critical `#C9362B`. Use Instrument Sans with system fallbacks, visible `:focus-visible`, and `prefers-reduced-motion`.

- [ ] **Step 3: Remove hero, gradient, and repeated shadow/card styles**

Keep borders and spacing only where they encode grouping. Retain urgency/status colors.

- [ ] **Step 4: Simplify role navigation**

Render student items `Raise a ticket`, `My tickets`, and `Notifications` as a compact horizontal navigation row in the main header. Keep a restrained admin sidebar for `Live tickets`, `Dashboard`, `Corpus`, `Models`, and `Resolved` because the operational workspace needs persistent navigation.

- [ ] **Step 5: Start Streamlit and manually check login plus both role menus at desktop and narrow widths**

- [ ] **Step 6: Commit**

```powershell
git add app.py assets/style.css utils/ui.py pages training/dataset_generator.py README.md
git commit -m "style: establish the Falcon Mail interface"
```

### Task 2: Two-step student ticket flow

**Files:**
- Modify: `pages/submit_complaint.py`
- Modify: `pages/student_complaints.py`

**Interfaces:**
- Consumes: `process_complaint()` and processing status from the live trace plan.
- Produces session keys `ticket_draft`, `ticket_reviewing`, and `last_submission_result`.

- [ ] **Step 1: Split submission into focused render functions**

```python
def render_ticket_form() -> None: ...
def render_ticket_review(draft: dict) -> None: ...
def submit_reviewed_ticket(draft: dict) -> dict: ...
def render_submission_result_view(result: dict) -> None: ...
```

- [ ] **Step 2: Build the narrow one-column form**

Keep description, location, and optional category context. Remove suggestion-chip grids, reporting-tip cards, and AI marketing cards. Escape every value inserted into HTML.

- [ ] **Step 3: Make `Review ticket` non-persistent**

Store trimmed form values in `ticket_draft`, set `ticket_reviewing=True`, and rerun. The review screen shows only user-entered fields with `Edit` and `Send ticket`; it does not invoke NLP.

- [ ] **Step 4: Make `Send ticket` invoke NLP exactly once**

Disable repeat intent through session state while the call is active. Show a simple processing status, then store the result and clear the draft.

- [ ] **Step 5: Render success and manual-review outcomes**

Success shows ticket ID, category, urgency, resolved location, department, and privacy-safe duplicate notice. Failure retention shows ticket ID and `Needs staff review`, not a raw exception.

- [ ] **Step 6: Update `My tickets` to display `Processing` and `Needs Review` safely when analysis fields are null**

- [ ] **Step 7: Manually verify edit-before-send, refresh, double-click resistance, normal success, critical result, duplicate notice, and retained failure**

- [ ] **Step 8: Commit**

```powershell
git add pages/submit_complaint.py pages/student_complaints.py
git commit -m "feat: simplify the Falcon Mail student flow"
```

### Task 3: Live administrator inbox and pipeline inspector

**Files:**
- Modify: `pages/admin_queue.py`

**Interfaces:**
- Consumes: `list_processing_runs()`, `get_processing_run()`, `retry_complaint_processing()`, and existing complaint operations.
- Produces session key `selected_processing_run_id`.

- [ ] **Step 1: Replace the current stacked complaint cards with a master-detail layout**

Use a compact queue column and a detail column. Each row shows ticket ID, title, location, status, current stage, elapsed time, and urgency when known.

- [ ] **Step 2: Merge processing and unresolved records by `ticket_id`**

Prefer the latest run state for progress and the complaint record for authoritative assignment/status. Do not show duplicate rows.

- [ ] **Step 3: Preserve selection across the two-second fragment refresh**

Store the run ID in session state and clear it only when the selected run no longer exists.

- [ ] **Step 4: Render the pipeline rail**

Use the ten approved stage names in order. Completed stages show result, confidence, duration, source, and concise evidence. Running, pending, skipped, and failed states have distinct accessible treatments.

- [ ] **Step 5: Add retry, correction, and existing operational controls**

Retry is visible only for `needs_review` or `failed`. Category, urgency, location, and department corrections call `override_complaint_prediction()` with a required reason. Assignment, status change, resolution note, and resolution validation remain available after analysis.

- [ ] **Step 6: Manually submit a ticket in a student browser and observe real stages in an admin browser**

Confirm the UI never advances ahead of stored Firestore state and retains selection during refresh.

- [ ] **Step 7: Commit**

```powershell
git add pages/admin_queue.py
git commit -m "feat: add the live Falcon Mail processing inbox"
```

### Task 4: Corpus and Models admin pages

**Files:**
- Create: `pages/corpus.py`
- Create: `pages/models.py`
- Modify: `app.py`
- Modify: `utils/ui.py`

**Interfaces:**
- Consumes: `data/metadata/corpus_v2_summary.json`, `data/processed/corpus_v2.csv`, and `models/training_metadata.json` from the corpus plan.

- [ ] **Step 1: Add admin-only routing for `Corpus` and `Models`**

Both render functions must call `get_current_user()` and stop with `Access Denied` unless `is_admin`.

- [ ] **Step 2: Build the Corpus page**

Show total/source/split counts, category and urgency distributions, group counts, approved/excluded totals, source citation and license, and a privacy-safe sample browser containing only normalized complaint text and labels.

- [ ] **Step 3: Build the Models page**

Show model algorithm/version/date/corpus hash, category and urgency metrics, per-class results, confusion matrices, MiniLM model name, duplicate threshold, and explicit limitations.

- [ ] **Step 4: Add empty states**

If either JSON/CSV is absent or malformed, explain the exact preparation command to run instead of raising an exception.

- [ ] **Step 5: Manually confirm student denial, admin access, distributions, citations, confusion matrices, and missing-file messages**

- [ ] **Step 6: Commit**

```powershell
git add app.py utils/ui.py pages/corpus.py pages/models.py
git commit -m "feat: expose Falcon Mail corpus and model evidence"
```

### Task 5: Final manual walkthrough and documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add startup, admin provisioning, corpus preparation, retraining, and manual verification instructions**

- [ ] **Step 2: Run the twelve-step manual checklist from the approved specification**

- [ ] **Step 3: Record observed model metrics and known limitations without claiming unmeasured performance**

- [ ] **Step 4: Confirm `rg -n "SENTINEL|Sentinel" app.py pages utils assets README.md` returns no user-facing branding**

- [ ] **Step 5: Commit**

```powershell
git add README.md
git commit -m "docs: add Falcon Mail operating walkthrough"
```
