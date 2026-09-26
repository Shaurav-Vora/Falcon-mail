"""Administrator view of Falcon Mail corpus provenance and composition."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, Iterable, List

import streamlit as st

from config import BASE_DIR
from utils.auth import get_current_user
from utils.ui import render_admin_evidence_header


CORPUS_PATH = Path(BASE_DIR) / "data" / "processed" / "corpus_v2.csv"
SUMMARY_PATH = Path(BASE_DIR) / "data" / "metadata" / "corpus_v2_summary.json"
PREPARE_COMMAND = "python training/prepare_corpus_v2.py --finalize"
SAFE_SAMPLE_FIELDS = ("text", "category", "urgency", "source_type", "split", "review_status")


class CorpusArtifactError(ValueError):
    """Raised when a published corpus artifact cannot be safely displayed."""


def _load_artifacts() -> tuple[Dict[str, Any], List[Dict[str, str]]]:
    if not SUMMARY_PATH.exists() or not CORPUS_PATH.exists():
        raise CorpusArtifactError("Corpus v2 has not been prepared on this machine.")
    try:
        with SUMMARY_PATH.open("r", encoding="utf-8") as handle:
            summary = json.load(handle)
        with CORPUS_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
    except (OSError, csv.Error, json.JSONDecodeError) as error:
        raise CorpusArtifactError("The Corpus v2 files are incomplete or malformed.") from error
    if not isinstance(summary, dict) or not rows or "text" not in rows[0]:
        raise CorpusArtifactError("The Corpus v2 files are incomplete or malformed.")
    return summary, rows


def _count(rows: Iterable[Dict[str, str]], field: str) -> Dict[str, int]:
    return dict(Counter((row.get(field) or "Unspecified").strip() for row in rows))


def _mapping(summary: Dict[str, Any], *keys: str) -> Dict[str, int]:
    for key in keys:
        value = summary.get(key)
        if isinstance(value, dict):
            parsed = {}
            for name, count in value.items():
                try:
                    parsed_count = int(count)
                except (TypeError, ValueError):
                    continue
                if parsed_count >= 0:
                    parsed[str(name)] = parsed_count
            if parsed:
                return parsed
    return {}


def _integer(summary: Dict[str, Any], fallback: int, *keys: str) -> int:
    for key in keys:
        value = summary.get(key)
        if value is not None:
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                continue
            if parsed >= 0:
                return parsed
    return fallback


def _render_distribution(title: str, values: Dict[str, int]) -> None:
    st.markdown(f"#### {title}")
    if not values:
        st.caption("Not recorded in this corpus summary.")
        return
    total = max(sum(values.values()), 1)
    for label, count in sorted(values.items(), key=lambda item: (-item[1], item[0])):
        st.write(label)
        st.progress(count / total, text=f"{count:,} · {count / total:.1%}")


def _source_entries(summary: Dict[str, Any], source_counts: Dict[str, int]) -> List[Dict[str, Any]]:
    sources = summary.get("sources") or summary.get("source_provenance") or []
    if isinstance(sources, dict):
        sources = [dict(value, name=name) if isinstance(value, dict) else {"name": name}
                   for name, value in sources.items()]
    if isinstance(sources, list) and sources:
        parsed_sources = [source for source in sources if isinstance(source, dict)]
        if parsed_sources:
            return parsed_sources
    return [
        {
            "name": name,
            "count": count,
            "license": summary.get("license"),
            "citation": summary.get("citation"),
            "review_status": summary.get("review_status"),
        }
        for name, count in source_counts.items()
    ]


def _privacy_safe_text(value: str) -> str:
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[email removed]", value or "")
    return re.sub(r"(?<!\w)(?:\+?\d[\d\s()-]{6,}\d)(?!\w)", "[number removed]", text)


def _render_samples(rows: List[Dict[str, str]]) -> None:
    st.markdown("### Privacy-safe sample browser")
    st.caption("Only normalized complaint text and training labels are shown. Source IDs and personal fields stay hidden.")
    filter_columns = st.columns(3)
    filtered = rows
    for column, (label, field) in zip(
        filter_columns,
        (("Source", "source_type"), ("Split", "split"), ("Category", "category")),
    ):
        options = ["All"] + sorted({(row.get(field) or "Unspecified") for row in rows})
        with column:
            selected = st.selectbox(label, options, key=f"corpus_filter_{field}")
        if selected != "All":
            filtered = [row for row in filtered if (row.get(field) or "Unspecified") == selected]

    if not filtered:
        st.info("No approved records match these filters.")
        return
    sample_index = st.number_input(
        "Sample number",
        min_value=1,
        max_value=len(filtered),
        value=1,
        step=1,
    )
    sample = filtered[int(sample_index) - 1]
    with st.container(border=True):
        st.write(_privacy_safe_text(sample.get("text", "")))
        labels = [
            f"{field.replace('_', ' ').title()}: {sample.get(field) or 'Unspecified'}"
            for field in SAFE_SAMPLE_FIELDS[1:]
        ]
        st.caption(" | ".join(labels))
    st.caption(f"Showing record {int(sample_index):,} of {len(filtered):,} matching records")


def render_corpus_page() -> None:
    """Render corpus evidence for administrators only."""
    user = get_current_user()
    if not user or not user.is_admin:
        st.error("Access Denied: Administrator privileges required.")
        return

    render_admin_evidence_header(
        "Corpus",
        "Inspect what the classifiers learned from, how records were reviewed, and how groups were split.",
    )
    try:
        summary, rows = _load_artifacts()
    except CorpusArtifactError as error:
        st.warning(str(error))
        st.write("Prepare the reviewed corpus before using this page:")
        st.code(PREPARE_COMMAND, language="powershell")
        return

    source_counts = _mapping(summary, "source_counts", "sources_count") or _count(rows, "source_dataset")
    split_counts = _mapping(summary, "split_counts", "splits") or _count(rows, "split")
    category_counts = _mapping(summary, "category_distribution", "category_counts") or _count(rows, "category")
    urgency_counts = _mapping(summary, "urgency_distribution", "urgency_counts") or _count(rows, "urgency")
    review_counts = _mapping(summary, "review_counts", "review_status_counts") or _count(rows, "review_status")
    groups = {
        row.get("incident_group_id") or row.get("template_group_id")
        for row in rows
        if row.get("incident_group_id") or row.get("template_group_id")
    }
    group_sizes = Counter(
        row.get("incident_group_id") or row.get("template_group_id")
        for row in rows
        if row.get("incident_group_id") or row.get("template_group_id")
    )
    word_counts = [len((row.get("text") or "").split()) for row in rows]

    metrics = st.columns(4)
    metrics[0].metric("Training records", f"{_integer(summary, len(rows), 'total_rows', 'dataset_size'):,}")
    metrics[1].metric("Groups", f"{_integer(summary, len(groups), 'group_count'):,}")
    metrics[2].metric(
        "Approved",
        f"{_integer(summary, review_counts.get('approved', 0), 'approved_count'):,}",
    )
    metrics[3].metric(
        "Excluded",
        f"{_integer(summary, review_counts.get('excluded', 0), 'excluded_count'):,}",
    )
    st.caption(
        f"Corpus version: {summary.get('corpus_version') or 'Not recorded'} · "
        f"SHA-256: {summary.get('sha256') or summary.get('dataset_hash') or 'Not recorded'}"
    )
    st.caption(
        f"Complaint length: median {median(word_counts):.0f} words · "
        f"mean {mean(word_counts):.1f} · longest {max(word_counts):,} · "
        f"multi-record groups: {sum(size > 1 for size in group_sizes.values()):,}"
    )

    distribution_columns = st.columns(2, gap="large")
    with distribution_columns[0]:
        _render_distribution("Sources", source_counts)
        _render_distribution("Data splits", split_counts)
    with distribution_columns[1]:
        _render_distribution("Categories", category_counts)
        _render_distribution("Urgency", urgency_counts)

    st.divider()
    st.markdown("### Source record")
    for source in _source_entries(summary, source_counts):
        with st.container(border=True):
            st.write(source.get("name") or source.get("dataset") or "Unnamed source")
            details = st.columns(3)
            details[0].caption(f"Records: {source.get('count', 'Not recorded')}")
            details[1].caption(f"Review: {source.get('review_status') or 'Not recorded'}")
            details[2].caption(f"License: {source.get('license') or 'Not recorded'}")
            st.caption(f"Citation: {source.get('citation') or source.get('url') or 'Not recorded'}")

    st.divider()
    _render_samples(rows)
