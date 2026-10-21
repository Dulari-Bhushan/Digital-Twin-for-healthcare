import os

# Tests write to the real log folder through the API; never let a test run clear a developer's demo entries.
os.environ.setdefault("KAYA_KEEP_LOGS", "1")
