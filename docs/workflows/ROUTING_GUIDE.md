# Task Routing & Subsystem Agent Guide

**Purpose**: Route incoming coding tasks to the correct subsystem specialist and provide context templates.  
**Updated**: 2026-04-01

---

## Quick Routing Matrix

Use this table to identify which agent should own a task:

| Task Type | Primary Agent | Secondary Agents | Context Files |
|-----------|---------------|------------------|----------------|
| Add/modify API endpoint | Backend Specialist | Data Contract Reviewer | `DIRECTORY_INTELLIGENCE.md`, API route file |
| Fix/feature backend logic | Backend Specialist | – | Backend core module file |
| Change API response shape | Data Contract Reviewer | Backend Specialist, Frontend Specialist | Contract schema + route + client |
| Add/modify frontend page | Frontend Specialist | – | Feature folder, router.tsx |
| Fix/feature UI component | Frontend Specialist | – | Component file |
| Connect frontend to new backend | Integration Agent | Backend Specialist, Frontend Specialist | Route file + client file + contract |
| Deploy/infra change | DevOps Agent | Platform team | Dockerfile, docker-compose, render.yaml |
| Add experiment config | Research Agent | Backend Specialist | Experiment file, simulation schema |
| Database schema/migration | Backend Specialist | Data Contract Reviewer | Core/database files, contracts |
| Authentication/security | Backend Specialist | – | Middleware files, config |

---

## Agent Personas

### 1. Backend Specialist
**When to invoke**: Any backend logic, route, middleware, or core service work.

**Scope**: 
- `apps/backend/app/` (all subdirs)
- `apps/backend/requirements.txt`

**Responsibilities**:
- Design and code API routes
- Extend middleware
- Manage database queries
- Implement business logic
- Coordinate with contracts team on schema changes

**Guardrails**:
- DO NOT modify frontend code
- DO check schema alignment before changing response structures
- DO test with current contracts before committing

**Tool Restrictions**: `read`, `search`, `edit`, `todo` (no web, no terminal directly; use scripts)

---

### 2. Frontend Specialist
**When to invoke**: Any UI, routing, state, or feature work.

**Scope**:
- `apps/frontend/src/` (all subdirs)
- `apps/frontend/package.json`
- `apps/frontend/vite.config.ts`

**Responsibilities**:
- Design pages and features
- Manage routing and navigation
- Implement UI components
- Manage state (Zustand, React Query)
- Build and test frontend

**Guardrails**:
- DO NOT modify backend code
- DO align API client calls with backend v2 routes
- DO test with mocked API before integration testing

**Tool Restrictions**: `read`, `search`, `edit`, `todo`

---

### 3. Integration Agent
**When to invoke**: Cross-layer task (new feature from backend → frontend → contract).

**Scope**:
- All layers (serves as coordinator)

**Responsibilities**:
- Define schema contract first
- Implement backend API
- Implement frontend client
- Test end-to-end flow
- Ensure both sides stay in sync

**Guardrails**:
- DO start with contract definition
- DO update contract before changing implementations
- DO run integration tests

**Tool Restrictions**: `read`, `search`, `edit`, `todo`, `agent` (to delegate specialized work)

---

### 4. Data Contract Reviewer
**When to invoke**: Any data structure, schema, or cross-layer data format change.

**Scope**:
- `modules/contracts/`
- Schema validation across layers

**Responsibilities**:
- Review and approve schema changes
- Ensure backward compatibility
- Version schema updates
- Validate consumer alignment

**Guardrails**:
- DO enforce breaking change process
- DO require migration strategy for v1→v2
- DO block non-compliant changes

**Tool Restrictions**: `read`, `search`, `edit`, `todo`

---

### 5. Research Agent
**When to invoke**: Experiments, analytics, ML models, or simulation tuning.

**Scope**:
- `research/`
- `modules/ai_engine/`
- `apps/backend/app/sim/`
- `apps/backend/app/experiments/`

**Responsibilities**:
- Configure and run experiments
- Manage ML training and validation
- Analyze outputs and metrics
- Publish results and reports

**Guardrails**:
- DO align simulation outputs with schema
- DO version experiment configs
- DO document result interpretations

**Tool Restrictions**: `read`, `search`, `edit`, `todo`, `execute` (for experiment runs)

---

