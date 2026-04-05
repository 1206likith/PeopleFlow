# Frontend Renovation Workflow

**Workflow Name**: `frontend-modernization`  
**Execution Mode**: Phased (4 phases over 8-12 weeks)  
**Tracks**: design-system, component-library, state-management, integration  
**Conditions**: design-approved, component-tests-pass, state-migrations-complete, e2e-passing

---

## SECTION 1: Workflow Overview

### Problem Statement
Current frontend has:
- Inconsistent component patterns (custom implementations per feature)
- Manual state management scattered across components
- Limited reusability and testing infrastructure
- Dark theme hardcoded (not extensible)
- Canvas rendering logic coupled to components

### Solution
Build a modern, scalable frontend with:
1. **Design System** - Token-based themes, motion system, accessibility
2. **Component Library** - Atomic components (Button, Input, Card, Modal, Dialog, Tabs, etc.)
3. **Advanced State** - Domain-specific Zustand stores with selectors and middleware
4. **Type Safety** - Zod for API response validation
5. **Forms** - React Hook Form + Zod for builder/designer/operations flows
6. **Testing** - Component tests (Vitest), integration tests (E2E with Playwright)
7. **Performance** - Code splitting, React Query optimization, lazy routes

### Success Criteria
- [ ] All components in library have storybook stories
- [ ] 80%+ unit test coverage
- [ ] 100% TypeScript coverage (strict mode)
- [ ] WCAG 2.1 AA accessibility compliance
- [ ] Performance budget: FCP < 2s, LCP < 3s
- [ ] Build size < 500KB gzipped
- [ ] All features working with new stack

### Timeline
- **Phase 1** (Weeks 1-3): Design System + Token Architecture
- **Phase 2** (Weeks 4-6): Component Library + Storybook
- **Phase 3** (Weeks 7-9): State Management Migration
- **Phase 4** (Weeks 10-12): Forms, E2E Testing, Optimization

---

## SECTION 2: Agent List & Responsibilities

### A0: Frontend Architect (Task Orchestrator)
**Role**: Oversee entire renovation, coordinate handoffs, ensure coherence  
**Owner**: Integration Agent  
**Responsibilities**:
- Track all phases and blockers
- Ensure design system is consumed correctly by all layers
- Manage breaking changes
- Validate end-to-end integration

**Deliverables**:
- Phasing roadmap (this doc)
- Design system consumption guide
- Migration checklist per phase

---

### A1: Design System Architect
**Role**: Define tokens, themes, motion, accessibility baseline  
**Owner**: Frontend Specialist (with Design System expertise)  
**Files/Scope**:
- `apps/frontend/src/styles/tokens.ts` (new)
- `apps/frontend/tailwind.config.js` (refactor)
- `apps/frontend/src/styles/motion.css` (new)
- `apps/frontend/src/styles/typography.css` (new)
- `apps/frontend/src/styles/accessibility.css` (new)

**Responsibilities**:
- Design token system (colors, spacing, typography, shadows, radii)
- Theme variants (light, dark, high-contrast)
- Motion system (transitions, animations, durations)
- Accessibility baseline (focus states, reduced-motion)
- Documentation for tokens

**Success Criteria**:
- [ ] All tokens exported from single source
- [ ] Themes switchable at runtime
- [ ] WCAG AAA contrast ratios for text
- [ ] prefers-reduced-motion respected

---

### A2: UI Component Architect
**Role**: Build foundational UI component library  
**Owner**: Frontend Specialist  
**Files/Scope**:
- `apps/frontend/src/components/ui/` (new, ~15-20 components)
- `apps/frontend/src/components/ui/Button/`
- `apps/frontend/src/components/ui/Input/`
- `apps/frontend/src/components/ui/Card/`
- `apps/frontend/src/components/ui/Modal/`
- `apps/frontend/src/components/ui/Tabs/`
- `apps/frontend/src/components/ui/Select/`
- `apps/frontend/src/components/ui/Checkbox/`
- `apps/frontend/src/components/ui/Dialog/`
- etc.

**Responsibilities**:
- Implement atomic components with strict prop interfaces
- Prop type validation and composition patterns
- Component tests (Vitest + Testing Library)
- Storybook stories
- Accessibility (ARIA, keyboard navigation, focus management)

**Success Criteria**:
- [ ] 15+ core components implemented
- [ ] Each component has unit tests (90%+ coverage)
- [ ] Each component has Storybook story with variants
- [ ] All components pass accessibility audit
- [ ] Components are composable (no feature-specific logic)

---

### A3: Layout & Compound Components Architect
**Role**: Build layout primitives and compound components  
**Owner**: Frontend Specialist  
**Files/Scope**:
- `apps/frontend/src/components/layout/` (refactor)
- `apps/frontend/src/components/compound/` (new)

**Responsibilities**:
- Refactor Layout (PageShell, SideNav, TopNav) to use new tokens
- Create compound components (MenuButton, FormGroup, etc.)
- Create layout composition patterns (Stack, Flex, Grid wrappers)
- Integrate with design system token consumption

