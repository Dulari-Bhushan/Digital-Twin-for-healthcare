# Kaya: A Multi-Organ Digital Twin for Type 2 Diabetes

The full project README (team, problem, use case, novelties, models and results, stack, demo video, license) is at the [repository root](../README.md).

## Run it

You are in the right folder. Pick one way:

**Docker** (install [Docker Desktop](https://www.docker.com/products/docker-desktop/) first)

```bash
docker compose up --build
```

**Python 3.11 or newer**

```bash
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements-api.txt
uvicorn app:app --app-dir src/api --port 8000
```

Then open **<http://localhost:8000>**. No GPU, no data download, no account needed. Direct links to every screen, the optional voice key and fixes for common problems are in [section 10 of the main README](../README.md#10-run-it).
