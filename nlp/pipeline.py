"""Falcon Mail master NLP pipeline with persistent, privacy-safe tracing."""

import os
import sys
from typing import Any, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DEFAULT_DUPLICATE_THRESHOLD
from database.auth_context import AuthenticatedUser
from database.base_repository import BaseComplaintRepository
from database.database import get_repository
from database.identifiers import generate_complaint_id, generate_processing_run_id
from nlp.classification import predict_category
from nlp.duplicate_detection import check_duplicate_complaint, generate_embedding
from nlp.entity_extraction import extract_information
from nlp.preprocessing import preprocess_text
from nlp.summarization import generate_summary
from nlp.tracing import NullPipelineTracer, RepositoryPipelineTracer
from nlp.urgency import apply_safety_rules, predict_ml_urgency
from utils.helpers import get_recommended_department


MODEL_VERSIONS = {
    "category": "category-2026-09-12-v1",
    "urgency": "urgency-2026-09-12-v1",
    "duplicates": "sentence-transformers/all-MiniLM-L6-v2",
    "extraction": "spaCy/en_core_web_sm",
}

SAFE_PROCESSING_ERROR = (
    "Your ticket was received, but automated analysis could not finish. "
    "An administrator will review it manually."
)


def _diagnostic_code(error: Exception) -> str:
    """Map internal failures to stable codes without exposing exception details."""
    message = str(error).lower()
    if isinstance(error, FileNotFoundError) or "model" in message:
        return "MODEL_LOAD_FAILED"
    if isinstance(error, (ModuleNotFoundError, ImportError)):
        return "DEPENDENCY_UNAVAILABLE"
    if isinstance(error, (ConnectionError, TimeoutError)):
        return "STORAGE_UNAVAILABLE"
    return "NLP_PROCESSING_FAILED"


def _student_safe_duplicate(duplicate: Dict[str, Any]) -> Dict[str, Any]:
    """Remove another reporter's text and ticket identity from student output."""
    return {
        "is_duplicate": bool(duplicate.get("is_duplicate")),
        "duplicate_type": duplicate.get("duplicate_type", "none"),
        "similarity": duplicate.get("similarity", 0.0),
    }


