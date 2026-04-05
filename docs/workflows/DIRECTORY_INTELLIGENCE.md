# Directory Intelligence Baseline

**Generated**: 2026-04-01  
**Scope**: PeopleFlow full-stack platform  
**Purpose**: Repository topology, entrypoints, boundaries, and safe edit zones

---

## Topology Overview

```
PeopleFlow (Root)
├── apps/                    # Runtime applications
│   ├── backend/            # FastAPI service (simulation, API, experiments)
│   ├── frontend/           # React + Vite client (UI, routing, API clients)
│   └── unity/              # Unity visualization/simulation project
├── modules/                # Shared platform code
│   ├── contracts/          # JSON schema truth (canonical data definitions)
│   └── ai_engine/          # ML models, training pipelines
├── research/               # Experiments, analytics, outputs
├── infra/                  # Docker, deployment, runtime config
├── docs/                   # Architecture, guides, notes
└── artifacts/              # Generated outputs, logs, reports
```

---

## Entrypoints by Layer

### Backend
- **Entry File**: `apps/backend/app/main.py`
- **Entry Point**: FastAPI app initialization with middleware stack
- **Runtime**: `uvicorn app.main:app --port 8000`
- **API Docs**: `/api/v2/docs`

### Frontend
- **Entry File**: `apps/frontend/src/main.tsx`
- **Router File**: `apps/frontend/src/app/router.tsx`
- **Entry Point**: React 19 + React Router 7
- **Build**: `npm run build` (Vite)
- **Dev**: `npm run dev`

### Unity
- **Entry**: `apps/unity/Assets/Scenes/`
- **Type**: Standalone project (Packages, ProjectSettings, Scripts)

---

## API Surface Map

### Backend Routes (v2 Primary)

| Domain | Module | Routes | Purpose |
|--------|--------|--------|---------|
| Simulation | `simulation.py` | `/api/v2/simulations` | Create, list, run, update simulations |
| Results | `results.py` | `/api/v2/results` | Query simulation results |
| Reports | `reports.py` | `/api/v2/reports` | Generate and retrieve reports |
| Predictions | `predictions.py` | `/api/v2/predictions` | ML predictions and inference |
| Replay | `replay.py` | `/api/v2/replay` | Replay simulation runs |
| Metrics | `metrics.py` | `/api/v2/metrics` | Export metrics and timeseries |
| Scenarios | `scenarios.py` | `/api/v2/scenarios` | Manage scenario presets |
| Validation | `validation.py` | `/api/v2/validation` | Validation and benchmark utilities |
| Optimization | `optimization.py` | `/api/v2/optimization` | Optimization runs and configs |
| System | `system.py` | `/api/v2/system` | System status, health, info |
| Models | `models.py` | `/api/v2/models` | Model registry and management |
| ML | `ml.py` | `/api/v2/ml` | ML inference endpoints (optional) |
| Unity | `unity.py` | `/api/v2/unity` | WebSocket + admin mutations (optional) |

### Backend Middleware Stack
(First executed → Last added)
1. `CorrelationIDMiddleware` - Trace request flow
2. `ApiV2EnvelopeMiddleware` - v2 response shape
3. `AdminKeyMiddleware` - Admin API key guard
4. `HttpsOnlyMiddleware` - Optional HTTPS enforcement
5. `RequestSizeLimitMiddleware` - Body size limit
6. `MetricsMiddleware` (optional) - Prometheus metrics
7. `RateLimitMiddleware` (optional) - Rate limiting
8. `StructuredLoggingMiddleware` - JSON logging
9. `GZipMiddleware` - Compression
10. `SecurityHeadersMiddleware` - Security headers
11. `CORSMiddleware` - CORS

### WebSocket
- **Endpoint**: `/ws/{simulation_id}` (upgraded)
- **Auth**: `admin_key` query parameter required for write ops
- **Manager**: `app.api.websocket.ConnectionManager`
- **Message Types**: `ping`, `simulation_update`, `subscribe`, `subscribed`, `error`, `pong`

---

## Frontend Route & Feature Map

### Routes (from `router.tsx`)
| Path | Feature Module | Component | Purpose |
|------|----------------|-----------|---------|
| `/` | `home` | `HomePage` | Landing page / navigation hub |
| `/designer` | `designer` | `DesignerPage` | Floor plan upload, exit config, annotation |
| `/simulation` | `simulation` | `SimulationHubPage` | Simulation list, create, run, control |
| `/analytics` | `analytics` | `AnalyticsHubPage` | Results exploration, reports, metrics |
| `/scenarios` | `scenarios` | `ScenarioBuilderPage` | Scenario preset browser, custom creation |
| `/operations` | `operations` | `OperationsPage` | Admin, system status, batch management |

### API Client Layer (`lib/api/*.ts`)
| Module | Routes Served |
|--------|---------------|
| `simulation.ts` | Simulation CRUD, control |
| `results.ts` | Results retrieval |
| `metrics.ts` | Metrics export |
| `scenarios.ts` | Scenario management |
| `analytics.ts` | Report and export functions |
| `ml.ts` | ML inference |
| `optimization.ts` | Optimization runs |
| `unity.ts` | WebSocket client (optional) |
| `system.ts` | System health |

### Frontend State & Data Flow
- **Router**: React Router 7 (`BrowserRouter` + centralized `Routes`)
- **Data Fetching**: TanStack React Query v5 (query cache, mutations)
- **State**: Zustand (global stores)
- **Styling**: Tailwind CSS + PostCSS + responsive design

---

## Shared Contracts (modules/contracts/)

All TypeScript and JSON schemas should align with these canonical definitions:

