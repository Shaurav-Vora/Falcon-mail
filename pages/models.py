"""Administrator view of Falcon Mail model versions and evaluation evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

from config import BASE_DIR, DEFAULT_DUPLICATE_THRESHOLD, SENTENCE_TRANSFORMER_MODEL
from utils.auth import get_current_user
from utils.ui import render_admin_evidence_header


METADATA_PATH = Path(BASE_DIR) / "models" / "training_metadata.json"
TRAIN_COMMANDS = (
    "python training/train_category.py\n"
    "python training/train_urgency.py\n"
    "python training/evaluate.py"
)


class ModelArtifactError(ValueError):
    """Raised when model evidence cannot be read."""


def _load_metadata() -> Dict[str, Any]:
    if not METADATA_PATH.exists():
        raise ModelArtifactError("Training metadata has not been generated on this machine.")
    try:
        with METADATA_PATH.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise ModelArtifactError("Training metadata is malformed.") from error
    if not isinstance(metadata, dict) or not metadata:
        raise ModelArtifactError("Training metadata is malformed.")
    return metadata


def _percent(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "Not recorded"
    return f"{number:.1%}" if -1 <= number <= 1 else f"{number:.2f}"


def _per_class(model: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    value = model.get("per_class_metrics") or model.get("per_class") or model.get("classification_report") or {}
    if not isinstance(value, dict):
        return {}
    return {
        str(label): scores
        for label, scores in value.items()
        if isinstance(scores, dict)
        and label not in {"accuracy", "macro avg", "weighted avg", "micro avg"}
    }


def _confusion_matrix(model: Dict[str, Any]) -> Optional[Tuple[List[str], List[List[int]]]]:
    matrix = model.get("confusion_matrix")
    labels = model.get("confusion_matrix_labels") or model.get("labels")
    values = model.get("confusion_matrix_values")
    if isinstance(matrix, dict):
        labels = matrix.get("labels") or labels
        values = matrix.get("values") or matrix.get("matrix") or values
    elif isinstance(matrix, list):
        values = matrix
    if not isinstance(labels, list) or not isinstance(values, list):
        return None
    if not labels or len(values) != len(labels) or any(not isinstance(row, list) or len(row) != len(labels) for row in values):
        return None
    return [str(label) for label in labels], values


def _render_model(model_name: str, model: Dict[str, Any]) -> List[str]:
    st.markdown(f"### {model_name}")
    identity = st.columns(3)
    identity[0].metric("Version", model.get("model_version") or "Not recorded")
    identity[1].metric("Training records", model.get("dataset_size") or "Not recorded")
    identity[2].metric("Group leakage", "Detected" if model.get("group_leakage_detected") else "None reported")
    st.write(model.get("algorithm") or "Algorithm not recorded")
    st.caption(
        f"Trained: {model.get('training_timestamp') or model.get('timestamp') or 'Not recorded'} · "
        f"Corpus: {model.get('corpus_version') or 'Legacy corpus'} · "
        f"SHA-256: {model.get('dataset_hash') or 'Not recorded'}"
    )

    metrics = model.get("metrics") if isinstance(model.get("metrics"), dict) else {}
    metric_columns = st.columns(max(1, min(len(metrics), 5)))
    if metrics:
        for column, (name, value) in zip(metric_columns, metrics.items()):
            column.metric(name.replace("_", " ").title(), _percent(value))
    else:
        st.info("Overall evaluation metrics were not recorded for this model.")

    gaps: List[str] = []
    per_class = _per_class(model)
    st.markdown("#### Per-class results")
    if per_class:
        rows = []
        for label, scores in per_class.items():
            rows.append(
                {
                    "Class": label,
                    "Precision": _percent(scores.get("precision")),
                    "Recall": _percent(scores.get("recall")),
                    "F1": _percent(scores.get("f1") or scores.get("f1-score")),
                    "Support": scores.get("support", "Not recorded"),
                }
            )
        st.dataframe(rows, hide_index=True, width="stretch")
    else:
        gaps.append(f"{model_name} per-class precision, recall and F1 are not in the current metadata.")
        st.info("Per-class results will appear after Corpus v2 evaluation.")

    st.markdown("#### Confusion matrix")
    matrix = _confusion_matrix(model)
    if matrix:
        labels, values = matrix
        frame = pd.DataFrame(values, index=[f"Actual {label}" for label in labels], columns=[f"Predicted {label}" for label in labels])
        st.dataframe(frame, width="stretch")
    else:
        gaps.append(f"{model_name} confusion matrix is not in the current metadata.")
        st.info("The confusion matrix will appear after Corpus v2 evaluation.")

    source_metrics = model.get("source_metrics") or model.get("metrics_by_source")
    st.markdown("#### Performance by source")
    if isinstance(source_metrics, dict) and source_metrics:
        rows = []
        for source, values in source_metrics.items():
            if not isinstance(values, dict):
                continue
            rows.append({"Source": source, **{key.replace("_", " ").title(): _percent(value) for key, value in values.items()}})
        st.dataframe(rows, hide_index=True, width="stretch")
    else:
        gaps.append(f"{model_name} synthetic and external results have not been measured separately.")
        st.info("Synthetic and external results have not been measured separately yet.")

    compared = model.get("models_compared")
    if isinstance(compared, dict) and compared:
        with st.expander("Compared algorithms"):
            rows = [{"Algorithm": name, **values} for name, values in compared.items() if isinstance(values, dict)]
            st.dataframe(rows, hide_index=True, width="stretch")
    return gaps


def render_models_page() -> None:
    """Render model evidence for administrators only."""
    user = get_current_user()
    if not user or not user.is_admin:
        st.error("Access Denied: Administrator privileges required.")
        return

    render_admin_evidence_header(
        "Models",
        "Review the exact classifier versions, evaluation evidence, duplicate model, and known limits.",
    )
    try:
        metadata = _load_metadata()
    except ModelArtifactError as error:
        st.warning(str(error))
        st.write("Train and evaluate the classifiers before using this page:")
        st.code(TRAIN_COMMANDS, language="powershell")
        return

    duplicate_columns = st.columns(2)
    duplicate_columns[0].metric("Duplicate model", SENTENCE_TRANSFORMER_MODEL)
    duplicate_columns[1].metric("Similarity threshold", f"{DEFAULT_DUPLICATE_THRESHOLD:.2f}")
    st.caption("MiniLM creates semantic embeddings for duplicate comparison; it does not classify category or urgency.")

    model_choice = st.segmented_control(
        "Classifier",
        ["Category", "Urgency"],
        default="Category",
        key="model_evidence_choice",
    ) or "Category"
    model_key = "category_model" if model_choice == "Category" else "urgency_model"
    model = metadata.get(model_key)
    if not isinstance(model, dict):
        st.warning(f"{model_choice} model metadata is missing.")
        st.code(TRAIN_COMMANDS, language="powershell")
        return

    gaps = _render_model(f"{model_choice} classifier", model)
    declared = metadata.get("limitations") or model.get("limitations") or []
    if isinstance(declared, str):
        declared = [declared]
    st.divider()
    st.markdown("### Known limitations")
    limitations = [
        "Evaluation scores describe the recorded test split; they do not guarantee performance on future campus language.",
        "Deterministic safety rules can elevate urgent incidents after the urgency classifier runs.",
        "MiniLM similarity supports duplicate review but does not prove two reports describe the same incident.",
        *[str(item) for item in declared if item],
        *gaps,
    ]
    for limitation in dict.fromkeys(limitations):
        st.write(f"- {limitation}")
