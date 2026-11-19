import os

# Tests write to the real log folder through the API; never let a test run clear a developer's demo entries.
os.environ.setdefault("KAYA_KEEP_LOGS", "1")

# Tests never call the real Gemini service; the ones that need a client use a fake.
os.environ.setdefault("GEMINI_API_KEY", "")

# The calendar tests and every other test use a throw-away appointment file, never the demo calendar.
import tempfile
os.environ.setdefault("KAYA_APPOINTMENTS", os.path.join(tempfile.mkdtemp(), "appointments.json"))
