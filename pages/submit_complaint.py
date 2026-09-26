"""Student ticket submission flow for Falcon Mail."""

import streamlit as st

from config import CATEGORIES, DEFAULT_DUPLICATE_THRESHOLD
from nlp.pipeline import process_complaint
from utils.ui import render_global_header


def render_submit_complaint_page() -> None:
    """Render the student form, review, or submission-result state."""
    render_global_header("Raise a ticket")
    last_result = st.session_state.get("last_submission_result")
    if last_result:
        render_submission_result_view(last_result)
        return

    draft = st.session_state.get("ticket_draft") or {}
    if st.session_state.get("ticket_reviewing") and draft:
        render_ticket_review(draft)
    else:
        render_ticket_form()


def render_ticket_form() -> None:
    """Collect a ticket draft without invoking the NLP pipeline."""
    st.markdown("## What can we help with?")
    st.caption(
        "Describe what happened and include a room, block, or campus area when you can."
    )
    draft = st.session_state.get("ticket_draft") or {}

    with st.container(key="ticket_form_shell"):
        with st.form("ticket_form", clear_on_submit=False):
            description = st.text_area(
                "What happened?",
                value=str(draft.get("description") or ""),
                height=180,
                placeholder="Describe the issue, when it started, and how it affects you.",
            )
            location = st.text_input(
                "Where did it happen? (optional)",
                value=str(draft.get("location") or ""),
                placeholder="For example: Room 206, Block A",
            )
            category_options = ["Let Falcon Mail choose"] + list(CATEGORIES)
            previous_category = draft.get("category")
            selected_index = (
                category_options.index(previous_category)
                if previous_category in category_options
                else 0
            )
            category = st.selectbox(
                "Category context (optional)",
                category_options,
                index=selected_index,
                help="This provides context; Falcon Mail still analyzes the ticket text.",
            )
            review_clicked = st.form_submit_button(
                "Review ticket", type="primary", use_container_width=True
            )

    if review_clicked:
        clean_description = description.strip()
        if not clean_description:
            st.error("Describe the issue before reviewing your ticket.")
            return
        st.session_state["ticket_draft"] = {
            "description": clean_description,
            "location": location.strip() or None,
            "category": category if category != "Let Falcon Mail choose" else None,
        }
        st.session_state["ticket_reviewing"] = True
        st.rerun()


def render_ticket_review(draft: dict) -> None:
    """Confirm only student-entered fields; no analysis happens here."""
    st.markdown("## Review your ticket")
    st.caption(
        "Check the details below. Falcon Mail has not sent or analyzed this ticket yet."
    )

    with st.container(key="ticket_review_shell"):
        with st.container(border=True):
            st.markdown("**What happened?**")
            st.write(str(draft.get("description") or ""))
            st.markdown("**Where it happened**")
            st.write(str(draft.get("location") or "Not specified"))
            st.markdown("**Category context**")
            st.write(str(draft.get("category") or "Let Falcon Mail choose"))

        edit_column, send_column = st.columns(2)
        with edit_column:
            if st.button(
                "Edit",
                use_container_width=True,
                disabled=st.session_state.get("ticket_submitting", False),
            ):
                st.session_state["ticket_reviewing"] = False
                st.rerun()
        with send_column:
            send_clicked = st.button(
                "Send ticket",
                type="primary",
                use_container_width=True,
                disabled=st.session_state.get("ticket_submitting", False),
            )

    if send_clicked and not st.session_state.get("ticket_submitting", False):
        st.session_state["ticket_submitting"] = True
        status = st.status("Sending and analyzing your ticket…", expanded=True)
        try:
            result = submit_reviewed_ticket(draft)
            status.update(label="Ticket received", state="complete", expanded=False)
            st.session_state["last_submission_result"] = result
            st.session_state["ticket_draft"] = None
            st.session_state["ticket_reviewing"] = False
            st.rerun()
        except Exception:
            status.update(label="Ticket not sent", state="error", expanded=False)
            st.error(
                "Falcon Mail could not send the ticket. Check your connection and try again."
            )
        finally:
            st.session_state["ticket_submitting"] = False


def submit_reviewed_ticket(draft: dict) -> dict:
    """Run the genuine NLP pipeline once for an explicitly confirmed draft."""
    from utils.auth import get_current_user

    actor = get_current_user()
    if actor is None:
        raise PermissionError("Sign in before sending a ticket.")
    return process_complaint(
        text=str(draft.get("description") or "").strip(),
        actor=actor,
        store_in_db=True,
        duplicate_threshold=DEFAULT_DUPLICATE_THRESHOLD,
        user_location=draft.get("location"),
        user_category=draft.get("category"),
    )


def render_submission_result_view(result: dict) -> None:
    """Show a concise, privacy-safe ticket outcome to the student."""
    ticket_id = str(result.get("complaint_id") or "Unavailable")
    needs_review = bool(
        result.get("needs_manual_review")
        or result.get("processing_status") == "needs_review"
    )

    with st.container(key="ticket_result_shell"):
        if needs_review:
            st.warning("Ticket received — needs staff review")
            st.markdown(f"### Ticket `{ticket_id}`")
            st.write(
                "Automatic analysis could not finish, but your ticket is saved and visible to staff."
            )
            st.caption(
                f"Submitted location: {result.get('location') or 'Not specified'}"
            )
        else:
            st.success("Ticket received")
            st.markdown(f"### Ticket `{ticket_id}`")
            category = str(result.get("category") or "Pending analysis")
            urgency = str(result.get("urgency") or "Pending")
            location = str(
                result.get("location")
                or (result.get("entities") or {}).get("location")
                or "Not specified"
            )
            department = str(
                result.get("recommended_department")
                or result.get("department")
                or "Awaiting routing"
            )
            first, second = st.columns(2)
            with first:
                st.markdown("**Category**")
                st.write(category)
                st.markdown("**Location**")
                st.write(location)
            with second:
                st.markdown("**Urgency**")
                st.write(urgency)
                st.markdown("**Sent to**")
                st.write(department)
            if result.get("student_dup_notice"):
                st.info(str(result["student_dup_notice"]))

        another_column, tickets_column = st.columns(2)
        with another_column:
            if st.button("Raise another ticket", use_container_width=True):
                st.session_state["last_submission_result"] = None
                st.session_state["ticket_draft"] = None
                st.session_state["ticket_reviewing"] = False
                st.rerun()
        with tickets_column:
            if st.button(
                "Go to My tickets", type="primary", use_container_width=True
            ):
                st.session_state["last_submission_result"] = None
                st.session_state["nav_page"] = "My tickets"
                st.rerun()
