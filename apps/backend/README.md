# Backend Setup

## One-command setup (Windows)

From repository root:

```bat
cd apps\backend
setup_backend.bat
```

This will:
- create `apps/backend/.venv` (if missing)
- upgrade pip tooling
- install `apps/backend/requirements.txt`
- create root `.env` from `infra/deployment/environment.example.env` (if missing)

## Manual setup

From repository root:

```bash
python -m venv apps/backend/.venv
apps/backend/.venv/Scripts/python -m pip install --upgrade pip setuptools wheel
apps/backend/.venv/Scripts/python -m pip install -r apps/backend/requirements.txt
copy infra\deployment\environment.example.env .env
```

## Run backend

```bat
apps\backend\.venv\Scripts\activate
cd apps\backend
python -m uvicorn app.main:app --reload --port 8000
```

Docs: `http://127.0.0.1:8000/api/v2/docs`
OpenAPI: `http://127.0.0.1:8000/api/v2/openapi.json`

## Journal Artifact Generation

From `apps/backend`:

```bat
python app/experiments/generate_journal_results.py
python app/experiments/runtime_scalability_probe.py
python app/experiments/blocked_exit_comparison_probe.py
python app/experiments/ingestion_timing_probe.py
python app/experiments/generate_alpha_beta_sensitivity_figure.py
python app/experiments/generate_multimedia_supplement.py
```

Outputs are written primarily to `Research_Paper_IEEE/`.
