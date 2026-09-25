"""Shared identifier generators for Falcon Mail records."""

import uuid


def generate_complaint_id() -> str:
    """Return a public complaint identifier in ``CMP-XXXXXXXX`` format."""
    return f"CMP-{uuid.uuid4().hex[:8].upper()}"


def generate_processing_run_id() -> str:
    """Return a processing trace identifier in ``RUN-XXXXXXXXXX`` format."""
    return f"RUN-{uuid.uuid4().hex[:10].upper()}"
