# PeopleFlow Project Notes for AI Paper Writing

These notes are meant to give an AI writing assistant the right factual framing for the current PeopleFlow repository. The goal is to help the writer produce a credible IEEE-style research paper draft that matches the system as it exists today, without drifting into claims the evidence does not yet support.

## 1. What PeopleFlow Is

PeopleFlow is a floor-plan-aware evacuation simulation platform with:

- floor-plan upload and processing
- manual correction of exits and geometry through a browser designer
- live browser-based evacuation simulation
- replay and analytics linked to the same simulation session
- experiment execution and artifact-backed reporting

At a high level, the system is best described as a **simulation-based safety assessment and decision-support framework** for building evacuation analysis.

It is **not** best framed as:

- a finished state-of-the-art reinforcement learning paper
- a mathematically complete proof-of-safety system
- a fully validated hazard-physics simulator for every emergency type

## 2. Recommended Paper Framing

The strongest paper direction for the current project is:

**Simulation-based safety assessment of building evacuation using floor-plan-aware crowd modeling**

This framing is strong because the repo currently supports:

- floor-plan ingestion and geometry extraction
- scenario-based evacuation simulation
- session replay and analytics
- reproducible experiment runs with stored artifacts
- calibration and optimization workflows

The paper should argue that PeopleFlow helps **assess evacuation safety through simulation-backed evidence** such as:

- evacuation time
- clearance time
- crowd-density hotspots
- bottleneck persistence
- exit load balance
- scenario resilience under blocked exits or higher occupancy

The paper should **not** argue that PeopleFlow:

- guarantees real-world safety
- proves a building is safe in all conditions
- has already demonstrated definitive superiority over prior evacuation systems

## 3. One-Sentence Project Description

PeopleFlow converts floor plans into simulation-ready evacuation environments, runs reproducible emergency scenarios, and reports interpretable safety indicators that help identify safer building layouts, evacuation strategies, and operational interventions.

## 4. Current System Architecture

### Backend

Main backend stack:

- FastAPI application
- REST APIs and WebSocket support
- SQLite in demo/development usage, with production-oriented modes available

Important backend areas:

- simulation v2/v3 routes: [simulation_v3.py](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/api/routes/simulation_v3.py)
- simulation services: [simulation_session_service.py](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/services/simulation_session_service.py), [simulation_projection_service.py](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/services/simulation_projection_service.py), [simulation_session_repository.py](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/services/simulation_session_repository.py)
- research/simulation engine area: [simulation_kernel.py](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/sim/simulation_kernel.py), [core_engine.py](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/sim/core_engine.py)
- floor-plan processing: [simulation_upload_service.py](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/services/simulation_upload_service.py), [semantic_floorplan.py](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/services/semantic_floorplan.py), [floor_plan_processor.py](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/services/floor_plan_processor.py), [structural_graph.py](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/services/structural_graph.py)
- experiments: [experiment_execution.py](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/api/routes/experiment_execution.py), [experiment_execution_service.py](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/services/experiment_execution_service.py), [experiment_artifact_service.py](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/services/experiment_artifact_service.py), [experiment_job_service.py](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/services/experiment_job_service.py)

### Frontend

Main frontend stack:

- React + Vite
- browser-first interface
- session-based simulation studio

Important frontend areas:

- simulation studio: [SimulationHubPage.tsx](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/frontend/src/features/simulation/SimulationHubPage.tsx)
- 2D/3D rendering: [SimulationCanvas2D.tsx](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/frontend/src/features/simulation/SimulationCanvas2D.tsx), [SimulationCanvas3D.tsx](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/frontend/src/features/simulation/SimulationCanvas3D.tsx)
- timeline and controls: [TimelineStrip.tsx](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/frontend/src/features/simulation/TimelineStrip.tsx), [SimulationControls.tsx](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/frontend/src/features/simulation/SimulationControls.tsx)
- designer: [DesignerPage.tsx](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/frontend/src/features/designer/DesignerPage.tsx), [FloorPlanPreviewCanvas.tsx](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/frontend/src/features/designer/FloorPlanPreviewCanvas.tsx), [ExitConfigPanel.tsx](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/frontend/src/features/designer/ExitConfigPanel.tsx)
- experiments dashboard: [ExperimentsPage.tsx](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/frontend/src/features/experiments/ExperimentsPage.tsx)
- API layer: [simulationSessions.ts](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/frontend/src/lib/api/simulationSessions.ts), [experiments.ts](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/frontend/src/lib/api/experiments.ts), [types.ts](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/frontend/src/lib/api/types.ts)