### 6. DevOps Agent
**When to invoke**: Docker, deployment, infrastructure, or runtime environment work.

**Scope**:
- `infra/`
- `.github/workflows/` (CI/CD)
- Docker configs

**Responsibilities**:
- Manage deployment configs
- Build and optimize Docker images
- Configure environments and secrets
- Monitor production health

**Guardrails**:
- DO require prod config review before merge
- DO version infrastructure changes
- DO test in staging before production

**Tool Restrictions**: `read`, `search`, `edit`, `todo`, `execute`

---

## Task Template: New Feature

When proposing a new feature, use this template for context:

```markdown
# New Feature: [Feature Name]

## Routing Decision
- **Primary Layer**: [backend | frontend | both]
- **Agent**: [Agent name]

## Requirements
1. [Requirement 1]
2. [Requirement 2]

## Scope
- **New Routes**: [List]
- **Modified Routes**: [List]
- **New Components**: [List]
- **Contract Changes**: [Yes | No]

## Implementation Plan
1. [Step 1]
2. [Step 2]

## Test Plan
- Unit: [Yes | No]
- Integration: [Yes | No]
- E2E: [Yes | No]

## Risk Assessment
- **Contract Risk**: [High | Medium | Low]
- **Cross-layer Risk**: [High | Medium | Low]
- **UX Impact**: [High | Medium | Low]

## Files to Touch
- [ ] `apps/backend/app/api/routes/[domain].py`
- [ ] `apps/frontend/src/features/[feature]/`
- [ ] `modules/contracts/[schema].json`

## Sign-Off
- [ ] Backend Specialist approved
- [ ] Frontend Specialist approved
- [ ] Contract Reviewer approved
```

---

## Task Template: Bug Fix

```markdown
# Bug Fix: [Bug Title]

## Context
- **Reported By**: [Who/Source]
- **Severity**: [Critical | High | Medium | Low]
- **Affected Layer**: [backend | frontend | both]

## Root Cause
[Description of root cause]

## Fix Location
- **File**: [Path]
- **Function**: [Name]
- **Line Range**: [Lines]

## Testing
- [ ] Unit test
- [ ] Regression test
- [ ] Affected workflows tested

## Rollback Plan
[If applicable]
```

---

## Escalation & Blocking Issues

### Blocking Situations
1. **Schema breaking change**: Requires contract + backend + frontend coordination (use Integration Agent)
2. **Database migration**: Requires research + backend coordination
3. **Security issue**: Requires backend + DevOps review
4. **Performance issue**: Requires profiling + agent delegation based on layer

### Escalation Contacts (Placeholder)
- Backend Lead: [Name/Contact]
- Frontend Lead: [Name/Contact]
- DevOps Lead: [Name/Contact]
- Research Lead: [Name/Contact]

---

## Workflow for Complex Tasks

For tasks affecting multiple layers or systems:

1. **Pre-flight**
   - Define requirements clearly
   - Identify all affected layers
   - Review current state (use DIRECTORY_INTELLIGENCE.md)
   - Estimate risk using matrix

2. **Design Phase**
   - Create feature proposal
   - Design schema/contract if needed
   - Get contract approval
   - Get architectural review

3. **Implementation Phase**
   - Implement backend (if needed)
   - Implement frontend (if needed)
   - Implement contracts (if new)
   - Run unit tests per layer

4. **Integration Phase**
   - Connect frontend to backend
   - Run integration tests
   - Test error paths
   - Test with real-world data

5. **Validation Phase**
   - Code review (peer + specialist)
   - Security review (if applicable)
   - Performance review (if applicable)
   - Deployment readiness check

6. **Deployment**
   - Merge to main
   - Build artifacts
   - Deploy to staging
   - Smoke test
   - Deploy to production
   - Monitor logs/metrics

---

## Non-Blocking Dependencies

These can proceed in parallel:

- Frontend UI work ↔ Backend API implementation (if contract is finalized)
- Research experiments ↔ Backend feature work (if experiment config is stable)
- Documentation ↔ Implementation (if requirements are clear)

---

## References

- Directory Intelligence: [DIRECTORY_INTELLIGENCE.md](./DIRECTORY_INTELLIGENCE.md)
- Full Architecture: [../STRUCTURE.md](../STRUCTURE.md)
- Contributing Guide: [../guides/CONTRIBUTING.md](../guides/CONTRIBUTING.md)
