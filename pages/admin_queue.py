"""Administrator live ticket inbox and genuine NLP trace inspector."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import streamlit as st

from config import CATEGORIES, CATEGORY_DEPARTMENT_MAP, URGENCY_LEVELS
from database.database import get_repository
from nlp.pipeline import retry_complaint_processing
from utils.auth import get_current_user
from utils.ui import render_global_header


PIPELINE_STAGES = (
    ("received", "Received"),
    ("preprocessing", "Preprocessing"),
    ("category", "Category classification"),
    ("urgency", "Urgency classification"),
    ("safety_rules", "Safety rules"),
    ("extraction", "Detail extraction"),
    ("duplicates", "Duplicate detection"),
    ("summary", "Summary"),
    ("routing", "Department routing"),
    ("persistence", "Persistence"),
)

VALID_STAGE_STATES = {"pending", "running", "completed", "failed", "skipped"}


def _text(value: Any, fallback: str = "Not available") -> str:
    value = str(value or "").strip()
    return value or fallback


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _elapsed_label(run: Optional[Dict[str, Any]]) -> str:
    if not run:
        return "No trace"
    started = _parse_timestamp(run.get("created_at"))
    if not started:
        return "Time unavailable"
    if run.get("overall_status") == "processing":
        ended = datetime.now(timezone.utc)
    else:
        ended = (
            _parse_timestamp(run.get("completed_at"))
            or _parse_timestamp(run.get("updated_at"))
            or datetime.now(timezone.utc)
        )
    seconds = max(0.0, (ended - started).total_seconds())
    if seconds < 1:
        return "<1s"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, remaining = divmod(int(seconds), 60)
    return f"{minutes}m {remaining}s"


def _queue_sort_key(item: Dict[str, Any]):
    urgency_rank = {"Critical": 0, "High": 1, "Medium": 3, "Low": 5}
    urgency = item["complaint"].get("urgency")
    run_status = _text(item.get("run", {}).get("overall_status"), "").lower()
    attention_rank = 2 if run_status in {"failed", "needs_review"} else 4
    created = _text(
        item["complaint"].get("created_at") or item.get("run", {}).get("created_at"),
        "9999",
    )
    return (urgency_rank.get(urgency, attention_rank), created)


def _load_queue(user, repo) -> List[Dict[str, Any]]:
    """Merge trace runs and unresolved tickets without duplicating ticket IDs."""
    runs = repo.list_processing_runs(actor=user, limit=100)
    unresolved = repo.get_unresolved_complaints(actor=user)
    items_by_ticket: Dict[str, Dict[str, Any]] = {}

    for run in runs:
        ticket_id = _text(run.get("ticket_id"), "")
        if not ticket_id or ticket_id in items_by_ticket:
            continue
        items_by_ticket[ticket_id] = {
            "ticket_id": ticket_id,
            "selection_id": _text(run.get("run_id"), f"ticket:{ticket_id}"),
            "run": run,
            "complaint": {},
        }

    for complaint in unresolved:
        ticket_id = _text(complaint.get("complaint_id") or complaint.get("id"), "")
        if not ticket_id:
            continue
        item = items_by_ticket.setdefault(
            ticket_id,
            {
                "ticket_id": ticket_id,
                "selection_id": f"ticket:{ticket_id}",
                "run": {},
                "complaint": {},
            },
        )
        item["complaint"] = complaint

    for ticket_id, item in items_by_ticket.items():
        if item["complaint"]:
            continue
        try:
            item["complaint"] = repo.get_complaint_by_id(ticket_id, actor=user) or {}
        except (PermissionError, ValueError):
            item["complaint"] = {}

    items = list(items_by_ticket.values())
    items.sort(key=_queue_sort_key)
    return items


def _filter_queue(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    st.markdown("### Inbox")
    search = st.text_input(
        "Search tickets",
        placeholder="Ticket ID, title, location, or reporter",
        key="admin_queue_search",
    ).strip().lower()
    filter_columns = st.columns(2)
    with filter_columns[0]:
        status_filter = st.selectbox(
            "Status",
            [
                "All",
                "Processing",
                "Completed",
                "Needs Review",
                "Failed",
                "Open",
                "In Progress",
                "Resolved",
                "Rejected",
            ],
            key="admin_queue_status_filter",
        )
    with filter_columns[1]:
        urgency_filter = st.selectbox(
            "Urgency", ["All"] + list(URGENCY_LEVELS), key="admin_queue_urgency_filter"
        )

    filtered = []
    for item in items:
        complaint = item["complaint"]
        run = item["run"]
        run_status = _text(
            run.get("overall_status") or complaint.get("processing_status") or complaint.get("status"),
            "Processing",
        )
        normalized_status = run_status.replace("_", " ").title()
        urgency = _text(complaint.get("urgency"), "Pending")
        haystack = " ".join(
            _text(value, "")
            for value in (
                item["ticket_id"],
                complaint.get("title") or run.get("title"),
                complaint.get("location") or run.get("submitted_location"),
                complaint.get("reporter_name") or run.get("reporter_name"),
            )
        ).lower()
        if search and search not in haystack:
            continue
        if status_filter != "All" and normalized_status != status_filter:
            continue
        if urgency_filter != "All" and urgency != urgency_filter:
            continue
        filtered.append(item)
    return filtered


def _render_queue_row(item: Dict[str, Any], selected: bool) -> None:
    complaint = item["complaint"]
    run = item["run"]
    ticket_id = item["ticket_id"]
    title = _text(complaint.get("title") or run.get("title"), "Untitled ticket")
    status = _text(
        run.get("overall_status") or complaint.get("processing_status") or complaint.get("status"),
        "processing",
    ).replace("_", " ").title()
    current_stage = _text(run.get("current_stage"), "Not started").replace("_", " ").title()
    urgency = _text(complaint.get("urgency"), "Pending")
    location = _text(
        complaint.get("location") or run.get("submitted_location"), "Not specified"
    )

    with st.container(border=True):
        if st.button(
            title,
            key=f"select_queue_{item['selection_id']}",
            type="primary" if selected else "secondary",
            use_container_width=True,
        ):
            st.session_state["selected_processing_run_id"] = item["selection_id"]
            st.rerun(scope="fragment")
        st.caption(f"Ticket #{ticket_id}")
        st.write(location)
        st.caption(f"{status} · {current_stage} · {_elapsed_label(run)}")
        st.write(f"Urgency: {urgency}")


def _stage_state(run: Dict[str, Any], stage_name: str) -> tuple[str, Dict[str, Any]]:
    data = (run.get("stages") or {}).get(stage_name) or {}
    state = _text(data.get("status"), "pending").lower()
    if state not in VALID_STAGE_STATES:
        state = "pending"
    return state, data


def _format_confidence(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _text(value)
    return f"{number * 100:.1f}%" if 0 <= number <= 1 else f"{number:.2f}"


def _render_trace_value(label: str, value: Any) -> None:
    if value is None or value == "" or value == {} or value == []:
        return
    st.caption(label)
    st.write(value)


def _render_pipeline(run: Optional[Dict[str, Any]]) -> None:
    st.markdown("### NLP pipeline")
    if not run:
        st.info("This ticket predates live processing traces. Its ticket controls remain available.")
        return

    overall_status = _text(run.get("overall_status"), "processing").replace("_", " ").title()
    st.caption(
        f"Run {_text(run.get('run_id'))} · {overall_status} · {_elapsed_label(run)} elapsed"
    )

    state_icon = {
        "completed": "✓",
        "running": "●",
        "failed": "!",
        "skipped": "–",
        "pending": "○",
    }
    for index, (stage_name, stage_label) in enumerate(PIPELINE_STAGES, start=1):
        state, data = _stage_state(run, stage_name)
        with st.container(
            border=True, key=f"pipeline_stage_{state}_{stage_name}"
        ):
            label_column, state_column = st.columns([0.76, 0.24])
            with label_column:
                st.markdown(f"**{state_icon[state]} {index}. {stage_label}**")
            with state_column:
                st.caption(state.title())

            if state == "running":
                st.caption("Currently processing this stage.")
                _render_trace_value("Input context", data.get("metadata"))
            elif state == "completed":
                _render_trace_value("Result", data.get("result"))
                confidence = _format_confidence(data.get("confidence"))
                if confidence:
                    st.caption(f"Confidence: {confidence}")
                duration = data.get("duration_ms")
                if duration is not None:
                    st.caption(f"Duration: {duration} ms")
                _render_trace_value("Source model or rule", data.get("model_or_rule"))
                _render_trace_value("Evidence", data.get("evidence"))
            elif state == "failed":
                st.error(_text(data.get("safe_error"), "This stage could not complete."))
                if data.get("diagnostic_code"):
                    st.caption(f"Diagnostic code: {data['diagnostic_code']}")
            elif state == "skipped":
                st.caption("This stage was not required for this ticket.")


def _select_options(current: Any, options: List[str]) -> tuple[List[str], int]:
    current_text = _text(current, "")
    values = list(dict.fromkeys(([current_text] if current_text else []) + options))
    return values, values.index(current_text) if current_text in values else 0


def _render_corrections(complaint: Dict[str, Any], user, repo) -> None:
    ticket_id = _text(complaint.get("complaint_id") or complaint.get("id"), "")
    if not ticket_id:
        return
    st.markdown("### Correct NLP fields")
    field = st.selectbox(
        "Field to correct",
        ["category", "urgency", "location", "department"],
        format_func=lambda value: value.title(),
        key=f"override_field_{ticket_id}",
    )
    current = complaint.get(field)
    if field == "category":
        options, selected = _select_options(current, list(CATEGORIES))
        new_value = st.selectbox(
            "Correct category", options, index=selected, key=f"override_value_{ticket_id}_category"
        )
    elif field == "urgency":
        options, selected = _select_options(current, list(URGENCY_LEVELS))
        new_value = st.selectbox(
            "Correct urgency", options, index=selected, key=f"override_value_{ticket_id}_urgency"
        )
    elif field == "department":
        departments = list(dict.fromkeys(CATEGORY_DEPARTMENT_MAP.values()))
        options, selected = _select_options(current, departments)
        new_value = st.selectbox(
            "Correct department", options, index=selected, key=f"override_value_{ticket_id}_department"
        )
    else:
        new_value = st.text_input(
            "Correct location",
            value=_text(current, ""),
            key=f"override_value_{ticket_id}_location",
        )
    reason = st.text_area(
        "Reason for correction",
        placeholder="Required for the audit trail",
        key=f"override_reason_{ticket_id}_{field}",
    )
    if st.button("Apply correction", key=f"override_apply_{ticket_id}"):
        if not _text(new_value, "") or not reason.strip():
            st.error("Enter a corrected value and a reason.")
        else:
            try:
                repo.override_complaint_prediction(
                    ticket_id, field, new_value, reason, actor=user
                )
                st.success(f"{field.title()} correction recorded.")
                st.rerun(scope="fragment")
            except (PermissionError, ValueError) as error:
                st.error(str(error))
            except Exception:
                st.error("Falcon Mail could not record this correction. Try again.")


def _render_operations(complaint: Dict[str, Any], user, repo) -> None:
    ticket_id = _text(complaint.get("complaint_id") or complaint.get("id"), "")
    if not ticket_id:
        return
    status = _text(complaint.get("status"), "Open")
    assigned_uid = complaint.get("assigned_admin_uid")
    assigned_name = complaint.get("assigned_admin_name")

    st.markdown("### Assignment and status")
    if not assigned_uid:
        if st.button(
            "Assign to me", key=f"assign_{ticket_id}", type="primary", use_container_width=True
        ):
            try:
                result = repo.assign_complaint(ticket_id, actor=user)
                if result.get("success"):
                    st.success("Ticket assigned to you.")
                    st.rerun(scope="fragment")
                else:
                    st.error(_text(result.get("message"), "Ticket could not be assigned."))
            except Exception:
                st.error("Falcon Mail could not assign this ticket. Try again.")
    elif assigned_uid == user.uid:
        st.info("Assigned to you")
    else:
        st.info(f"Assigned to {_text(assigned_name, 'another administrator')}")

    statuses = ["Open", "In Progress", "Resolved", "Rejected"]
    initial_status = status if status in statuses else "Open"
    with st.form(f"status_form_{ticket_id}"):
        new_status = st.selectbox(
            "Ticket status", statuses, index=statuses.index(initial_status)
        )
        resolution_note = st.text_area(
            "Resolution note",
            value=_text(complaint.get("resolution_note"), ""),
            placeholder="Required when resolving or rejecting a ticket",
        )
        update_clicked = st.form_submit_button(
            "Save status", use_container_width=True
        )
    if update_clicked:
        try:
            updated = repo.update_complaint_status(
                complaint_id=ticket_id,
                new_status=new_status,
                actor=user,
                resolution_note=resolution_note,
            )
            if updated:
                st.success(f"Ticket status changed to {new_status}.")
                st.rerun(scope="fragment")
            else:
                st.error("Ticket status could not be updated.")
        except (PermissionError, ValueError) as error:
            st.error(str(error))
        except Exception:
            st.error("Falcon Mail could not update this ticket. Try again.")


def _render_ticket_detail(item: Dict[str, Any], user, repo) -> None:
    ticket_id = item["ticket_id"]
    complaint = item["complaint"]
    run = item["run"] or None

    if run:
        latest = repo.get_processing_run(run.get("run_id"), actor=user)
        if latest is None:
            st.session_state.pop("selected_processing_run_id", None)
            st.info("This processing run is no longer available. Select another ticket.")
            return
        run = latest
    try:
        complaint = repo.get_complaint_by_id(ticket_id, actor=user) or complaint
    except (PermissionError, ValueError):
        pass

    st.markdown("### Selected ticket")
    st.write(_text(complaint.get("title") or (run or {}).get("title"), "Untitled ticket"))
    st.caption(f"Ticket #{ticket_id}")
    st.write(_text(complaint.get("description"), "Complaint text is unavailable."))

    overview = st.columns(2)
    with overview[0]:
        st.caption("Status")
        st.write(_text(complaint.get("status"), "Processing"))
        st.caption("Category")
        st.write(_text(complaint.get("category"), "Pending analysis"))
        st.caption("Location")
        st.write(
            _text(complaint.get("location") or (run or {}).get("submitted_location"), "Not specified")
        )
    with overview[1]:
        st.caption("Urgency")
        st.write(_text(complaint.get("urgency"), "Pending"))
        st.caption("Department")
        st.write(_text(complaint.get("department"), "Awaiting routing"))
        st.caption("Reporter")
        st.write(_text(complaint.get("reporter_name") or (run or {}).get("reporter_name"), "Unknown"))

    retryable = bool(
        (run or {}).get("overall_status") in {"failed", "needs_review"}
        or complaint.get("status") == "Needs Review"
        or complaint.get("needs_manual_review")
    )
    processing_finished = bool(
        (run and run.get("overall_status") in {"completed", "failed", "needs_review"})
        or (
            not run
            and (
                complaint.get("processing_status")
                in {"completed", "failed", "needs_review"}
                or complaint.get("status") not in {"Processing", None}
            )
        )
    )
    workspace_options = ["Pipeline"]
    if processing_finished:
        workspace_options.extend(["Corrections", "Operations"])
    workspace = st.segmented_control(
        "Ticket workspace",
        workspace_options,
        default="Pipeline",
        key=f"ticket_workspace_{ticket_id}",
        label_visibility="collapsed",
    ) or "Pipeline"

    if workspace == "Pipeline":
        _render_pipeline(run)
        if retryable and st.button(
            "Retry NLP processing", key=f"retry_{ticket_id}", type="primary"
        ):
            try:
                with st.spinner("Retrying the genuine NLP pipeline…"):
                    retry_complaint_processing(ticket_id, actor=user, repo=repo)
                st.success("Processing retry completed.")
                st.rerun(scope="fragment")
            except (PermissionError, ValueError) as error:
                st.error(str(error))
            except Exception:
                st.error("Falcon Mail could not retry processing. The ticket remains available for review.")
    elif workspace == "Corrections":
        _render_corrections(complaint, user, repo)
    elif workspace == "Operations":
        _render_operations(complaint, user, repo)


@st.fragment(run_every="2s")
def render_admin_queue_fragment(user, repo):
    """Poll stored state and render the administrator master-detail workspace."""
    try:
        items = _load_queue(user, repo)
    except PermissionError as error:
        st.error(str(error))
        return
    except Exception:
        st.error("Falcon Mail could not load the live inbox. Check the storage connection.")
        return

    if not items:
        st.success("No live tickets need attention.")
        st.session_state.pop("selected_processing_run_id", None)
        return

    selection_ids = {item["selection_id"] for item in items}
    selected_id = st.session_state.get("selected_processing_run_id")
    if selected_id not in selection_ids:
        selected_id = items[0]["selection_id"]
        st.session_state["selected_processing_run_id"] = selected_id

    with st.container(key="admin_inbox_layout"):
        queue_column, detail_column = st.columns([0.36, 0.64], gap="large")
        with queue_column:
            filtered = _filter_queue(items)
            st.caption(f"Showing {len(filtered)} of {len(items)} tickets")
            if not filtered:
                st.info("No tickets match these filters.")
            for item in filtered:
                _render_queue_row(item, item["selection_id"] == selected_id)

        with detail_column:
            selected = next(
                (item for item in items if item["selection_id"] == selected_id), None
            )
            if selected:
                try:
                    _render_ticket_detail(selected, user, repo)
                except PermissionError as error:
                    st.error(str(error))
                except Exception:
                    st.error("Falcon Mail could not load this ticket's details.")


def render_admin_queue_page():
    """Render the administrator-only live ticket workspace."""
    user = get_current_user()
    if not user or not user.is_admin:
        st.error("Administrator access is required to view live tickets.")
        return

    render_global_header("Live tickets")
    st.caption("Review incoming tickets and inspect each genuine NLP stage as it is stored.")
    st.markdown(
        """
        <style>
        div[class*="st-key-pipeline_stage_completed_"] {
            border-left: 4px solid #138A5B;
        }
        div[class*="st-key-pipeline_stage_running_"] {
            border-left: 4px solid #F15A24;
        }
        div[class*="st-key-pipeline_stage_failed_"] {
            border-left: 4px solid #C9362B;
        }
        div[class*="st-key-pipeline_stage_pending_"],
        div[class*="st-key-pipeline_stage_skipped_"] {
            border-left: 4px solid #CBD5E1;
        }
        @media (max-width: 900px) {
            .st-key-admin_inbox_layout [data-testid="stHorizontalBlock"] {
                flex-wrap: wrap;
            }
            .st-key-admin_inbox_layout [data-testid="column"] {
                flex: 1 1 100% !important;
                min-width: 100% !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    try:
        repo = get_repository()
    except Exception:
        st.error("Falcon Mail could not connect to ticket storage.")
        return

    render_admin_queue_fragment(user, repo)