## 5. What the Current Workflow Looks Like

The most important end-to-end workflow in the repo is:

1. upload a floor plan
2. extract walls, exits, and obstacles
3. inspect and adjust geometry in the designer
4. create a simulation session
5. run emergency scenarios in the browser studio
6. review live analytics, replay, and artifacts
7. compare scenarios or launch experiment workflows

This workflow is stronger for paper writing than older descriptions centered only on Unity or reinforcement learning.

## 6. APIs and Research-Relevant Endpoints

### Floor-plan and simulation preparation

- `POST /api/v2/simulations/upload`

### Canonical simulation session API

- `POST /api/v3/simulation/sessions`
- `GET /api/v3/simulation/sessions`
- `GET /api/v3/simulation/sessions/{id}`
- `POST /api/v3/simulation/sessions/{id}/control`
- `GET /api/v3/simulation/sessions/{id}/analysis`
- `GET /api/v3/simulation/sessions/{id}/replay`
- WebSocket session channel: `/ws/{session_id}` or related live session path in the frontend runtime

### Experiment and artifact endpoints

- `POST /api/v2/experiments/runs`
- `GET /api/v2/experiments/jobs`
- `GET /api/v2/experiments/artifacts`

For the paper, the simulation session API is especially important because it supports the idea of:

- reproducible configuration snapshots
- live session monitoring
- replayable results
- linked analytics

## 7. Key Capabilities That Are Safe to Describe

These claims are aligned with the current system:

- PeopleFlow can upload and process floor plans into simulation-ready geometry.
- The system supports manual correction of exits in the designer.
- The simulation workflow is session-based and supports live control, replay, and linked analysis.
- The frontend provides a browser-first 2D/3D simulation studio.
- The experiments subsystem supports reproducible runs, calibration, optimization, and artifact storage.
- The project includes hazard-oriented scenario presets such as fire, earthquake, flood, gas leak, and blast-style disruption.
- The system can be used to compare evacuation scenarios rather than rely on a single run.

## 8. Claims That Need Caution

These should be written carefully:

- “Validated against reality”
- “Research-grade”
- “Multi-hazard”
- “Adaptive guidance optimization”
- “Behaviorally realistic”
- “Survival probability”

These are best described as:

- implemented capabilities
- supported workflows
- preliminary calibration-backed features
- decision-support components

They should not automatically be described as fully validated scientific contributions unless the paper includes direct evidence for them.

## 9. Strong Evidence Available in the Repo

### Reproduced paper case-study bundle

The strongest paper-specific bundle currently prepared for writing is:

- [paper_case_studies.json](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/experiments/output/paper_case_studies.json)
- [paper_case_studies.csv](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/experiments/output/paper_case_studies.csv)

This bundle was generated from:

- [generate_paper_assets.py](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/experiments/generate_paper_assets.py)

Important notes:

- the case-study bundle is stronger for the current manuscript than the older benchmark output files
- the reported terminal time is an **operational clearance time** tied to the current 95\% completion rule in the kernel
- Case C is based on a real uploaded floor plan stored in SQLite, but its geometry is normalized by a scale factor for practical simulation-space use
- the paper figures in the same folder are generated assets, not hand-drawn placeholders

### Calibration evidence

The most credible current validation-oriented artifact is:

- [calibration_summary.json](/l:/Likith/Coding_Projects/Python/PeopleFlow/research/experiments/output/calibration_summary.json)

Key points:

- 10 calibration trials
- best validation score is about `0.5845`
- includes explicit parameter overrides and reproducibility metadata

This is useful in the paper as:

