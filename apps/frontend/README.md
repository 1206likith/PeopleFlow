# PeopleFlow Frontend

React + Vite + TypeScript frontend for PeopleFlow API v2.

## Environment

Copy `.env.example` to `.env` and adjust values:

- `VITE_API_BASE_URL`
- `VITE_WS_BASE_URL`
- `VITE_DEFAULT_ACTOR_ID`
- `VITE_ENABLE_UNITY_HOOK`

## Scripts

- `npm run dev -- --host 127.0.0.1 --port 4173`
- `npm run typecheck`
- `npm run test`
- `npm run build`
- `npm run test:e2e`

## Routes

- `/`
- `/designer`
- `/simulation`
- `/analytics`
- `/scenarios`
- `/operations`
- `/experiments`

Compatibility redirects:

- `/dashboard` -> `/`
- `/simulate` -> `/simulation`
- `/upload` -> `/designer`
- `/design` -> `/designer`
