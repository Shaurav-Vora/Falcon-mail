"""Train and report the Falcon Mail category classifier on Corpus v2."""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import sys
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, precision_recall_fscore_support
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import CATEGORY_MODEL_PATH, CORPUS_V2_PATH, CORPUS_V2_SUMMARY_PATH, MODELS_DIR, RANDOM_SEED
from nlp.preprocessing import preprocess_text


METADATA_PATH = Path(MODELS_DIR) / "training_metadata.json"


def _metrics(y_true, y_pred) -> dict[str, float]:
    _, _, macro_f1, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    _, _, weighted_f1, _ = precision_recall_fscore_support(y_true, y_pred, average="weighted", zero_division=0)
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "macro_f1": round(float(macro_f1), 4),
        "weighted_f1": round(float(weighted_f1), 4),
    }


def _source_metrics(frame: pd.DataFrame, predictions) -> dict[str, dict[str, float | int]]:
    result = {}
    predicted = pd.Series(predictions, index=frame.index)
    for source_type, subset in frame.groupby("source_type"):
        result[str(source_type)] = {"records": len(subset), **_metrics(subset["category"], predicted.loc[subset.index])}
    return result


def _report(y_true, y_pred, labels: list[str]) -> dict[str, dict[str, float | int]]:
    report = classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0)
    return {
        label: {
            "precision": round(float(report[label]["precision"]), 4),
            "recall": round(float(report[label]["recall"]), 4),
            "f1-score": round(float(report[label]["f1-score"]), 4),
            "support": int(report[label]["support"]),
        }
        for label in labels
    }


def _update_metadata(section: dict) -> None:
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8")) if METADATA_PATH.exists() else {}
    metadata["category_model"] = section
    temporary = METADATA_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    temporary.replace(METADATA_PATH)


def _load_corpus() -> tuple[pd.DataFrame, dict, str]:
    corpus_path = Path(CORPUS_V2_PATH)
    if not corpus_path.exists():
        raise FileNotFoundError(f"Corpus v2 not found at {corpus_path}. Run training/prepare_corpus_v2.py --finalize first.")
    frame = pd.read_csv(corpus_path)
    required = {"text", "category", "split", "incident_group_id", "source_type"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Corpus v2 is missing columns: {', '.join(sorted(missing))}")
    if set(frame["split"]) != {"train", "validation", "test"}:
        raise ValueError("Corpus v2 must contain train, validation, and test splits.")
    if frame.groupby("incident_group_id")["split"].nunique().max() != 1:
        raise ValueError("Corpus v2 contains incident-group leakage between splits.")
    summary = json.loads(Path(CORPUS_V2_SUMMARY_PATH).read_text(encoding="utf-8"))
    dataset_hash = hashlib.sha256(corpus_path.read_bytes()).hexdigest()
    if dataset_hash != summary.get("sha256"):
        raise ValueError("Corpus v2 hash does not match its summary metadata.")
    return frame, summary, dataset_hash


def train_category_classifier():
    print("==========================================================")
    print("       FALCON MAIL - CATEGORY MODEL TRAINING              ")
    print("==========================================================")
    frame, summary, dataset_hash = _load_corpus()
    print("Preprocessing Corpus v2 complaint text...")
    frame["processed_text"] = frame["text"].map(lambda text: preprocess_text(text)["processed_text"])
    train = frame[frame["split"] == "train"]
    validation = frame[frame["split"] == "validation"]
    test = frame[frame["split"] == "test"]

    def feature_union():
        return FeatureUnion([
            ("word", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1)),
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, min_df=2)),
        ])
    candidates = [
        ("Word TF-IDF + Logistic Regression", Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1)),
            ("clf", LogisticRegression(C=2.5, max_iter=1000, class_weight="balanced", random_state=RANDOM_SEED)),
        ])),
        ("Word+Char FeatureUnion + Logistic Regression", Pipeline([
            ("features", feature_union()),
            ("clf", LogisticRegression(C=2.5, max_iter=1000, class_weight="balanced", random_state=RANDOM_SEED)),
        ])),
        ("Word+Char FeatureUnion + Calibrated LinearSVC", Pipeline([
            ("features", feature_union()),
            ("clf", CalibratedClassifierCV(LinearSVC(C=1.0, class_weight="balanced", random_state=RANDOM_SEED))),
        ])),
    ]

    compared = {}
    trained = []
    for name, pipeline in candidates:
        print(f"Selecting candidate on validation split: {name}")
        pipeline.fit(train["processed_text"], train["category"])
        predictions = pipeline.predict(validation["processed_text"])
        values = _metrics(validation["category"], predictions)
        compared[name] = values
        trained.append((values["macro_f1"], name, pipeline))
        print(f"  Accuracy {values['accuracy']:.2%} | Macro F1 {values['macro_f1']:.4f} | Weighted F1 {values['weighted_f1']:.4f}")

    _, best_name, selected_template = max(trained, key=lambda item: item[0])
    development = pd.concat([train, validation], ignore_index=True)
    selected = clone(selected_template)
    selected.fit(development["processed_text"], development["category"])
    test_predictions = selected.predict(test["processed_text"])
    test_metrics = _metrics(test["category"], test_predictions)
    labels = [str(label) for label in selected.classes_]
    matrix = confusion_matrix(test["category"], test_predictions, labels=labels)
    per_class = _report(test["category"], test_predictions, labels)

    print(f"\nSelected: {best_name}")
    print(f"Held-out test: accuracy {test_metrics['accuracy']:.2%} | macro F1 {test_metrics['macro_f1']:.4f}")
    print(classification_report(test["category"], test_predictions, labels=labels, zero_division=0))

    model_path = Path(CATEGORY_MODEL_PATH)
    temporary_model = model_path.with_suffix(".pkl.tmp")
    joblib.dump(selected, temporary_model)
    temporary_model.replace(model_path)

    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    metadata = {
        "model_version": f"category-corpus-v2-{datetime.date.today():%Y%m%d}",
        "algorithm": best_name,
        "selection_split": "validation",
        "models_compared": compared,
        "corpus_version": str(summary.get("corpus_version", "2.0")),
        "dataset_hash": dataset_hash,
        "dataset_size": len(frame),
        "source_counts": summary.get("source_counts", {}),
        "train_size": len(train),
        "validation_size": len(validation),
        "test_size": len(test),
        "train_groups": train["incident_group_id"].nunique(),
        "validation_groups": validation["incident_group_id"].nunique(),
        "test_groups": test["incident_group_id"].nunique(),
        "group_leakage_detected": False,
        "random_seed": RANDOM_SEED,
        "python_version": sys.version.split()[0],
        "sklearn_version": sklearn.__version__,
        "training_timestamp": timestamp,
        "metrics": test_metrics,
        "per_class_metrics": per_class,
        "confusion_matrix": {"labels": labels, "values": matrix.tolist()},
        "source_metrics": _source_metrics(test, test_predictions),
    }
    _update_metadata(metadata)
    print(f"Saved model: {model_path}")
    print(f"Updated metadata: {METADATA_PATH}")
    return selected, test_metrics["accuracy"]


if __name__ == "__main__":
    train_category_classifier()
