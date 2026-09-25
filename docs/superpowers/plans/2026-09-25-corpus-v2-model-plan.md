# Falcon Mail Corpus v2 and Model Reporting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a provenance-preserving Corpus v2 from Falcon Mail data and the approved university complaint source, then produce model metadata the admin UI can explain honestly.

**Architecture:** Raw inputs are immutable, normalization writes a versioned processed CSV, and grouped splits prevent paraphrase/template leakage. Existing scikit-learn trainers consume the normalized corpus and publish machine-readable evaluation metadata; no automatic retraining is added.

**Tech Stack:** Python 3.14 standard library, pandas, scikit-learn, joblib, CSV/JSON

**Spec:** `docs/superpowers/specs/2026-09-25-minimal-ui-live-nlp-corpus-design.md`

## Global Constraints

- Use only online-form ticket text; do not add email or WhatsApp channel fields.
- Attribute `alaminxpro/university-students-complaints` under CC BY 4.0.
- Keep raw files unchanged and exclude gender, semester, and student department from model features.
- Keep synthetic and external metrics separate.
- Keep all records from one incident/template group in one split.
- Do not add automated tests or modify the existing `tests/` directory.

## Review Focus

- An external row with an unmapped or uncertain label must be excluded from training, not silently coerced.
- Paraphrases sharing `Complaint_Group_ID` must never cross splits.
- Re-running preparation with identical inputs must produce the same split.
- Training metadata must state source counts and dataset hash.
- Download or license failure must leave existing corpus and models unchanged.

---

### Task 1: Versioned corpus directories and source record

**Files:**
- Create: `data/raw/falcon_mail_v1/complaints.csv`
- Create: `data/raw/university_students_complaints/README.md`
- Create: `data/metadata/DATA_SOURCES.md`
- Create: `data/metadata/label_mapping.json`
- Modify: `.gitignore` if downloaded raw files should remain local

**Interfaces:**
- Produces documented raw inputs for the preparation script.

- [ ] **Step 1: Copy the current `data/complaints.csv` byte-for-byte into the versioned raw directory**

- [ ] **Step 2: Record the external source**

Pin the Hugging Face revision `3a21d7a28cca2dad1ced731246772810798215f7`, list `train.csv` and `test.csv`, record CC BY 4.0 attribution, and state that publisher labels require Falcon Mail review.

- [ ] **Step 3: Define label suggestions**

`Academic -> Academic`, `Administrative -> Administration`, `Finance -> Administration`, and `Technical -> IT` are suggestions. `Infrastructure` remains manual because aspects determine Maintenance, Electrical, Plumbing, Facilities, Cleanliness, or Transport. No suggestion becomes a reviewed label automatically.

- [ ] **Step 4: Commit**

```powershell
git add data/raw/falcon_mail_v1 data/raw/university_students_complaints/README.md data/metadata
git commit -m "docs: register Falcon Mail corpus sources"
```

### Task 2: Reproducible external download and review queue

**Files:**
- Create: `training/fetch_external_corpus.py`
- Create: `training/prepare_corpus_v2.py`
- Modify: `config.py`

**Interfaces:**
- Produces: `data/raw/university_students_complaints/train.csv`, `test.csv`, and `data/processed/corpus_v2_review.csv`.

- [ ] **Step 1: Add corpus paths to `config.py`**

Define `CORPUS_V2_PATH`, `CORPUS_V2_REVIEW_PATH`, `CORPUS_V2_SUMMARY_PATH`, and raw source directories without replacing legacy `COMPLAINTS_CSV_PATH` yet.

- [ ] **Step 2: Implement a standard-library downloader**

Download the two pinned raw CSV URLs to temporary `.download` files, validate non-empty CSV headers, then atomically rename. On failure, delete only temporary files.

- [ ] **Step 3: Normalize Falcon Mail rows**

Map `text`, `category`, `urgency`, and `template_group_id` into the approved schema; set `source_dataset="falcon_mail_v1"`, `source_type="synthetic"`, and `review_status="approved"`.

- [ ] **Step 4: Normalize external rows into a review queue**