| Schema | Purpose |
|--------|---------|
| `simulation.schema.json` | Simulation state, config, results |
| `experiment_index.schema.json` | Experiment registry and metadata |
| `experiment_result.schema.json` | Experiment output structure |
| `metrics.schema.json` | Metrics payload and timeseries |
| `websocket.schema.json` | WebSocket message contracts |

---

## Safe Edit Zones (By Responsibility)

### Backend API Endpoints
- **Path**: `apps/backend/app/api/routes/`
- **Safe**: Add new route files, modify existing endpoint handlers
- **Caution**: Do not alter middleware stack order without testing
- **Owned by**: Backend API team

### Backend Core Services
- **Path**: `apps/backend/app/core/`
- **Safe**: Add new services, extend config
- **Caution**: Middleware and config changes affect all routes
- **Owned by**: Backend platform team

### Backend Simulation Engine
- **Path**: `apps/backend/app/sim/`
- **Safe**: Modify physics, pathfinding, agent behavior
- **Caution**: Output changes must match `simulation.schema.json`
- **Owned by**: Research/simulation team

### Frontend Routes & Pages
- **Path**: `apps/frontend/src/app/`
- **Safe**: Add routes, modify router logic
- **Caution**: Ensure new routes are discoverable in navigation
- **Owned by**: Frontend application team

### Frontend Features (Domain-Specific Pages)
- **Path**: `apps/frontend/src/features/`
- **Safe**: Add new feature folders, modify feature-local components
- **Caution**: Do not break existing API client contracts
- **Owned by**: Feature teams (designer, simulation, analytics, etc.)

### Frontend API Clients
- **Path**: `apps/frontend/src/lib/api/`
- **Safe**: Add endpoints, modify request/response mapping
- **Caution**: Changes must stay in sync with backend v2 API
- **Owned by**: Frontend + Backend integration team

### Frontend Components & Lib
- **Path**: `apps/frontend/src/components/` and `apps/frontend/src/lib/`
- **Safe**: Add reusable UI components, utilities
- **Caution**: Do not couple to specific features
- **Owned by**: Frontend infrastructure team

### Shared Contracts
- **Path**: `modules/contracts/`
- **Safe**: Add new schema files (new domains), extend existing schemas backward-compatibly
- **Caution**: Breaking schema changes require migration strategy
- **Owned by**: API contract committee (backend + frontend + Unity)

### Research & Experiments
- **Path**: `research/experiments/` and `research/analytics/`
- **Safe**: Add experiment configs, analysis scripts, output reports
- **Caution**: Do not alter baseline/calibration config format without versioning
- **Owned by**: Research team

### Infrastructure & Deployment
- **Path**: `infra/`
- **Safe**: Add new docker-compose configs, deployment scripts
- **Caution**: Production config changes require review
- **Owned by**: DevOps/platform team

---

## Edit Risk Matrix

| Zone | Risk | Impact | Review Needed |
|------|------|--------|---------------|
| Backend route handler | Low | Single endpoint | Feature owner |
| Backend middleware | High | All requests | Platform team |
| Backend simulation core | High | All results | Research team |
| Frontend route | Low | Single page entry | Frontend team |
| Frontend feature | Low | Single feature | Feature owner |
| Frontend API client | Medium | All feature calls | Integration team |
| Contracts | High | Cross-layer | All stakeholders |
| Infra config | High | Deployment & runtime | DevOps + platform |

---

## Task Routing Guide

When working on a new feature or fix, use this flowchart:

```
Question 1: What layer?
├─ API behavior? → Backend route file
├─ UI layout/interaction? → Frontend feature
├─ Data transmission? → API client + schema
└─ Deployment/runtime? → Infra

Question 2: Is it a new domain?
├─ Yes → Create new route file + API client + schema
└─ No → Extend existing

Question 3: Cross-layer change?
├─ Yes → Update contracts first, then consumers
└─ No → Single-layer implementation

Question 4: Data format change?
├─ Yes → Schema review required
└─ No → Safe to proceed
```

---

## Dependency Map

### Backend Dependencies (Key)
- **Web**: FastAPI 0.104, Pydantic 2.5
- **Database**: Motor/PyMongo (async MongoDB)
- **Real-time**: python-socketio, redis
- **ML**: TensorFlow 2.15, PyTorch 2.1, scikit-learn
- **Data**: numpy, pandas, scipy, OpenCV

### Frontend Dependencies (Key)
- **Web**: React 19, React Router 7, Vite 7.3
- **Data**: TanStack React Query 5, Zustand 5, axios (via client.ts)
- **UI**: Tailwind CSS 3.4, Recharts 3.7
- **Testing**: Vitest, Playwright, Testing Library

### Shared Dependencies
- Python 3.10+ (backend)
- Node 18+/npm 9+ (frontend)
- Docker (deployment)

---

## Known Concerns & Future Work

1. **v1 API Deprecation**: v1 routes still mounted; plan migration timeline
2. **ML Model Loading**: Conditional on `ENVIRONMENT=production`; consider lazy loading
3. **Admin Key Security**: Query param auth is convenient but visible in logs; consider header-only for production
4. **WebSocket Scalability**: In-memory connection manager; consider Redis adapter for multi-instance
5. **Contract Drift**: Schemas live in JSON; consider OpenAPI 3.1 generation for API auto-docs
6. **Frontend Build**: Single vite.config; consider split for mono-repo optimization

---

## References

- Main: [README.md](../../README.md)
- Architecture: [docs/STRUCTURE.md](../STRUCTURE.md)
- Quick Start: [docs/README.md](../README.md)
- Guides: [docs/guides/](../guides/)
