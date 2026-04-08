# PeopleFlow - AI-Powered Emergency Evacuation Simulator

PeopleFlow simulates evacuation dynamics under hazards using AI-driven agents, pathfinding, and real-time analytics.

## Project Overview
- 3D Unity simulation with ML-Agents (optional)
- Research-grade behavioral and movement models
- Real-time analytics and reporting
- REST + WebSocket APIs
- Auth-free single-tenant API with admin-key mutation guard

## Architecture
Backend (FastAPI) <-> Unity (WebSocket)
Frontend (React + Vite) <-> Backend (REST + WebSocket)

## Project Structure
PeopleFlow/
- modules/contracts/                   Shared JSON schemas
- apps/backend/app/sim/                Research-grade simulation core
- apps/backend/app/experiments/        Experiment runner + configs
- apps/backend/app/validation/         Validation and benchmark utilities
- apps/unity/                          Unity visualization
- research/experiments/output/*.json   Experiment outputs
- artifacts/experiments/output/index.json             Experiment index
- research/experiments/output/metrics.csv            Metrics export

See `docs/STRUCTURE.md` for a full layout map.

## Quick Start
One click on Windows:
- Double-click `start_peopleflow.bat`
- Or run `.\start_peopleflow.ps1`

This starts the backend and frontend in separate windows, skips services that are already running, and opens the frontend at `http://127.0.0.1:4173/`.
The launcher also writes the resolved frontend/backend URLs to `.peopleflow-launch.json`, which is especially useful if it had to fall back to alternate ports.

Useful launcher options:
- `.\start_peopleflow.ps1 -NoBrowser`
- `.\start_peopleflow.ps1 -OpenPath /simulation`
- `.\start_peopleflow.bat -BackendPort 8002 -FrontendPort 4175`

## Launch Demo
[![Launch Demo](https://img.shields.io/badge/Launch-Demo-2E7D32?style=for-the-badge)](http://127.0.0.1:4173/simulation)

After starting PeopleFlow, open `http://127.0.0.1:4173/simulation` to enter the interactive demo route directly.

Backend:
- pip install -r requirements.txt
- cp infra/deployment/environment.example.env .env
- cd apps/backend
- python -m uvicorn app.main:app --reload --port 8000

Optional backend ML extras:
- `apps/backend/setup_backend_ml.bat`
- Installs PyTorch + YOLO-compatible extras from `apps/backend/requirements-ml.txt`
- Detectron2 remains best-effort and may require Linux/WSL or a pinned wheel/toolchain

API docs: `/api/v2/docs`
OpenAPI schema: `/api/v2/openapi.json`

## API Security Model
- Authentication routes are removed.
- Read endpoints are open.
- Mutation endpoints under `/api/v2/*` require `X-Admin-Key`.
- Unity mutation websocket `/ws/unity/{simulation_id}` requires `admin_key` query param.

## Runtime Modes
- `APP_MODE=production`: MongoDB is required and startup fails fast if unavailable.
- `APP_MODE=demo`: in-memory deterministic mode; v2 responses return `meta.mode = "demo"`.

## Shared Contracts
The canonical payload definitions live in modules/contracts/ and are used by backend, client tools, and Unity.

## Experiments
- Run a baseline: `python -m app.experiments.cli --config research/experiments/baseline.json --validate`
- Run ablations: `python -m app.experiments.cli --config research/experiments/baseline.json --ablation --validate`
- Run calibration: `python -m app.experiments.cli --config research/experiments/baseline.json --calibrate --calibration-config research/experiments/calibration.json`
- Run optimization: `python -m app.experiments.cli --config research/experiments/baseline.json --optimize --optimization-config research/experiments/optimization.json`

## Journal Reproducibility (PeopleFlow Paper)
From repository root:

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19432157.svg)](https://doi.org/10.5281/zenodo.19432157)

All plots, tables, and ETH validation metrics can be regenerated using the provided CLI pipeline.

1) Generate the core + supplementary matrix statistics (450 + 90 runs):
- `cd apps/backend`
- `python app/experiments/generate_journal_results.py`

2) Generate runtime/scalability evidence tables:
- `python app/experiments/runtime_scalability_probe.py`

3) Generate blocked-exit policy comparison evidence:
- `python app/experiments/blocked_exit_comparison_probe.py`

4) Generate floor-plan ingestion timing evidence:
- `python app/experiments/ingestion_timing_probe.py`

5) Generate alpha/beta sensitivity figure:
- `python app/experiments/generate_alpha_beta_sensitivity_figure.py`

6) Generate 30-second multimedia supplement (pipeline + simulation + analytics):
- `python app/experiments/generate_multimedia_supplement.py`

Primary paper outputs are written to `Research_Paper_IEEE/`, including:
- `journal_results_stats.csv`
- `runtime_scalability_summary.csv`
- `blocked_exit_policy_comparison.csv`
- `ingestion_timing.csv`
- `fig_alpha_beta_sensitivity.png`
- `supplementary/peopleflow_multimedia_supplement.mp4`