- evidence of a calibration workflow
- evidence of parameter search against empirical targets
- support for interpretability and tuning

### Optimization evidence

Another usable artifact is:

- [optimization_summary.json](/l:/Likith/Coding_Projects/Python/PeopleFlow/research/experiments/output/optimization_summary.json)

This is useful as:

- evidence that the platform includes parameter optimization workflows
- a sign that scenario tuning and parameter search are part of the research pipeline

### System/workflow evidence

The current codebase itself is strong evidence for the existence of:

- simulation sessions
- replay and analysis
- experiment jobs
- artifact browsing
- floor-plan processing
- interactive geometry editing

This makes the paper stronger as a **systems + case-study safety paper** than as a pure algorithm paper.

## 10. Evidence That Is Currently Weak or Not Publication-Ready

These output files currently contain degenerate or obviously weak results and should **not** be used as core evidence unless they are regenerated and verified:

- [benchmark_corridor.json](/l:/Likith/Coding_Projects/Python/PeopleFlow/research/experiments/output/benchmark_corridor.json)
- [benchmark_multi_exit.json](/l:/Likith/Coding_Projects/Python/PeopleFlow/research/experiments/output/benchmark_multi_exit.json)
- [baseline.json](/l:/Likith/Coding_Projects/Python/PeopleFlow/research/experiments/output/baseline.json) if it shows zeroed or unrealistic metrics in the current run state
- [manual-experiment-run.json](/l:/Likith/Coding_Projects/Python/PeopleFlow/research/experiments/output/manual-experiment-run.json)

Examples of weak patterns seen in the current outputs:

- `total_evacuation_time: 0.0`
- empty flow distributions
- empty exit-flow summaries

These are useful as engineering artifacts, but not yet as polished research results for the final paper.

## 11. Existing Drafts and Docs That Need Careful Use

### Existing LaTeX paper draft

- [research_paper.tex](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/experiments/output/research_paper.tex)
- [references.bib](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/experiments/output/references.bib)

This draft has already been reframed toward case-study safety assessment and is the correct direction to continue.

### Research feature summary

- [RESEARCH_FEATURES_IMPLEMENTATION.md](/l:/Likith/Coding_Projects/Python/PeopleFlow/docs/notes/RESEARCH_FEATURES_IMPLEMENTATION.md)

This file is useful as an implementation inventory, but the writer should treat it as:

- a list of implemented or intended modules
- not a direct proof that every feature is experimentally validated

### Publication notes

- [publication_specs.md](/l:/Likith/Coding_Projects/Python/PeopleFlow/docs/publication_specs.md)

This is useful for methodology language, assumptions, and terminology, but should be filtered through the actual current evidence.

## 12. Recommended Paper Thesis

The paper should make the following argument:

PeopleFlow provides a floor-plan-aware, reproducible evacuation simulation workflow that supports safety-oriented decision-making by quantifying how building layout, occupancy, exit availability, and routing strategy affect evacuation performance.

That is the safest and strongest thesis for the current repo.

## 13. What the Paper Should Emphasize

The paper should emphasize:

- end-to-end workflow from floor plan to analysis
- scenario comparison rather than a single “best” run
- interpretable safety metrics
- case studies on realistic building layouts
- reproducibility through seeds, sessions, and artifacts

The paper should de-emphasize:

- novelty claims about reinforcement learning
- claims of complete hazard realism
- claims of universal real-world validation

## 14. Best Case-Study Structure

The most realistic paper structure is:

### Case A: Simple corridor or benchmark geometry

Purpose:

- easy-to-interpret baseline
- useful for showing core metrics and bottlenecks

### Case B: Multi-room office or academic floor

Purpose:

- show route competition
- show exit imbalance
- compare guidance/routing strategies

### Case C: Large real uploaded floor plan

Purpose:

- show practical relevance
- show floor-plan-to-simulation pipeline on realistic geometry

### Optional Case D: Layout or guidance redesign

Purpose:

- strongest engineering story
- show before/after safety improvement

## 15. Scenario Matrix the Writer Should Assume

For each selected building, the writer should prefer these comparisons:

- baseline evacuation
- higher occupancy stress test
- blocked-exit scenario
- guided-routing scenario

Optional additions:

- shortest-path vs least-crowded vs guided
- different disaster presets if the run quality is stable enough

## 16. Core Metrics the Paper Should Use

Use a compact metric set. The paper does not need every metric in the system.

Recommended core metrics:

- total evacuation time
- 90\% clearance time
- peak local density
- exit utilization balance
- bottleneck count or bottleneck persistence
- percent evacuated within target time

Optional only if stable and interpretable:

- hazard exposure proxies
- survival-oriented metrics

## 17. Language Rules for the AI Writer

Use phrases like:

- simulation-based safety assessment
- safety-oriented decision support
- evidence for safer configurations
- evacuation performance indicators
- scenario-based comparison
- floor-plan-derived simulation

Avoid phrases like:

- guarantees safety
- proves the building is safe
- state-of-the-art RL controller
- fully validated real-world hazard model
- outperforms all prior evacuation systems

## 18. Suggested Section Flow

The writer should preserve this order:

1. Introduction
2. Related Work
3. PeopleFlow Framework
4. Simulation Methodology
5. Safety Assessment Method
6. Case Study Design
7. Results and Interpretation
8. Discussion
9. Conclusion

This is already reflected in:

- [research_paper.tex](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/experiments/output/research_paper.tex)

## 19. Figures and Tables the Writer Should Plan For

### Figures

- overall PeopleFlow workflow diagram
- floor plan and extracted geometry
- simulation snapshots at several time points
- density or bottleneck heatmap

### Tables

- case-study descriptions
- scenario setup summary
- safety metrics by scenario
- policy comparison summary

## 20. Practical Project Notes

- The launcher is Windows-friendly and starts backend + frontend with [start_peopleflow.bat](/l:/Likith/Coding_Projects/Python/PeopleFlow/start_peopleflow.bat).
- The system supports a browser-first workflow, so the paper can mention a usable operator/research interface rather than a backend-only prototype.
- Optional ML dependencies such as PyTorch, YOLO, and Detectron2 are not always installed; the floor-plan pipeline can fall back to OpenCV-based processing.
- This fallback behavior is acceptable to mention as an engineering practicality, but the paper should not oversell the ML side unless those dependencies are part of the actual case-study evidence.

## 21. Suggested “Do Not Hallucinate” Rules for the Writer

The writer must not invent:

- external validation datasets that are not explicitly present
- exact benchmark wins over prior systems
- numerical case-study results not drawn from verified runs
- human-subject study claims
- full-scale real-world deployment claims

The writer may reasonably infer:

- the system is designed for simulation-backed safety assessment
- reproducibility matters in the architecture
- floor-plan-derived case studies are the main evidence format

## 22. Best Next Step After These Notes

The manuscript is no longer only a bare skeleton. It now has:

- a reproduced case-study bundle in [paper_case_studies.json](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/experiments/output/paper_case_studies.json)
- a CSV export in [paper_case_studies.csv](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/experiments/output/paper_case_studies.csv)
- generated figure assets:
  - [fig_pipeline.png](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/experiments/output/fig_pipeline.png)
  - [fig_architecture.png](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/experiments/output/fig_architecture.png)
  - [fig_case_layouts.png](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/experiments/output/fig_case_layouts.png)
  - [fig_floorplan.png](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/experiments/output/fig_floorplan.png)
  - [fig_simulation.png](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/experiments/output/fig_simulation.png)
  - [fig_density.png](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/experiments/output/fig_density.png)
- a BibTeX file in [references.bib](/l:/Likith/Coding_Projects/Python/PeopleFlow/apps/backend/app/experiments/output/references.bib)

The next high-value step is therefore narrower:

- replace the placeholder author/affiliation block with the real authors
- compile and tune the exact IEEE page count in Overleaf
- optionally regenerate the case-study bundle with richer geometry or stronger scenarios before submission

The draft is now closer to a near-submission manuscript than to an empty scaffold, but it still needs final author metadata and a compile-checked polish pass.
