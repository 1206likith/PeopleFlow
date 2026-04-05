# Repository Structure

This repo is organized as a clean, research-grade mono-repo.

## Top-Level
- `apps/` - Runtime applications (backend, Unity)
- `modules/` - Shared libraries and contracts
- `research/` - Experiments, analytics, datasets, outputs
- `infra/` - Deployment and Docker infrastructure
- `artifacts/` - Logs and archived outputs
- `docs/` - Guides, notes, and documentation

## Applications
- `apps/backend/` - FastAPI backend (API + simulation/experiments)
- `apps/unity/` - Unity project (Assets/Packages/ProjectSettings)

## Research
- `research/experiments/` - Experiment configs + outputs
- `research/analytics/` - Scripts/templates for reports

## Modules
- `modules/ai_engine/` - ML models, training pipelines
- `modules/contracts/` - JSON schemas shared across layers