Preserve `Complaint_Description`, original labels, source ID, and `Complaint_Group_ID`. Populate suggested labels separately while leaving `reviewed_category` and `reviewed_urgency` empty and `review_status="pending"`.

- [ ] **Step 5: Run the fetch and preparation commands**

```powershell
python training/fetch_external_corpus.py
python training/prepare_corpus_v2.py --build-review-queue
```

Confirm 585 Falcon Mail rows plus 332 external rows are represented before review.

- [ ] **Step 6: Commit**

```powershell
git add config.py training/fetch_external_corpus.py training/prepare_corpus_v2.py data/processed/corpus_v2_review.csv
git commit -m "feat: prepare the Corpus v2 review queue"
```

### Task 3: Review, grouped split, and corpus summary

**Files:**
- Modify: `data/processed/corpus_v2_review.csv`
- Modify: `training/prepare_corpus_v2.py`
- Create: `data/processed/corpus_v2.csv`
- Create: `data/metadata/corpus_v2_summary.json`

**Interfaces:**
- Produces the approved training file and summary consumed by trainers and the Corpus page.

- [ ] **Step 1: Review every external category and urgency label**

Use Falcon Mail's eleven categories and four urgency levels. Mark each external row `approved` or `excluded` and preserve its original labels. Do not include pending rows in training.

- [ ] **Step 2: Assign deterministic group keys**

Prefix groups with their source: `falcon:<template_group_id>` and `external:<Complaint_Group_ID>`. Rows without a source group receive `record:<source>:<source_record_id>`.

- [ ] **Step 3: Assign 70/15/15 splits by group with seed 42**

Shuffle unique group keys, assign groups rather than rows, and assert in the preparation script that intersections between split group sets are empty.

- [ ] **Step 4: Write summary JSON**

Include corpus version, SHA-256, total rows, source counts, category/urgency distributions, split counts, approved/excluded counts, group count, license/citation, and generation timestamp.

- [ ] **Step 5: Run preparation and manually inspect distributions and ten random rows from each source**

```powershell
python training/prepare_corpus_v2.py --finalize
```

- [ ] **Step 6: Commit**

```powershell
git add data/processed data/metadata/corpus_v2_summary.json training/prepare_corpus_v2.py
git commit -m "data: publish reviewed Falcon Mail Corpus v2"
```

### Task 4: Train and evaluate on Corpus v2

**Files:**
- Modify: `training/train_category.py`
- Modify: `training/train_urgency.py`
- Modify: `training/evaluate.py`
- Modify: `models/training_metadata.json`
- Modify: `config.py`

**Interfaces:**
- Consumes `data/processed/corpus_v2.csv`.
- Produces existing model artifacts plus expanded metadata for the Models page.

- [ ] **Step 1: Point trainers to `CORPUS_V2_PATH` and consume the stored split column**

Train on `train`, select using `validation`, and report final metrics on `test`. Never randomly split rows inside the trainer.

- [ ] **Step 2: Preserve the existing algorithms and safety rules**

Do not change the category model family, urgency model family, MiniLM model, or deterministic emergency elevation in this task.

- [ ] **Step 3: Expand metadata**

Write `corpus_version`, dataset hash, source counts, model version, training timestamp, per-class precision/recall/F1, confusion-matrix labels/values, and separate synthetic/external metrics.

- [ ] **Step 4: Retrain explicitly**

```powershell
python training/train_category.py
python training/train_urgency.py
python training/evaluate.py
```

Review the report rather than treating overall accuracy as sufficient. Confirm Critical recall, macro F1, and external-only results are present.

- [ ] **Step 5: Commit model and metadata changes together**

```powershell
git add config.py training models/category_classifier.pkl models/urgency_classifier.pkl models/training_metadata.json
git commit -m "feat: train Falcon Mail models on Corpus v2"
```

### Task 5: Corpus handoff documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document source locations, preparation commands, attribution, review process, and metric limitations**

- [ ] **Step 2: State clearly which records are synthetic and which are externally sourced**

- [ ] **Step 3: Open the generated CSV and JSON manually and confirm the documented counts match**

- [ ] **Step 4: Commit**

```powershell
git add README.md
git commit -m "docs: document Falcon Mail Corpus v2"
```