def _manual_review_payload(
    text: str,
    complaint_id: str,
    processing_run_id: str,
    user_location: Optional[str],
    diagnostic_code: str,
) -> Dict[str, Any]:
    """Build the stable student response for retained processing failures."""
    return {
        "title": text[:80],
        "original_text": text,
        "description": text,
        "category": None,
        "category_confidence": None,
        "urgency": None,
        "final_urgency": None,
        "urgency_confidence": None,
        "location": user_location or "Campus",
        "department": None,
        "summary": SAFE_PROCESSING_ERROR,
        "complaint_id": complaint_id,
        "processing_run_id": processing_run_id,
        "status": "Needs Review",
        "processing_status": "needs_review",
        "needs_manual_review": True,
        "safe_error": SAFE_PROCESSING_ERROR,
        "diagnostic_code": diagnostic_code,
    }


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
    """Run the real NLP stages and persist observable progress when requested."""
    if not text or not text.strip():
        raise ValueError("Complaint text cannot be empty.")
    if bool(complaint_id) != bool(processing_run_id):
        raise ValueError("complaint_id and processing_run_id must be supplied together.")

    clean_text = text.strip()
    should_persist = bool(store_in_db and actor is not None)
    retrying_existing = bool(complaint_id and processing_run_id)

    if should_persist and repo is None:
        repo = get_repository()

    if should_persist:
        complaint_id = complaint_id or generate_complaint_id()
        processing_run_id = processing_run_id or generate_processing_run_id()
        if not retrying_existing:
            intake = {
                "complaint_id": complaint_id,
                "title": clean_text[:80],
                "description": clean_text,
                "category": None,
                "category_confidence": None,
                "urgency": None,
                "urgency_confidence": None,
                "department": None,
                "location": user_location or "Campus",
                "submitted_location": user_location,
                "submitted_category": user_category,
                "status": "Processing",
                "processing_status": "processing",
                "processing_run_id": processing_run_id,
                "needs_manual_review": False,
                "model_versions": MODEL_VERSIONS,
            }
            repo.create_complaint(intake, actor=actor)
            try:
                repo.create_processing_run(
                    {
                        "run_id": processing_run_id,
                        "ticket_id": complaint_id,
                        "reporter_uid": actor.uid,
                        "reporter_name": actor.full_name,
                        "title": intake["title"],
                        "submitted_location": user_location,
                    },
                    actor=actor,
                )
            except Exception as error:
                diagnostic_code = _diagnostic_code(error)
                repo.mark_complaint_needs_review(
                    complaint_id,
                    SAFE_PROCESSING_ERROR,
                    diagnostic_code,
                    actor,
                )
                return _manual_review_payload(
                    clean_text,
                    complaint_id,
                    processing_run_id,
                    user_location,
                    diagnostic_code,
                )

    tracer = (
        RepositoryPipelineTracer(repo, processing_run_id, actor)
        if should_persist and repo is not None and processing_run_id and actor is not None
        else NullPipelineTracer()
    )
    intake_exists = bool(should_persist and complaint_id and processing_run_id)
    current_stage = "received"

    try:
        tracer.start_stage("received")
        tracer.complete_stage(
            "received",
            result={"accepted": True, "ticket_id": complaint_id},
            model_or_rule="input validation",
        )

        current_stage = "preprocessing"
        tracer.start_stage(current_stage)
        preprocessed = preprocess_text(clean_text)
        tracer.complete_stage(
            current_stage,
            result={
                "input_characters": len(clean_text),
                "normalized_characters": len(preprocessed["processed_text"]),
            },
            model_or_rule="spaCy/en_core_web_sm",
            evidence={"token_count": len(preprocessed.get("tokens", []))},
        )

        current_stage = "category"
        tracer.start_stage(current_stage)
        cat_res = predict_category(clean_text)
        category = cat_res["category"]
        category_confidence = float(cat_res["confidence"])
        top_categories = sorted(
            cat_res.get("probabilities", {}).items(), key=lambda item: item[1], reverse=True
        )[:3]
        tracer.complete_stage(
            current_stage,
            result=category,
            confidence=round(category_confidence, 4),
            model_or_rule="TF-IDF + Logistic Regression",
            evidence={"top_categories": dict(top_categories)},
        )

        current_stage = "urgency"
        tracer.start_stage(current_stage)
        ml_urgency = predict_ml_urgency(clean_text)
        tracer.complete_stage(
            current_stage,
            result=ml_urgency["ml_prediction"],
            confidence=ml_urgency["ml_confidence"],
            model_or_rule="TF-IDF + Logistic Regression",
        )

        current_stage = "safety_rules"
        tracer.start_stage(current_stage)
        urg_res = apply_safety_rules(clean_text, ml_urgency)
        tracer.complete_stage(
            current_stage,
            result=urg_res["final_urgency"],
            confidence=urg_res["ml_confidence"],
            model_or_rule=(
                "deterministic safety rule" if urg_res["rule_elevated"] else "ML result retained"
            ),
            evidence={
                "rule_elevated": urg_res["rule_elevated"],
                "rule_trigger": urg_res["rule_trigger"],
            },
        )

        final_urgency = urg_res["final_urgency"]
        ml_prediction = urg_res["ml_prediction"]
        ml_confidence = float(urg_res["ml_confidence"])
        rule_elevated = bool(urg_res["rule_elevated"])
        rule_trigger = urg_res["rule_trigger"]
        decision_source = urg_res["decision_source"]

        current_stage = "extraction"
        tracer.start_stage(current_stage)
        entities = extract_information(clean_text, user_provided_location=user_location)
        extracted_result = {
            key: entities.get(key)
            for key in ("location", "building", "room", "date", "time", "person", "org")
            if entities.get(key) is not None
        }
        tracer.complete_stage(
            current_stage,
            result=extracted_result,
            model_or_rule="spaCy NER + campus patterns",
            evidence={"resolved_location": entities.get("location")},
        )

        current_stage = "duplicates"
        tracer.start_stage(current_stage)
        embedding = generate_embedding(clean_text)
        candidate_records = []
        if repo is not None:
            system_actor = actor or AuthenticatedUser(
                uid="system",
                email="system@falcon-mail.local",
                full_name="Falcon Mail System",
                role="admin",
            )
            candidate_records = repo.get_duplicate_candidates(actor=system_actor, limit=50)
        dup_res = check_duplicate_complaint(
            clean_text,
            candidate_records,
            threshold=duplicate_threshold,
            new_category=category,
            new_location=entities.get("location"),
        )
        tracer.complete_stage(
            current_stage,
            result={
                "is_duplicate": dup_res.get("is_duplicate"),
                "duplicate_type": dup_res.get("duplicate_type"),
                "similarity": dup_res.get("similarity"),
                "matched_id": dup_res.get("matched_id"),
            },
            confidence=dup_res.get("similarity"),
            model_or_rule="all-MiniLM-L6-v2 + multi-signal rules",
            evidence={
                "candidate_count": len(candidate_records),
                "threshold": duplicate_threshold,
            },
        )

        student_dup_notice = None
        if dup_res.get("is_duplicate"):
            student_dup_notice = "A related active incident may already exist."

        current_stage = "summary"
        tracer.start_stage(current_stage)
        summary = generate_summary(clean_text, category, final_urgency, entities)
        tracer.complete_stage(
            current_stage,
            result=summary,
            model_or_rule="deterministic operational template",
        )

        current_stage = "routing"
        tracer.start_stage(current_stage)
        rec_dept = get_recommended_department(category)
        tracer.complete_stage(
            current_stage,
            result=rec_dept,
            model_or_rule="category-to-department routing map",
            evidence={"category": category},
        )

        duplicate_for_response = (
            dup_res if actor is None or actor.is_admin else _student_safe_duplicate(dup_res)
        )
        payload = {
            "title": entities.get("issue") or (
                clean_text[:60] + "..." if len(clean_text) > 60 else clean_text
            ),
            "original_text": clean_text,
            "description": clean_text,
            "processed_text": preprocessed["processed_text"],
            "category": category,
            "category_confidence": round(category_confidence, 4),
            "user_category": user_category,
            "urgency": final_urgency,
            "final_urgency": final_urgency,
            "urgency_confidence": round(ml_confidence, 4),
            "ml_prediction": ml_prediction,
            "ml_confidence": round(ml_confidence, 4),
            "rule_elevated": rule_elevated,
            "rule_trigger": rule_trigger,
            "decision_source": decision_source,
            "entities": entities,
            "location": entities.get("location", "Campus"),
            "user_location": user_location,
            "building": entities.get("building"),
            "room": entities.get("room"),
            "issue": entities.get("issue"),
            "summary": summary,
            "recommended_department": rec_dept,
            "department": rec_dept,
            "duplicate": duplicate_for_response,
            "student_dup_notice": student_dup_notice,
            "dense_embedding": embedding.tolist() if hasattr(embedding, "tolist") else embedding,
            "duplicate_of_id": dup_res.get("matched_id") if dup_res.get("is_duplicate") else None,
            "duplicate_similarity": (
                dup_res.get("similarity") if dup_res.get("is_duplicate") else 0.0
            ),
            "status": "Open",
            "complaint_id": complaint_id,
            "processing_run_id": processing_run_id,
            "processing_status": "completed",
            "model_versions": MODEL_VERSIONS,
        }

        current_stage = "persistence"
        tracer.start_stage(current_stage)
        if should_persist and repo is not None and actor is not None and complaint_id:
            repo.finalize_complaint_analysis(complaint_id, payload, actor=actor)
        tracer.complete_stage(
            current_stage,
            result={"ticket_id": complaint_id, "status": "Open"},
            model_or_rule="repository persistence",
        )
        tracer.complete_run(payload)
        if actor is not None and not actor.is_admin:
            payload["duplicate_of_id"] = None
        return payload

    except Exception as error:
        if not intake_exists or repo is None or actor is None or not complaint_id:
            raise

        diagnostic_code = _diagnostic_code(error)
        try:
            tracer.fail_stage(current_stage, SAFE_PROCESSING_ERROR, diagnostic_code)
        except Exception:
            pass
        repo.mark_complaint_needs_review(
            complaint_id,
            SAFE_PROCESSING_ERROR,
            diagnostic_code,
            actor,
        )
        try:
            tracer.fail_run(SAFE_PROCESSING_ERROR, diagnostic_code)
        except Exception:
            pass
        return _manual_review_payload(
            clean_text,
            complaint_id,
            processing_run_id,
            user_location,
            diagnostic_code,
        )


