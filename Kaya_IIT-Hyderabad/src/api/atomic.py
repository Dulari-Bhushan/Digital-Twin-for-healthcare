"""Read and write the small JSON stores so that a reader never sees a half-written file.

`Path.write_text` truncates the file and then writes it, so a request that reads at that moment finds an empty or partial
file. The stores for uploads, messages and the diary are small JSON files that are read by one request while another thread
(for example the document reader) updates them. Writing to a temporary file and renaming it over the real one is atomic:
a reader gets either the old content or the new content, never a mixture.

On Windows a file that is open cannot be replaced, and cannot be opened while it is being replaced, so both sides retry for a
few milliseconds instead of failing. On Linux and macOS the first attempt always works.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

RETRIES = 100
PAUSE_S = 0.005


def write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{uuid.uuid4().hex[:8]}.tmp")
    try:
        tmp.write_text(text, encoding="utf8")
        for attempt in range(RETRIES):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:                       # Windows: a reader has the file open right now
                if attempt == RETRIES - 1:
                    raise
                time.sleep(PAUSE_S)
    finally:
        tmp.unlink(missing_ok=True)


def read_json(path: Path, default):
    """The parsed JSON in `path`, or `default` if the file is missing or unreadable after a few retries."""
    path = Path(path)
    for attempt in range(RETRIES):
        try:
            return json.loads(path.read_text(encoding="utf8"))
        except FileNotFoundError:
            return default
        except (PermissionError, ValueError):             # being replaced right now (Windows), or a stray bad file
            if attempt == RETRIES - 1:
                return default
            time.sleep(PAUSE_S)
        except OSError:
            return default
    return default
