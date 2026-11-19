"""Reset the demo to a clean start: clear everything a previous demo left behind.

Run it with the server stopped, then start the server again:

    python scripts/reset_demo.py

It deletes the git-ignored folders where the demo stores what was done in the app: messages and prescriptions sent to patients,
reports patients uploaded, the patient diary (walks, medicines, how they felt) and the appointment calendar. Nothing else is touched. The server
re-creates the sample unanswered patient messages and a fresh sample week of appointments when it starts. Add --dry-run to see what would be removed.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = {
    "messages and prescriptions": ROOT / "data" / "patient_messages",
    "uploaded reports": ROOT / "data" / "patient_uploads",
    "patient diary": ROOT / "data" / "patient_logs",
    "appointment calendar": ROOT / "data" / "appointments.json",
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="show what would be removed without deleting")
    args = ap.parse_args()
    for label, folder in FOLDERS.items():
        files = ([folder] if folder.is_file() else [f for f in folder.glob("**/*") if f.is_file()]) if folder.exists() else []
        verb = "would remove" if args.dry_run else "removed"
        print(f"{label}: {verb} {len(files)} file(s) in {folder.relative_to(ROOT)}")
        if files and not args.dry_run:
            folder.unlink() if folder.is_file() else shutil.rmtree(folder)
    if not args.dry_run:
        print("Clean. Start the server; the sample patient messages are re-created on start.")


if __name__ == "__main__":
    main()