**Success Criteria**:
- [ ] Layout components consume tokens only
- [ ] No hardcoded colors/spacing
- [ ] Compound components are exported together

---

### A4: State Management Architect
**Role**: Architect domain-specific Zustand stores  
**Owner**: Frontend Specialist  
**Files/Scope**:
- `apps/frontend/src/lib/state/stores/` (refactor organization)
- `apps/frontend/src/lib/state/stores/simulationStore.ts`
- `apps/frontend/src/lib/state/stores/designerStore.ts`
- `apps/frontend/src/lib/state/stores/analyticsStore.ts`
- `apps/frontend/src/lib/state/middleware/` (new)

**Responsibilities**:
- Design normalized state schemas per domain
- Implement selectors for derived state
- Add middleware (persistence, logging, devtools)
- Type-safe actions
- State synchronization patterns with API

**Success Criteria**:
- [ ] State normalized and testable
- [ ] Selectors prevent unnecessary re-renders
- [ ] Redux DevTools integration works
- [ ] State persistence for builder workflows

---

### A5: Form System Architect
**Role**: Integrate React Hook Form + Zod for complex forms  
**Owner**: Frontend Specialist  
**Files/Scope**:
- `apps/frontend/src/lib/forms/` (new)
- `apps/frontend/src/components/forms/` (new)

**Responsibilities**:
- Create form schema definitions (Zod)
- Integrate React Hook Form with UI components
- Form validation (client-side + sync with backend)
- Multi-step forms (designer, scenarios, operations)
- Error display and recovery

**Success Criteria**:
- [ ] All builder/designer forms use RHF + Zod
- [ ] Type-safe form submissions
- [ ] Real-time validation with error display
- [ ] Form state persistence

---

### A6: Feature Integration Lead
**Role**: Migrate existing features to use new systems  
**Owner**: Frontend Specialist  
**Files/Scope**:
- `apps/frontend/src/features/` (refactor each feature module)

**Responsibilities**:
- Migrate each feature (home, designer, simulation, analytics, scenarios, operations)
- Replace old components with new library
- Connect to stores instead of local state
- Update API client integration to use Zod validation
- Add component-level tests

**Success Criteria**:
- [ ] All features refactored (6 features total)
- [ ] All features have component tests
- [ ] Feature integration tests pass
- [ ] No visual regressions

---

### A7: Testing & Performance Lead
**Role**: E2E testing, performance profiling, accessibility audit  
**Owner**: Frontend Specialist  
**Files/Scope**:
- `apps/frontend/tests/e2e/` (expand)
- `apps/frontend/playwright.config.ts` (update)

**Responsibilities**:
- Expand E2E test scenarios (Playwright)
- Performance profiling and optimization
- Accessibility audit (Axe, WAVE)
- Bundle size tracking
- CI/CD integration for performance budgets

**Success Criteria**:
- [ ] 15+ E2E test scenarios
- [ ] Performance budgets enforced
- [ ] Accessibility audit passes (95%+ issues resolved)
- [ ] Bundle size tracked and bounded

---

## SECTION 3: Phase Breakdown & Specialist Assignments

### PHASE 1: Design System (Weeks 1-3)

**Lead**: A1 (Design System Architect)  
**Supporting**: A0 (Frontend Architect)  

**Week 1: Token Definition**
- [ ] Define color palette (semantic tokens: primary, secondary, danger, warning, success, info)
- [ ] Define typography scale (sizes, weights, line-heights)
- [ ] Define spacing scale (4px base, multiples)
- [ ] Define focus states and interactive feedback
- [ ] Document token usage guide

**Week 2: Theme Implementation**
- [ ] Implement Tailwind token integration
- [ ] Create light/dark/high-contrast themes
- [ ] Add CSS custom properties for runtime theming
- [ ] Implement motion system (durations, easing)
- [ ] Add accessibility baseline (focus rings, reduced-motion)

**Week 3: Documentation & Validation**
- [ ] Create design tokens documentation site (or Storybook-hosted)
- [ ] Validate WCAG contrast ratios
- [ ] Performance-test token delivery
- [ ] Get design approval

**Handoff to Phase 2**: Design system tokens finalized, all CSS variables in place

---

### PHASE 2: Component Library (Weeks 4-6)

**Lead**: A2 (UI Component Architect)  
**Supporting**: A3 (Layout Architect), A0 (Frontend Architect)  

**Week 4: Core Components (Part 1)**
- [ ] Button (primary, secondary, outline, ghost, loading states)
- [ ] Input (text, email, password, with validation)
- [ ] Card (with variants: plain, elevated, outlined)
- [ ] Badge/StatusBadge
- [ ] Spinner/Loader
- [ ] Implement 80% of tests for each