def retry_complaint_processing(
    complaint_id: str,
    actor: AuthenticatedUser,
    repo: BaseComplaintRepository,
) -> Dict[str, Any]:
    """Retry a failed ticket in place while preserving its prior trace attempt."""
    if not actor or not actor.is_admin:
        raise PermissionError("Access Denied: Admin privileges required to retry processing.")

    complaint = repo.get_complaint_by_id(complaint_id, actor)
    if not complaint:
        raise ValueError(f"Complaint '{complaint_id}' was not found.")
    run_id = complaint.get("processing_run_id")
    if not run_id:
        raise ValueError("Complaint has no processing run to retry.")
    run = repo.get_processing_run(run_id, actor)
    if not run:
        # Recover an intake whose ticket write succeeded but whose original trace
        # document could not be created. The ticket and run identities stay stable.
        repo.create_processing_run(
            {
                "run_id": run_id,
                "ticket_id": complaint_id,
                "reporter_uid": complaint.get("reporter_uid"),
                "reporter_name": complaint.get("reporter_name"),
                "title": complaint.get("title"),
                "submitted_location": complaint.get("submitted_location"),
            },
            actor,
        )
        run = repo.get_processing_run(run_id, actor)
    if not run:
        raise ValueError(f"Processing run '{run_id}' could not be recovered.")

    attempt_history = list(run.get("attempt_history", []))
    attempt_history.append({
        "attempt": int(run.get("retry_count", 0)),
        "stages": run.get("stages", {}),
        "overall_status": run.get("overall_status"),
        "safe_error": run.get("safe_error"),
        "diagnostic_code": run.get("diagnostic_code"),
        "created_at": run.get("created_at"),
        "updated_at": run.get("updated_at"),
        "completed_at": run.get("completed_at"),
    })
    repo.finish_processing_run(
        run_id,
        "processing",
        {
            "current_stage": "received",
            "stages": {},
            "retry_count": int(run.get("retry_count", 0)) + 1,
            "attempt_history": attempt_history,
            "safe_error": None,
            "diagnostic_code": None,
        },
        actor,
    )

    return process_complaint(
        text=complaint.get("description") or complaint.get("original_text") or "",
        actor=actor,
        repo=repo,
        store_in_db=True,
        user_location=complaint.get("submitted_location") or complaint.get("location"),
        user_category=complaint.get("submitted_category") or complaint.get("user_category"),
        complaint_id=complaint_id,
        processing_run_id=run_id,
    )
