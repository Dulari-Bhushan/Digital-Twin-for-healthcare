"""Patient-uploaded reports: content sniffing, limits, storage, and the API."""
import io
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "api"))

import uploads  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
NOW = datetime(2026, 1, 14, 21, 50)


def _pdf() -> bytes:
    from reportlab.pdfgen import canvas

    b = io.BytesIO()
    c = canvas.Canvas(b)
    c.drawString(72, 720, "lab report")
    c.save()
    return b.getvalue()


@pytest.mark.parametrize("data,ext", [(_pdf(), "pdf"), (PNG, "png"), (b"\xff\xd8\xff\xe0" + b"0" * 20, "jpg"), (b"RIFF\x00\x00\x00\x00WEBPVP8 ", "webp")])
def test_sniff_accepts_pdf_and_images(data, ext):
    assert uploads.sniff(data)[0] == ext


@pytest.mark.parametrize("data", [b"<html><script>alert(1)</script>", b"MZ\x90\x00", b"#!/bin/sh\nrm -rf /", b"GIF89a....", b""])
def test_sniff_rejects_everything_else(data):
    assert uploads.sniff(data) is None


def test_save_list_get_delete(tmp_path, monkeypatch):
    monkeypatch.setattr(uploads, "UP_DIR", tmp_path)
    m = uploads.save(7, _pdf(), "../../evil name.pdf", "  Blood <b>test</b>  ", "blood test", "2026-01-05", NOW)
    assert m["ext"] == "pdf" and m["verified"] is False and "<" not in m["title"]
    f, meta = uploads.get_file(7, m["id"])
    assert f.parent == tmp_path / "7" and f.name == f"{m['id']}.pdf"        # stored under a random id, never the client's file name
    assert [x["id"] for x in uploads.list_uploads(7)] == [m["id"]]
    assert uploads.delete(7, m["id"]) and not f.exists() and not uploads.delete(7, m["id"])


def test_limits_and_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(uploads, "UP_DIR", tmp_path)
    with pytest.raises(ValueError):
        uploads.save(7, b"not a report", "x.pdf", "", "other", "", NOW)
    with pytest.raises(ValueError):
        uploads.save(7, PNG + b"0" * (uploads.MAX_BYTES + 1), "big.png", "", "other", "", NOW)
    m = uploads.save(7, PNG, "scan.png", "", "weird category", "not a date", NOW)
    assert m["category"] == "other" and m["date"] == "2026-01-14" and m["title"] == "scan"
    monkeypatch.setattr(uploads, "MAX_PER_PATIENT", 2)
    uploads.save(7, PNG, "b.png", "", "other", "", NOW)
    with pytest.raises(ValueError):
        uploads.save(7, PNG, "c.png", "", "other", "", NOW)