**Week 5: Complex Components (Part 2)**
- [ ] Modal/Dialog (portal-based, accessibility)
- [ ] Tabs (keyboard navigation, aria-labels)
- [ ] Select (dropdown, multi, searchable)
- [ ] Checkbox/Radio
- [ ] Alert/Toast
- [ ] Implement tests; start Storybook stories

**Week 6: Compound & Layout Components**
- [ ] Compound components (MenuButton, FormGroup, etc.)
- [ ] Layout wrappers (Stack, Flex, Grid)
- [ ] Refactor existing layout components (PageShell, SideNav, TopNav)
- [ ] Complete Storybook stories for all components
- [ ] Accessibility audit pass 1

**Handoff to Phase 3**: Component library complete with tests and Storybook, 90%+ test coverage

---

### PHASE 3: State Management & Forms (Weeks 7-9)

**Lead**: A4 (State Management Architect) + A5 (Form System Architect)  
**Supporting**: A6 (Feature Integration Lead), A0 (Frontend Architect)  

**Week 7: State Store Architecture**
- [ ] Design simulation store (normalized, selectors)
- [ ] Design designer store (normalized, form state)
- [ ] Design analytics store (query results, filters)
- [ ] Add middleware (persistence, devtools, logging)
- [ ] Implement tests for stores

**Week 8: Forms & Validation**
- [ ] Create Zod schemas for all forms (builder, scenarios, operations)
- [ ] Integrate React Hook Form with UI components
- [ ] Build form wrappers and utilities
- [ ] Implement multi-step form state management
- [ ] Add real-time validation

**Week 9: Feature Migration (Part 1)**
- [ ] Migrate designer feature to use new stores + forms
- [ ] Migrate operations page to use new forms
- [ ] Connect API clients to use Zod validation
- [ ] Add feature-level integration tests

**Handoff to Phase 4**: Stores complete, forms system ready, 50% of features migrated

---

### PHASE 4: Integration, Testing & Optimization (Weeks 10-12)

**Lead**: A6 (Feature Integration Lead) + A7 (Testing & Performance Lead)  
**Supporting**: A0 (Frontend Architect)  

**Week 10: Feature Migration (Part 2)**
- [ ] Migrate simulation feature
- [ ] Migrate analytics feature
- [ ] Migrate scenarios feature
- [ ] Migrate home feature
- [ ] All features use new component library

**Week 11: E2E Testing & Accessibility**
- [ ] Expand E2E test scenarios (Playwright): 15+ scenarios
- [ ] Accessibility audit (Axe, WAVE) on all pages
- [ ] Fix critical accessibility issues
- [ ] Performance profiling (Lighthouse, custom metrics)

**Week 12: Optimization & Rollout**
- [ ] Code splitting and lazy route loading
- [ ] React Query cache optimization
- [ ] Bundle size optimization and tracking
- [ ] Performance budget enforcement
- [ ] Final testing and sign-off

**Handoff to Production**: All features migrated, tests green, performance budgets met

---

## SECTION 4: Data Flow & Integration Points

### State Management Flow
```
API Response (Zod validation) 
  ↓
Zustand Store (normalized) 
  ↓
Selectors (derived state) 
  ↓
Component consumption (no re-renders for unrelated changes) 
  ↓
User action → Action handler → Store update
```

### Component Hierarchy
```
App 
  ├── Providers (QueryClient, Zustand)
  ├── AppRouter (React Router)
  └── PageShell
      ├── TopNav (refactored → new components)
      ├── SideNav (refactored → new components)
      └── Page (feature)
          └── FeatureComponents (new library components + feature-specific)
```

### Form Data Flow
```
Form Schema (Zod) 
  ↓
React Hook Form (validation + state) 
  ↓
Form Component (with UI components) 
  ↓
onSubmit → API call (with Zod response validation) 
  ↓
Store update + success feedback
```

---

## SECTION 5: Specialist Task Breakdown

See `FRONTEND_RENOVATION_TASKS.md` for detailed task assignments per specialist.

---

## Blockers & Risks

**Risk: Design System Design Paralysis**
- *Mitigation*: Use existing design as baseline; iterate in sprints, not perfect upfront

**Risk: Component Library Explosion**
- *Mitigation*: Strict prop interfaces, no feature-specific variants in core library

**Risk: State Migration Breaks Existing Features**
- *Mitigation*: Parallel stores during migration; old and new coexist until feature migrated

**Risk: Forms Become Complex**
- *Mitigation*: Start with simple forms; complex ones (multi-step) done in Phase 3 week 9

**Risk: E2E Tests Flaky**
- *Mitigation*: Use test IDs, explicit waits, run multiple times before declaring passing

---

## Sign-Offs Required

- [ ] Design System approved by design/frontend team (end of Phase 1)
- [ ] Component Library code review passed (end of Phase 2)
- [ ] State Management patterns approved (mid Phase 3)
- [ ] E2E test suite approved (end of Phase 4)
- [ ] Performance budgets met (end of Phase 4)
- [ ] Go-live approval (end of Phase 4)

