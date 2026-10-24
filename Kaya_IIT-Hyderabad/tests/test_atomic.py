import json
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "api"))

import atomic  # noqa: E402
import messages  # noqa: E402
import uploads  # noqa: E402


def test_a_reader_never_sees_a_half_written_file(tmp_path):
    """One thread rewrites a large file over and over while another reads it: every read must be complete."""
    f = tmp_path / "store.json"
    atomic.write_text(f, json.dumps([{"i": 0, "pad": "x" * 200_000}]))
    stop = threading.Event()
    bad = []

    def write():
        i = 0
        while not stop.is_set():
            i += 1
            atomic.write_text(f, json.dumps([{"i": i, "pad": "x" * 200_000}]))

    t = threading.Thread(target=write)
    t.start()
    try:
        for _ in range(400):
            data = atomic.read_json(f, None)                                    # the same reader the stores use
            if not data or not data[0].get("pad"):                              # missing, empty or partial
                bad.append(repr(data)[:80])
    finally:
        stop.set()
        t.join()
    assert not bad, bad[:3]
    assert list(tmp_path.glob("*.tmp")) == []                                    # no temporary files are left behind


def test_the_upload_list_stays_complete_while_a_reading_updates_it(tmp_path, monkeypatch):
    """The failure seen on GitHub: listing uploads while the background reader rewrites the index returned an empty list."""
    monkeypatch.setattr(uploads, "UP_DIR", tmp_path)
    from datetime import datetime
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    m = uploads.save(5, png, "a.png", "", "other", "", datetime(2026, 1, 14, 9, 0), read=True)
    stop = threading.Event()

    def rewrite():
        n = 0
        while not stop.is_set():
            n += 1
            uploads.set_ocr(5, m["id"], state="reading", text="t" * 50_000, n=n)

    t = threading.Thread(target=rewrite)
    t.start()
    try:
        empty = sum(1 for _ in range(400) if not uploads.list_uploads(5))
    finally:
        stop.set()
        t.join()
    assert empty == 0


def test_messages_can_be_listed_while_one_is_being_added(tmp_path, monkeypatch):
    monkeypatch.setattr(messages, "MSG_DIR", tmp_path)
    messages.send(5, "advice", "t", "first", None, "2026-01-14 09:00:00")
    stop = threading.Event()

    def add():
        n = 0
        while not stop.is_set() and n < 150:
            n += 1
            messages.set_translations(5, messages.list_messages(5)[0]["id"], {"hi": {"title": "x", "body": "y" * 20_000, "instructions": []}})

    t = threading.Thread(target=add)
    t.start()
    try:
        empty = sum(1 for _ in range(300) if not messages.list_messages(5))
    finally:
        stop.set()
        t.join()
    assert empty == 0
