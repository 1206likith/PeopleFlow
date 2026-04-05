# API v2 Migration Guide

## Overview
- `/api/auth/*` has been removed.
- `/api/v2/*` is now the primary API surface.
- v1 routes remain temporarily and return deprecation headers.
- v2 docs and schema are served at `/api/v2/docs` and `/api/v2/openapi.json`.

## Security Model
- No user authentication tokens.
- Read endpoints are open.
- Mutating endpoints under `/api/v2/*` require `X-Admin-Key`.
- Unity write websocket requires `admin_key` query parameter.

## Runtime Modes
- `APP_MODE=production` requires a live MongoDB connection at startup (fail-fast if unavailable).
- `APP_MODE=demo` runs with deterministic in-memory behavior and `meta.mode = "demo"` in v2 responses.

## Compatibility Matrix
| v1 | v2 |
|---|---|
| `/api/simulation/*` | `/api/v2/simulations/*` |
| `/api/results/*` | `/api/v2/results/*` |
| `/api/reports/*` | `/api/v2/reports/*` |
| `/api/predictions/*` | `/api/v2/predictions/*` |
| `/api/replay/*` | `/api/v2/replay/*` |
| `/api/metrics/*` | `/api/v2/metrics/*` |
| `/api/scenarios/*` | `/api/v2/scenarios/*` |
| `/api/validation/*` | `/api/v2/validation/*` |
| `/api/optimization/*` | `/api/v2/optimization/*` |
| `/api/system/*` | `/api/v2/system/*` |
| `/api/unity/*` | `/api/v2/unity/*` |
| `/api/ml/*` | `/api/v2/ml/*` |

## Migration Checklist
- Remove all `/api/auth/*` client calls.
- Remove bearer-token wiring from API clients.
- Route all reads/writes to `/api/v2/*`.
- Add `X-Admin-Key` for all mutating v2 requests (`POST`, `PUT`, `PATCH`, `DELETE`).
- Update websocket Unity clients to pass `admin_key` query parameter.
- Expect v2 envelope response shape (`meta` + `data|error`).
- Inspect v1 responses for deprecation headers and move off v1 before `2026-06-30`.

## Envelope Contract
v2 JSON responses are wrapped:

```json
{
  "meta": {
    "version": "v2",
    "mode": "demo|production",
    "path": "/api/v2/...",
    "correlation_id": "...",
    "timestamp": "..."
  },
  "data": {}
}
```

Errors:

```json
{
  "meta": {"version": "v2", "...": "..."},
  "error": {
    "code": "validation_error|http_error|internal_error",
    "message": "...",
    "details": {}
  }
}
```

## Deprecation Timeline
- v2 GA target: 2026-03-31
- v1 frozen: 2026-04-15
- v1 removal: 2026-06-30
