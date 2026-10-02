"""Build the review queue and publish the reviewed Falcon Mail Corpus v2."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    CATEGORIES,
    CATEGORY_DEPARTMENT_MAP,
    CORPUS_V2_PATH,
    CORPUS_V2_REVIEW_PATH,
    CORPUS_V2_SUMMARY_PATH,
    EMERGENCY_KEYWORDS,
    EXTERNAL_RAW_DIR,
    FALCON_RAW_DIR,
    RANDOM_SEED,
    URGENCY_LEVELS,
)


REVISION = "3a21d7a28cca2dad1ced731246772810798215f7"
SOURCE_URL = "https://huggingface.co/datasets/alaminxpro/university-students-complaints"
REVIEW_FIELDS = [
    "record_id", "text", "suggested_category", "suggested_urgency",
    "reviewed_category", "reviewed_urgency", "review_status", "review_note",
    "department", "location", "incident_group_id", "template_group_id",
    "source_dataset", "source_record_id", "source_type", "original_category",
    "original_urgency", "original_primary_department", "original_aspects",
    "publisher_split", "split",
]
FINAL_FIELDS = [
    "record_id", "text", "category", "urgency", "department", "location",
    "incident_group_id", "template_group_id", "source_dataset", "source_record_id",
    "source_type", "original_category", "original_urgency", "reviewed_category",
    "reviewed_urgency", "review_status", "split",
]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def _contains_phrase(text: str, phrase: str) -> bool:
    """Match a phrase as words so, for example, 'tap' does not match 'laptop'."""
    return bool(re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text, re.IGNORECASE))


def _falcon_rows() -> list[dict[str, str]]:
    rows = []
    raw_path = Path(FALCON_RAW_DIR) / "complaints.csv"
    if not raw_path.exists():
        raise FileNotFoundError(f"Missing immutable Falcon Mail source snapshot: {raw_path}")
    for index, source in enumerate(_read_csv(raw_path), start=1):
        category = source["category"].strip()
        urgency = source["urgency"].strip()
        group = f"falcon:{source['template_group_id'].strip() or index}"
        rows.append({
            "record_id": f"falcon-{index:04d}",
            "text": source["text"].strip(),
            "suggested_category": category,
            "suggested_urgency": urgency,
            "reviewed_category": category,
            "reviewed_urgency": urgency,
            "review_status": "approved",
            "review_note": "Existing Falcon Mail label retained.",
            "department": CATEGORY_DEPARTMENT_MAP[category],
            "location": "",
            "incident_group_id": group,
            "template_group_id": group,
            "source_dataset": "falcon_mail_v1",
            "source_record_id": str(index),
            "source_type": "synthetic",
            "original_category": category,
            "original_urgency": urgency,
            "original_primary_department": "",
            "original_aspects": "",
            "publisher_split": "",
            "split": "",
        })
    return rows


def _category_decision(row: dict[str, str]) -> tuple[str, str]:
    category = row["Category"].strip()
    primary = row["Primary_Department"].strip()
    aspects = row["Aspects"].lower()
    text = row["Complaint_Description"].lower()
    # Publisher aspect tags are broad and often contain unrelated secondary labels.
    # Use them only for the clear transport branch; specific facility labels come
    # from the complaint wording and primary department.
    evidence = text

    if category == "Academic":
        return "Academic", "Publisher Academic label retained."
    if category in {"Administrative", "Finance"}:
        return "Administration", f"Publisher {category} label consolidated into Administration."
    if category == "Technical":
        if primary == "Transport & Parking" or "transport" in aspects or "parking" in aspects:
            return "Transport", "Technical transport issue routed to Transport."
        return "IT", "Technical issue mapped to IT."
    if category != "Infrastructure":
        return "", f"Unmapped publisher category: {category}."

    if primary == "IT":
        return "IT", "Infrastructure record has IT as its primary department."
    if any(_contains_phrase(evidence, word) for word in ("dirty", "clean", "cleaning", "garbage", "trash", "dust", "hygiene", "odor", "odors", "smell")):
        return "Cleanliness", "Cleanliness language takes precedence within Infrastructure."
    if any(_contains_phrase(evidence, word) for word in ("electrical", "electric", "light", "lights", "fan", "fans", "socket", "sockets", "charging", "power", "ac", "air condition", "air conditioning", "cable", "cables", "generator")):
        return "Electrical", "Electrical/AC evidence mapped to Electrical."
    if any(_contains_phrase(evidence, word) for word in ("water", "plumbing", "toilet", "toilets", "sink", "sinks", "drain", "drains", "leak", "leaking", "tap", "taps", "faucet", "faucets", "hand wash")):
        return "Plumbing", "Water or plumbing evidence mapped to Plumbing."
    if any(_contains_phrase(text, phrase) for phrase in ("not enough", "inadequate", "more washrooms", "more classrooms", "long line", "waiting time", "overcrowded", "prayer room", "separate male", "separate female", "every floor should have")):
        return "Facilities", "Capacity or availability request mapped to Facilities."
    if primary == "Transport & Parking" or "transport" in aspects or "parking" in aspects:
        return "Transport", "Infrastructure transport/parking issue mapped to Transport."
    if primary in {"Library", "Student Welfare"}:
        return "Facilities", f"{primary} infrastructure mapped to Facilities."
    return "Maintenance", "Remaining physical infrastructure mapped to Maintenance."


def _urgency_decision(row: dict[str, str]) -> tuple[str, str]:
    original = row["Severity"].strip()
    base = {"Low": "Low", "Medium": "Medium", "High": "High", "Urgent": "High"}.get(original, "")
    text = row["Complaint_Description"].lower()
    trigger = next((phrase for phrase in EMERGENCY_KEYWORDS if _contains_phrase(text, phrase)), "")
    if trigger:
        return "Critical", f"Safety phrase '{trigger}' elevates the reviewed urgency to Critical."
    if base:
        note = "Publisher severity retained." if original == base else "Publisher Urgent normalized to High; Critical is reserved for safety emergencies."
        return base, note
    return "", f"Unmapped publisher severity: {original}."


def _external_rows(finalize: bool) -> list[dict[str, str]]:
    rows = []
    for publisher_split in ("train", "test"):
        path = Path(EXTERNAL_RAW_DIR) / f"{publisher_split}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing {path}. Run training/fetch_external_corpus.py first.")
        for source in _read_csv(path):
            source_id = source["ID"].strip()
            group_id = source["Complaint_Group_ID"].strip() or source_id
            category, category_note = _category_decision(source)
            urgency, urgency_note = _urgency_decision(source)
            approved = bool(category and urgency)
            rows.append({
                "record_id": f"external-{source_id}",
                "text": source["Complaint_Description"].strip(),
                "suggested_category": category,
                "suggested_urgency": urgency,
                "reviewed_category": category if finalize and approved else "",
                "reviewed_urgency": urgency if finalize and approved else "",
                "review_status": "approved" if finalize and approved else ("excluded" if finalize else "pending"),
                "review_note": f"{category_note} {urgency_note}" if finalize else "Awaiting Falcon Mail label review.",
                "department": CATEGORY_DEPARTMENT_MAP.get(category, "") if finalize else "",
                "location": "",
                "incident_group_id": f"external:{group_id}",
                "template_group_id": f"external:{group_id}",
                "source_dataset": "university_students_complaints",
                "source_record_id": source_id,
                "source_type": "external",
                "original_category": source["Category"].strip(),
                "original_urgency": source["Severity"].strip(),
                "original_primary_department": source["Primary_Department"].strip(),
                "original_aspects": source["Aspects"].strip(),
                "publisher_split": publisher_split,
                "split": "",
            })
    return rows


def _assign_splits(rows: list[dict[str, str]]) -> None:
    groups = sorted({row["incident_group_id"] for row in rows})
    random.Random(RANDOM_SEED).shuffle(groups)
    train_end = round(len(groups) * 0.70)
    validation_end = train_end + round(len(groups) * 0.15)
    assignments = {
        group: "train" if index < train_end else "validation" if index < validation_end else "test"
        for index, group in enumerate(groups)
    }
    for row in rows:
        row["split"] = assignments[row["incident_group_id"]]
    split_groups = {
        split: {row["incident_group_id"] for row in rows if row["split"] == split}
        for split in ("train", "validation", "test")
    }
    assert not (split_groups["train"] & split_groups["validation"])
    assert not (split_groups["train"] & split_groups["test"])
    assert not (split_groups["validation"] & split_groups["test"])


def _count(rows: list[dict[str, str]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(row[field] for row in rows).items()))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_review_queue() -> None:
    rows = _falcon_rows() + _external_rows(finalize=False)
    _write_csv(Path(CORPUS_V2_REVIEW_PATH), rows, REVIEW_FIELDS)
    print(f"Review queue: {len(rows)} rows ({sum(r['review_status'] == 'pending' for r in rows)} pending)")


def finalize() -> None:
    review_rows = _falcon_rows() + _external_rows(finalize=True)
    _assign_splits(review_rows)
    _write_csv(Path(CORPUS_V2_REVIEW_PATH), review_rows, REVIEW_FIELDS)

    approved = [row for row in review_rows if row["review_status"] == "approved"]
    final_rows = [
        {
            **row,
            "category": row["reviewed_category"],
            "urgency": row["reviewed_urgency"],
        }
        for row in approved
    ]
    if not final_rows:
        raise ValueError("Review produced no approved records.")
    if any(row["reviewed_category"] not in CATEGORIES for row in final_rows):
        raise ValueError("Review produced a category outside Falcon Mail's taxonomy.")
    if any(row["reviewed_urgency"] not in URGENCY_LEVELS for row in final_rows):
        raise ValueError("Review produced an urgency outside Falcon Mail's taxonomy.")
    if any(not row["text"].strip() for row in final_rows):
        raise ValueError("Review produced an empty complaint text.")
    for group in {row["incident_group_id"] for row in final_rows}:
        if len({row["split"] for row in final_rows if row["incident_group_id"] == group}) != 1:
            raise ValueError(f"Group leakage detected for {group}.")

    normalized_text_splits: dict[str, set[str]] = {}
    for row in final_rows:
        normalized = " ".join(row["text"].lower().split())
        normalized_text_splits.setdefault(normalized, set()).add(row["split"])
    if any(len(splits) > 1 for splits in normalized_text_splits.values()):
        raise ValueError("Exact duplicate text leakage detected across splits.")

    corpus_path = Path(CORPUS_V2_PATH)
    _write_csv(corpus_path, final_rows, FINAL_FIELDS)
    Path(CORPUS_V2_SUMMARY_PATH).parent.mkdir(parents=True, exist_ok=True)
    external_rows = [row for row in review_rows if row["source_type"] == "external"]
    normalized_external_texts = [" ".join(row["text"].lower().split()) for row in external_rows]
    external_group_urgencies: dict[str, set[str]] = {}
    for row in external_rows:
        external_group_urgencies.setdefault(row["incident_group_id"], set()).add(row["original_urgency"])
    summary = {
        "corpus_version": "2.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sha256": _sha256(corpus_path),
        "total_rows": len(final_rows),
        "approved_count": len(approved),
        "excluded_count": sum(row["review_status"] == "excluded" for row in review_rows),
        "pending_count": sum(row["review_status"] == "pending" for row in review_rows),
        "group_count": len({row["incident_group_id"] for row in final_rows}),
        "source_counts": _count(final_rows, "source_dataset"),
        "source_type_counts": _count(final_rows, "source_type"),
        "category_distribution": _count(final_rows, "category"),
        "urgency_distribution": _count(final_rows, "urgency"),
        "split_counts": _count(final_rows, "split"),
        "review_counts": _count(review_rows, "review_status"),
        "sources": [
            {
                "name": "Falcon Mail v1",
                "count": sum(row["source_dataset"] == "falcon_mail_v1" for row in final_rows),
                "license": "Project-owned synthetic data",
                "review_status": "approved",
                "citation": "data/raw/falcon_mail_v1/complaints.csv",
            },
            {
                "name": "University Students Complaints Dataset",
                "count": sum(row["source_dataset"] == "university_students_complaints" for row in final_rows),
                "license": "CC BY 4.0",
                "review_status": "approved through documented rulebook",
                "citation": SOURCE_URL,
                "revision": REVISION,
            },
        ],
        "audit": {
            "external_original_rows": len(external_rows),
            "external_unique_groups": len(external_group_urgencies),
            "external_exact_duplicate_texts": len(normalized_external_texts) - len(set(normalized_external_texts)),
            "publisher_groups_with_mixed_severity": sum(len(values) > 1 for values in external_group_urgencies.values()),
            "personal_fields_excluded_from_features": ["Gender", "Semester", "Student_Dept", "Timestamp"],
            "split_policy": "70/15/15 deterministic shuffle of incident groups with seed 42",
        },
    }
    summary_path = Path(CORPUS_V2_SUMMARY_PATH)
    temporary = summary_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    temporary.replace(summary_path)
    print(f"Published Corpus v2: {len(final_rows)} rows, {summary['group_count']} groups")
    print(f"Splits: {summary['split_counts']}")
    print(f"Categories: {summary['category_distribution']}")
    print(f"Urgency: {summary['urgency_distribution']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build-review-queue", action="store_true")
    mode.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    if args.build_review_queue:
        build_review_queue()
    else:
        finalize()


if __name__ == "__main__":
    main()
