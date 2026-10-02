"""Fetch the pinned external input used by Falcon Mail Corpus v2."""

from __future__ import annotations

import csv
import hashlib
import os
import sys
import tempfile
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import EXTERNAL_RAW_DIR


REVISION = "3a21d7a28cca2dad1ced731246772810798215f7"
BASE_URL = (
    "https://huggingface.co/datasets/alaminxpro/"
    f"university-students-complaints/resolve/{REVISION}"
)
FILES = {
    "train.csv": "42827688fea7e114ce61cf7b72a20cec7ba8b31de3c0ca3c59a50415aa7229fe",
    "test.csv": "b62b5b334389e9171f6d819ca80d98f72aa593a5a3f5d0b4738398f9aa409aaa",
}
REQUIRED_COLUMNS = {
    "ID",
    "Complaint_Description",
    "Category",
    "Primary_Department",
    "Aspects",
    "Severity",
    "Complaint_Group_ID",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate(path: Path, expected_hash: str) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"Downloaded file is missing or empty: {path.name}")
    if _sha256(path) != expected_hash:
        raise ValueError(f"SHA-256 mismatch for {path.name}; source revision may have changed")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        columns = set(next(csv.reader(handle), []))
    missing = REQUIRED_COLUMNS - columns
    if missing:
        raise ValueError(f"{path.name} is missing columns: {', '.join(sorted(missing))}")


def fetch() -> None:
    destination = Path(EXTERNAL_RAW_DIR)
    destination.mkdir(parents=True, exist_ok=True)
    for filename, expected_hash in FILES.items():
        target = destination / filename
        if target.exists():
            _validate(target, expected_hash)
            print(f"Already verified: {target}")
            continue

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f"{filename}.", suffix=".download", dir=destination
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            urllib.request.urlretrieve(f"{BASE_URL}/{filename}?download=true", temporary)
            _validate(temporary, expected_hash)
            temporary.replace(target)
            print(f"Downloaded and verified: {target}")
        finally:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    fetch()
