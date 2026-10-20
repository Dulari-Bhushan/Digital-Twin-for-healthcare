"""Reports a patient uploads themselves (a PDF or a photo of a paper report, X-ray film, prescription).

Files are checked by their first bytes (the browser's claimed type is ignored), size-limited, stored under a random id
(the original file name is kept only as a display label), and listed in the patient's record as "uploaded by the
patient, not verified" until a clinician marks them verified. Nothing is read or interpreted automatically. Stored in data/patient_uploads/ (git-ignored).
"""
from __future__ import annotations

import json
import os
import re
import threading
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UP_DIR = Path(os.environ.get("KAYA_UPLOADS", ROOT / "data" / "patient_uploads"))
MAX_BYTES = 8 * 1024 * 1024
MAX_PER_PATIENT = 30
CATEGORIES = ("blood test", "scan or x-ray", "prescription", "discharge summary", "eye report", "other")
LOCK = threading.Lock()


def sniff(b: bytes) -> tuple[str, str] | None:
    """(extension, media type) from the file's first bytes, or None if it is not a PDF or a common image."""
    if b.startswith(b"%PDF-"):
        return "pdf", "application/pdf"
    if b.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png", "image/png"
    if b.startswith(b"\xff\xd8\xff"):
        return "jpg", "image/jpeg"
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        return "webp", "image/webp"
    return None


def clean_title(s: str, fallback: str) -> str:
    s = re.sub(r"[\x00-\x1f<>]", "", s or "").strip()
    return (s or fallback)[:80]


def _meta_path(pid: int) -> Path:
    return UP_DIR / str(int(pid)) / "index.json"


def _read(pid: int) -> list[dict]:
    p = _meta_path(pid)
    try:
        return json.loads(p.read_text(encoding="utf8")) if p.exists() else []
    except (OSError, ValueError):
        return []


def list_uploads(pid: int, full: bool = False) -> list[dict]:
    items = sorted(_read(pid), key=lambda x: x["uploaded"], reverse=True)
    return items if full else [public(x) for x in items]


def save(pid: int, data: bytes, filename: str, title: str, category: str, date: str, today: datetime, read: bool = False) -> dict:
    kind = sniff(data)
    if kind is None:
        raise ValueError("Only PDF, PNG, JPEG or WebP files are accepted.")
    if len(data) > MAX_BYTES:
        raise ValueError(f"The file is larger than {MAX_BYTES // (1024 * 1024)} MB.")
    if not data:
        raise ValueError("The file is empty.")
    if category not in CATEGORIES:
        category = "other"
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        date = today.strftime("%Y-%m-%d")
    with LOCK:
        items = _read(pid)
        if len(items) >= MAX_PER_PATIENT:
            raise ValueError(f"You can keep up to {MAX_PER_PATIENT} uploaded reports. Remove one first.")
        uid = uuid.uuid4().hex[:12]
        d = UP_DIR / str(int(pid))
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{uid}.{kind[0]}").write_bytes(data)
        meta = {"id": uid, "title": clean_title(title, clean_title(Path(filename or "").stem, "Uploaded report")), "category": category, "date": date,
                "uploaded": today.strftime("%Y-%m-%d %H:%M"), "ext": kind[0], "media": kind[1], "size_kb": max(1, round(len(data) / 1024)), "verified": False,
                "ocr": {"state": "pending" if read else "off"}}
        items.append(meta)
        _meta_path(pid).write_text(json.dumps(items), encoding="utf8")
    return meta


def get_file(pid: int, uid: str) -> tuple[Path, dict] | None:
    meta = next((x for x in _read(pid) if x["id"] == uid), None)
    if meta is None:
        return None
    f = UP_DIR / str(int(pid)) / f"{meta['id']}.{meta['ext']}"
    return (f, meta) if f.exists() else None


def delete(pid: int, uid: str) -> bool:
    with LOCK:
        items = _read(pid)
        meta = next((x for x in items if x["id"] == uid), None)
        if meta is None:
            return False
        (UP_DIR / str(int(pid)) / f"{meta['id']}.{meta['ext']}").unlink(missing_ok=True)
        _meta_path(pid).write_text(json.dumps([x for x in items if x["id"] != uid]), encoding="utf8")
    return True


def set_ocr(pid: int, uid: str, **fields) -> None:
    """Update the reading state of one upload (state, results, doc_date, text, error)."""
    with LOCK:
        items = _read(pid)
        for x in items:
            if x["id"] == uid:
                x["ocr"] = {**x.get("ocr", {}), **fields}
        _meta_path(pid).write_text(json.dumps(items), encoding="utf8")


def set_verified(pid: int, uid: str, verified: bool, today: datetime) -> dict | None:
    """A clinician confirms (or withdraws the confirmation) that this upload was checked against the original document.
    Verification only changes how the file is labelled; nothing in the twin reads uploaded values either way."""
    with LOCK:
        items = _read(pid)
        meta = next((x for x in items if x["id"] == uid), None)
        if meta is None:
            return None
        meta["verified"] = bool(verified)
        meta["verified_at"] = today.strftime("%Y-%m-%d %H:%M") if verified else None
        _meta_path(pid).write_text(json.dumps(items), encoding="utf8")
    return public(meta)


def public(meta: dict) -> dict:
    """Metadata for the list view: the reading state without the full text."""
    o = dict(meta.get("ocr", {"state": "off"}))
    o.pop("text", None)
    o["results"] = len(o.get("results") or [])
    return {**meta, "ocr": o}
