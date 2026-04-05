# Frontend Renovation: Specialist Task Assignments

**Master Coordinator**: Integration Agent  
**Execution Model**: Phased handoff, parallel work where possible  
**Communication**: Weekly sync, blockers escalated immediately

## EXECUTION STATUS (April 1, 2026)

### Completed Deltas
- [x] Theme runtime infrastructure (`data-theme`, Zustand persistence, theme sync) implemented.
- [x] Tokenized visual variables created (`apps/frontend/src/styles/variables.css`, `apps/frontend/src/styles/themes.css`).
- [x] Top utility bar theme switcher integrated.
- [x] Operations hub wired to expanded backend surface including:
  - [x] Models endpoints (`/api/v2/models/floorplan/train`, `/api/v2/models/floorplan/train/{job_id}`)
  - [x] Unity scene endpoint (`/api/v2/unity/scene/{simulation_id}`)
  - [x] Predictions, validation, replay extended, and reports actions.
- [x] Frontend typecheck clean after integration changes.
- [x] Shared `JsonPanel` component extracted and adopted in analytics tabs to reduce repeated JSON preview markup.

### In Progress Now
- [x] Phase 2 page renovation pass for core user-facing screens.
- [x] Home page visual and interaction refresh completed (class-driven, responsive).
- [x] Simulation hub visual refactor baseline completed (layout shells, alerts, workspace surfaces, tab/scrubber styling moved to reusable classes).
- [x] Analytics hub shell refactor baseline completed (header + selector/tab rail).
- [x] Analytics internals consistency pass (Overview moved to reusable analytics classes; remaining tabs already token-aligned).
- [x] Scenario builder consistency pass.

### Next Execution Targets
1. Optional: add Playwright visual-regression snapshots for Home/Simulation/Analytics shells.
2. Optional: extract repeated JSON preview panels into a shared `JsonPanel` component.
3. Optional: add focused integration tests for newly exposed Operations endpoint actions.

---

## SPECIALIST 1: Frontend Specialist (Design System Lead)
### Phase 1: Design System Architecture (Weeks 1-3)

**Total Effort**: 3 weeks | **Priority**: CRITICAL (blocks all other work)

#### Task 1.1: Token System Design
**Objective**: Define complete token taxonomy  
**Acceptance Criteria**:
- [ ] Color tokens: semantic (primary, secondary, danger, warning, success, info, neutral)
- [ ] Each color has 5-9 shades (50, 100, 200, ... 900)
- [ ] Text colors with 4.5:1 minimum contrast
- [ ] Spacing scale: base 4px, multiples (4, 8, 12, 16, 24, 32, 48, 64)
- [ ] Typography: 6-8 sizes (xs: 12px → 2xl: 32px)
- [ ] Border radius: 4 standard (sm, md, lg, xl)
- [ ] Shadows: 4-5 depths (sm → lg)
- [ ] Duration/easing for motion
- [ ] Type-safe token exports (`src/lib/design/tokens.ts`)

**Deliverables**:
- `src/lib/design/tokens.ts` - TypeScript token definitions
- `tokens-reference.md` - Human-readable token guide
- `colors.json` - Color palette visualization data

**Handoff Checklist**:
- [ ] All tokens exported and type-safe
- [ ] Color specs meet WCAG AA for all text combinations
- [ ] Design team approves palette

---

#### Task 1.2: Tailwind Configuration & CSS Custom Properties
**Objective**: Wire tokens into Tailwind; enable runtime theming  
**Acceptance Criteria**:
- [ ] `tailwind.config.js` uses token values
- [ ] CSS custom properties (`--color-primary`, etc.) in `:root`
- [ ] Theme variants (light, dark, high-contrast) switchable via `[data-theme]`
- [ ] All Tailwind colors, spacing, sizes use tokens (no hardcoded values)
- [ ] No magic numbers in config

**Deliverables**:
- Updated `tailwind.config.js`
- `styles/variables.css` - CSS custom properties
- `styles/themes.css` - Theme variants
- Testing that `npm run build` generates correct CSS

**Handoff Checklist**:
- [ ] `tailwind.config.js` builds without errors
- [ ] CSS variables show correct values in DevTools
- [ ] Theme switching works (localStorage + `[data-theme]` attribute)

---

#### Task 1.3: Motion & Animation System
**Objective**: Standardize transitions, animations, and motion preferences  
**Acceptance Criteria**:
- [ ] Duration tokens: fast (150ms), base (250ms), slow (350ms), xslow (500ms)
- [ ] Easing tokens: easeIn (cubic-bezier), easeOut, easeInOut, standard
- [ ] Entrance animation (fade-rise, slide-in)
- [ ] Exit animation (fade-out, slide-out)
- [ ] `prefers-reduced-motion` respected (no animations when disabled)
- [ ] All animations use tokens (no hardcoded durations)

**Deliverables**:
- `styles/motion.css` - Keyframes and animation classes
- `src/lib/design/motion.ts` - Motion token exports
- `motion-examples.html` - Reference page showing all animations

**Handoff Checklist**:
- [ ] Motion system uses tokens only
- [ ] `prefers-reduced-motion` media query respected
- [ ] No hardcoded animation durations or easings

---

#### Task 1.4: Typography & Accessibility Baseline
**Objective**: Establish typography scale and accessibility foundations  
**Acceptance Criteria**:
- [ ] 9 text sizes (xs, sm, base, md, lg, xl, 2xl, 3xl, 4xl)
- [ ] Font weights: 400 (regular), 500 (medium), 600 (semibold), 700 (bold)
- [ ] Line heights: 1.2 (compact), 1.5 (reading), 1.7 (loose)
- [ ] Letter spacing tokens for labels
- [ ] Focus ring styling (2px solid, consistent across all interactive elements)
- [ ] Focus visible styles in CSS

**Deliverables**:
- `styles/typography.css` - Font scales, weights, line heights
- `styles/accessibility.css` - Focus styles, reduced-motion overrides
- `typography-guide.md` - Usage examples

**Handoff Checklist**:
- [ ] All text uses size classes (no arbitrary sizes)
- [ ] Focus rings are consistent and 2px minimum
- [ ] WCAG AAA text contrast passes on all combinations

---

#### Task 1.5: Documentation & Storybook Setup
**Objective**: Document tokens and create Storybook home for component system  
**Acceptance Criteria**:
- [ ] Storybook installed and configured
- [ ] Design system docs page in Storybook (colors, typography, spacing, motion)
- [ ] Interactive token browser (click colors to copy values)
- [ ] Design system usage guide (markdown)

**Deliverables**:
- Storybook config (`.storybook/`)
- `stories/DesignSystem.stories.tsx` - Design tokens showcase
- `stories/Introduction.mdx` - Design system guide

**Handoff Checklist**:
- [ ] Storybook starts and builds without errors
- [ ] Design tokens are interactive and copyable
- [ ] Team can access Storybook to view system

---

## SPECIALIST 2: Frontend Specialist (Component Library Lead)
### Phase 2: Component Library (Weeks 4-6)

**Total Effort**: 3 weeks | **Priority**: CRITICAL (blocks feature work)  
**Prerequisite**: Task 1.1-1.5 complete (design system tokens)

#### Task 2.1: Atomic Components (Part 1)
**Objective**: Build core interactive components  
**Acceptance Criteria**:
- [ ] Button (variants: primary, secondary, outline, ghost, icon, loading)
- [ ] Input (text, email, password, number, validation states, disabled)
- [ ] Badge (standard, accent color variants, dismissible)
- [ ] Spinner/Loader (circular, inline, full-page variants)
- [ ] Each component: unit tests (90%+ coverage), Storybook story, TypeScript types

**Component Requirements**:
Each component must have:
- Props interface (strict typing)
- Default props documented
- Accessible ARIA attributes
- Focus management
- Keyboard navigation (if interactive)
- Snapshot tests
- 3-5 story variants

**Deliverables**:
- `src/components/ui/Button/`
- `src/components/ui/Input/`
- `src/components/ui/Badge/`
- `src/components/ui/Spinner/`
- Tests: `src/components/ui/**/*.test.tsx`
- Stories: `src/components/ui/**/*.stories.tsx`

**Handoff Checklist**:
- [ ] All components typed with strict TypeScript
- [ ] All tests passing (90%+ coverage)
- [ ] All stories rendering in Storybook
- [ ] Accessibility audit on each

---

#### Task 2.2: Form Components (Part 2)
**Objective**: Build form input components  
**Acceptance Criteria**:
- [ ] FormGroup (label + input + error/hint)
- [ ] Select (dropdown, controlled, disabled states)
- [ ] Checkbox (single, group, indeterminate)
- [ ] Radio (single, group)
- [ ] FileInput (file picker, multi, validation)
- [ ] TextArea (resizable, char counter)
- [ ] Each with tests, stories, accessibility

**Deliverables**:
- `src/components/ui/FormGroup/`
- `src/components/ui/Select/`
- `src/components/ui/Checkbox/`
- `src/components/ui/Radio/`
- `src/components/ui/FileInput/`
- `src/components/ui/TextArea/`
- Tests, stories for each

**Handoff Checklist**:
- [ ] Form components work with React Hook Form
- [ ] Validation states clear (error, success, warning)
- [ ] Screen readers can navigate properly

---

#### Task 2.3: Complex Components (Part 3)
**Objective**: Build modal, dialog, tabs, and layout primitives  
**Acceptance Criteria**:
- [ ] Modal (portal-based, backdrop, close button, focus trap)
- [ ] Dialog (configurable, confirmable, dismissible)
- [ ] Tabs (keyboard nav with Arrow keys, active state, disabled)
- [ ] Alert (with icon, color variants, dismissible)
- [ ] Card (variants: plain, elevated, outlined, interactive)
- [ ] Stack/Flex/Grid (layout composition primitives)

**Deliverables**:
- `src/components/ui/Modal/`
- `src/components/ui/Dialog/`
- `src/components/ui/Tabs/`
- `src/components/ui/Alert/`
- `src/components/ui/Card/`
- `src/components/ui/Stack/`, `Flex/`, `Grid/` (layout)
- Tests, stories

**Handoff Checklist**:
- [ ] Modal properly traps focus and restores on close
- [ ] Tabs keyboard navigation works (ArrowLeft/ArrowRight, Home, End)
- [ ] All portals render correctly
- [ ] Layout primitives responsive and composable

---

#### Task 2.4: Compound Components & Hooks
**Objective**: Create reusable compound component patterns  
**Acceptance Criteria**:
- [ ] MenuButton (button + dropdown menu)
- [ ] DropdownMenu (with keyboard nav, submenus optional)
- [ ] Breadcrumb (with separators, links)
- [ ] Stepper (multi-step form indicator)
- [ ] Tooltip (hover-based, keyboard-accessible)
- [ ] Custom hooks: useClickOutside, useFocusTrap, useMediaQuery

**Deliverables**:
- `src/components/compound/MenuButton/`
- `src/components/compound/DropdownMenu/`
- `src/components/compound/Breadcrumb/`
- `src/components/compound/Stepper/`
- `src/components/compound/Tooltip/`
- `src/lib/hooks/` (custom hooks)

**Handoff Checklist**:
- [ ] Hooks are pure and have no side effects (unless documented)
- [ ] Compound components compose properly
- [ ] All keyboard interactions working

---

#### Task 2.5: Refactor Layout Components
**Objective**: Migrate existing layout to new system  
**Acceptance Criteria**:
- [ ] PageShell uses new components and tokens (no hardcoded colors)
- [ ] TopNav refactored (new Button, MenuButton, Tabs)
- [ ] SideNav refactored (new navigation components)
- [ ] All layout components use token spacing
- [ ] Responsive breakpoints consistent

**Deliverables**:
- Refactored `src/components/layout/PageShell.tsx`
- Refactored `src/components/layout/TopNav.tsx`
- Refactored `src/components/layout/SideNav.tsx`
- Updated tests

**Handoff Checklist**:
- [ ] All layout still works (visual regression tests pass)
- [ ] No CSS hardcoded (all from tokens)
- [ ] Responsive design unchanged

---

#### Task 2.6: Storybook & Documentation
**Objective**: Document all components with stories and guide  
**Acceptance Criteria**:
- [ ] 20+ components have Storybook stories
- [ ] Each story has 3-5 variants (default, hovering, active, disabled, loading)
- [ ] Component API documented (props, examples, accessibility notes)
- [ ] Design system page updated with component gallery
- [ ] Contribution guide for adding new components

**Deliverables**:
- Complete Storybook config
- Stories for all components
- `COMPONENT_GUIDE.md` - How to build new components
- `docs/COMPONENT_LIBRARY.md` - Complete component reference

**Handoff Checklist**:
- [ ] `npm run storybook` starts without errors
- [ ] All components rendered correctly
- [ ] Stories cover all variants
- [ ] Accessibility tests in Storybook (Axe integration)

---

## SPECIALIST 3: Frontend Specialist (State Management Lead)
### Phase 3a: State Management (Weeks 7-8)

**Total Effort**: 2 weeks | **Priority**: HIGH (enables form system and feature migration)  
**Prerequisite**: Tasks 2.1-2.6 complete

#### Task 3.1: Zustand Store Architecture
**Objective**: Design and implement domain-specific stores  
**Acceptance Criteria**:
- [ ] Simulation store: run state, results, timeline, filters
- [ ] Designer store: floor plan, exits, annotations, mode (view/edit)
- [ ] Analytics store: selected simulation, query filters, export format
- [ ] Settings store: user preferences, theme, admin key
- [ ] Each store has normalized state with selectors
- [ ] Middleware for persistence (localStorage)
- [ ] Dev tools integration (Redux DevTools)

**Deliverables**:
- `src/lib/state/stores/simulationStore.ts`
- `src/lib/state/stores/designerStore.ts`
- `src/lib/state/stores/analyticsStore.ts`
- `src/lib/state/stores/settingsStore.ts`
- `src/lib/state/middleware/persistence.ts`
- `src/lib/state/middleware/devtools.ts`
- Tests for each store (state shape, selectors, actions)

**Deliverable Specs**:

**Simulation Store**:
```typescript
// State shape (normalized)
{
  runs: Record<string, SimulationRun>,
  selectedRunId: string | null,
  filters: { status, dateRange, hazardType },
  timeline: { frame, isPlaying },
  results: Record<string, SimulationResults>, // cached
}

// Selectors
- selectedRun(): SimulationRun | null
- filteredRuns(): SimulationRun[]
- timelineProgress(): number
- egressMetrics(): Metrics
```

**Designer Store**:
```typescript
{
  floorPlanId: string | null,
  floorPlan: FloorPlan | null,
  exits: Exit[],
  annotations: Annotation[],
  editMode: 'view' | 'edit',
  selectedExitId: string | null,
}

// Selectors
- exits(): Exit[]
- selectedExit(): Exit | null
- isDirty(): boolean
```

**Analytics Store**:
```typescript
{
  selectedSimulationId: string | null,
  queryResults: AnalyticsQuery | null,
  filters: { metric, timeRange, cohort },
  exportFormat: 'csv' | 'json',
}

// Selectors
- metrics(): Metrics[]
- canExport(): boolean
```

**Handoff Checklist**:
- [ ] All stores have 80%+ test coverage
- [ ] Selectors prevent unnecessary re-renders
- [ ] Redux DevTools shows state updates
- [ ] Persistence works (refresh page, state persists)

---

#### Task 3.2: Redux DevTools Integration & Debugging
**Objective**: Set up DevTools for state debugging  
**Acceptance Criteria**:
- [ ] Redux DevTools browser extension works with all stores
- [ ] Time-travel debugging available
- [ ] Action history visible
- [ ] Middleware logging shows state transitions
- [ ] Devtools config in dev environment only (not prod)

**Deliverables**:
- DevTools middleware implementation
- `src/lib/state/middleware/devtools.ts`
- Documentation on debugging workflow

**Handoff Checklist**:
- [ ] Redux DevTools extension loaded
- [ ] State tree visible in extension
- [ ] Time-travel works without breaking app

---

#### Task 3.3: State Validation & TypeScript
**Objective**: Ensure state types and actions are type-safe  
**Acceptance Criteria**:
- [ ] All state actions typed (no `any`)
- [ ] Selectors have inferred return types
- [ ] Store factory function exports typed hooks
- [ ] TypeScript strict mode passes

**Deliverables**:
- Type definitions for all stores
- Export hooks: `useSimulationStore()`, etc.
- Tests validating types

**Handoff Checklist**:
- [ ] `tsc --noEmit` passes (no type errors)
- [ ] All store imports are typed correctly

---

#### Task 3.4: Store Synchronization with API
**Objective**: Design patterns for syncing stores with backend  
**Acceptance Criteria**:
- [ ] When API mutation succeeds, store auto-updates
- [ ] Optimistic updates for performance
- [ ] Stale state invalidation pattern
- [ ] Load states (loading, error, success)
- [ ] Retry logic for failed mutations

**Deliverables**:
- `src/lib/state/utils/syncUtils.ts` - Store sync patterns
- Examples in stores for API integration
- Documentation of sync patterns

**Handoff Checklist**:
- [ ] Stores can be hydrated from API
- [ ] Mutations update stores optimistically
- [ ] Error states roll back optimistic changes

---

## SPECIALIST 4: Frontend Specialist (Forms & Integration Lead)
### Phase 3b: Forms System (Weeks 8-9)

**Total Effort**: 2 weeks | **Priority**: HIGH (enables designer and operations features)  
**Prerequisite**: Tasks 2.1-2.5 complete, Task 3.1-3.4 complete

#### Task 4.1: Zod Schema Definitions
**Objective**: Define type-safe form and API schemas  
**Acceptance Criteria**:
- [ ] Schema for floor plan upload
- [ ] Schema for exit configuration
- [ ] Schema for scenario creation
- [ ] Schema for simulation controls
- [ ] Schema for operations/admin commands
- [ ] Schemas validate on both client and server
- [ ] Type extraction from schemas (TypeScript)

**Deliverables**:
- `src/lib/forms/schemas/`
- `floorPlanSchema.ts`
- `exitConfigSchema.ts`
- `scenarioSchema.ts`
- `simulationSchema.ts`
- `operationsSchema.ts`
- Schema documentation

**Handoff Checklist**:
- [ ] All schemas pass Zod validation
- [ ] TypeScript types derived from schemas (type inference)

---

#### Task 4.2: React Hook Form Integration
**Objective**: Create reusable form wrappers for UI components  
**Acceptance Criteria**:
- [ ] FormProvider setup (error handling, submission)
- [ ] Controlled Input wrapper with RHF
- [ ] Controlled Select wrapper
- [ ] Controlled Checkbox/Radio wrappers
- [ ] Form submission error display
- [ ] Form state feedback (submission, errors)

**Deliverables**:
- `src/lib/forms/hooks/useForm.ts` (custom hook)
- `src/components/forms/FormField.tsx` (RHF + UI component wrapper)
- `src/components/forms/FormSubmitButton.tsx`
- `src/components/forms/FormError.tsx`
- Tests for form integration

**Handoff Checklist**:
- [ ] Forms work with both Zod and custom validators
- [ ] Error messages display correctly
- [ ] Submit button disabled during submission

---

#### Task 4.3: Multi-Step Forms
**Objective**: Build stepper form pattern for complex workflows  
**Acceptance Criteria**:
- [ ] MultiStepForm component
- [ ] Step validation (each step validated before advancing)
- [ ] Step state persistence (store or localStorage)
- [ ] Back/Next navigation
- [ ] Summary page before final submission
- [ ] Progress indicator (Stepper component)

**Deliverables**:
- `src/components/forms/MultiStepForm.tsx`
- `src/components/forms/FormStep.tsx`
- Example: Designer multi-step form
- Tests for step navigation and validation

**Handoff Checklist**:
- [ ] Steps can't be skipped (validation required)
- [ ] State persists if user navigates away
- [ ] Final submission collects all step data

---

#### Task 4.4: Form Hook Libraries
**Objective**: Create custom hooks for common form patterns  
**Acceptance Criteria**:
- [ ] `useFormState()` - for managing complex form states
- [ ] `useFieldArray()` - for dynamic field lists
- [ ] `useFormValidation()` - for async validation (e.g., checking floor plan exists)
- [ ] `useFormDebounce()` - for debounced submissions
- [ ] `useFormErrors()` - for error display and recovery

**Deliverables**:
- `src/lib/forms/hooks/`
- Custom hooks with JSDoc documentation
- Tests for each hook

**Handoff Checklist**:
- [ ] All hooks exported and typed correctly
- [ ] Hooks have >80% test coverage

---

#### Task 4.5: API Response Validation
**Objective**: Validate API responses with Zod at client boundary  
**Acceptance Criteria**:
- [ ] API client validates all responses against schemas
- [ ] Type-safe response handling in components
- [ ] Failed validation captured (logging, error handling)
- [ ] Graceful fallback for schema mismatches

**Deliverables**:
- Update `src/lib/api/client.ts` to validate responses
- `src/lib/api/schemas/` - Response schemas
- Example integration in a feature

**Handoff Checklist**:
- [ ] All API calls validate responses
- [ ] Type safety from API response → component

---

## SPECIALIST 5: Frontend Specialist (Feature Migration Lead)
### Phase 3c & 4a: Feature Migration (Weeks 9-11)

**Total Effort**: 3 weeks | **Priority**: HIGH (enables new features)  
**Prerequisite**: All Phase 2 complete, Phase 3a-3b started

#### Task 5.1: Designer Feature Migration (Week 9)
**Objective**: Refactor designer to use new systems  
**Acceptance Criteria**:
- [ ] Uses DesignerStore (state management)
- [ ] Uses new Button, Input, FormGroup components
- [ ] Uses new Modal for confirmations
- [ ] Uses MultiStepForm for exit configuration
- [ ] Uses Zod schemas for validation
- [ ] All integration tests passing

**Deliverables**:
- Refactored `src/features/designer/DesignerPage.tsx`
- Updated `src/features/designer/FloorPlanUploadPanel.tsx`
- Updated `src/features/designer/ExitConfigPanel.tsx`
- New tests: `src/features/designer/*.test.tsx`

**Handoff Checklist**:
- [ ] Designer functionality unchanged (regression tests pass)
- [ ] No hardcoded styles (all from design system)
- [ ] Component tests 80%+ coverage

---

#### Task 5.2: Operations Feature Migration (Week 9-10)
**Objective**: Refactor operations page for new form system  
**Acceptance Criteria**:
- [ ] All operations commands use new components
- [ ] Admin key input uses new Input component
- [ ] Operations forms use Zod validation
- [ ] Response display uses new layout components
- [ ] Loading/error states consistent

**Deliverables**:
- Refactored `src/features/operations/OperationsPage.tsx`
- Zod schema for operations commands
- Tests for operations page

**Handoff Checklist**:
- [ ] All operations working (API calls correct)
- [ ] Form validation prevents invalid submissions

---

#### Task 5.3: Simulation Feature Migration (Week 10)
**Objective**: Migrate simulation to use SimulationStore + new components  
**Acceptance Criteria**:
- [ ] Uses SimulationStore (state, selectors)
- [ ] Timeline uses new components
- [ ] Controls use new Button, Input components
- [ ] Canvas rendering unchanged (no visual changes)
- [ ] WebSocket integration with store

**Deliverables**:
- Refactored `src/features/simulation/SimulationHubPage.tsx`
- Refactored `src/features/simulation/SimulationControls.tsx`
- Store integration tests

**Handoff Checklist**:
- [ ] Simulation playback works end-to-end
- [ ] WebSocket updates reflect in store
- [ ] State persists across navigations

---

#### Task 5.4: Analytics Feature Migration (Week 10)
**Objective**: Migrate analytics to use AnalyticsStore + new components  
**Acceptance Criteria**:
- [ ] Uses AnalyticsStore (filters, export settings)
- [ ] Tabs use new Tab component
- [ ] Filter forms use new FormGroup
- [ ] Export buttons use new Button
- [ ] Charts responsive with new layout

**Deliverables**:
- Refactored `src/features/analytics/AnalyticsHubPage.tsx`
- Updated tabs and filter forms
- Store integration

**Handoff Checklist**:
- [ ] Analytics queries work end-to-end
- [ ] Export formats correct (CSV, JSON)
- [ ] Filters are reactive

---

#### Task 5.5: Scenarios & Home Features Migration (Week 11)
**Objective**: Quick migration of remaining features  
**Acceptance Criteria**:
- [ ] Scenarios feature uses new components
- [ ] Home feature navs to new routes correctly
- [ ] All features have 70%+ test coverage
- [ ] No broken links or missing navigation

**Deliverables**:
- Refactored `src/features/scenarios/ScenarioBuilderPage.tsx`
- Refactored `src/features/home/HomePage.tsx`
- Integration tests for all features

**Handoff Checklist**:
- [ ] All 6 features refactored
- [ ] Navigation working end-to-end
- [ ] Visual regression tests passing

---

## SPECIALIST 6: Frontend Specialist (Testing & Performance Lead)
### Phase 4b: E2E Testing & Optimization (Weeks 11-12)

**Total Effort**: 2 weeks | **Priority**: CRITICAL (validation before production)  
**Prerequisite**: All features migrated

#### Task 6.1: E2E Test Scenarios
**Objective**: Write comprehensive Playwright tests  
**Acceptance Criteria**:
- [ ] 15+ E2E scenarios covering all features
- [ ] Happy path: create simulation → run → view results
- [ ] Designer: upload floor plan → configure exits → validate
- [ ] Analytics: query results → filter → export
- [ ] Operations: execute commands, validate responses
- [ ] Error scenarios: invalid inputs, network errors, auth failures
- [ ] All tests pass consistently (no flakiness)

**Test Scenarios**:
1. Create and run a simulation (happy path)
2. Upload floor plan with invalid file (error handling)
3. Configure exits and save (multi-step)
4. View analytics and export CSV
5. Run operations command with admin key
6. Create custom scenario
7. Filter simulations by status
8. Switch between pages without errors
9. Admin key persistence check
10. WebSocket connection/reconnection
11. Form validation and error display
12. Multi-step form abort and resume
13. Logout and re-login (if auth added)
14. Theme switching (light/dark)
15. Mobile responsiveness checks

**Deliverables**:
- `tests/e2e/` - Playwright test files
- `tests/e2e/fixtures/` - Test helpers (login, setup)
- `playwright.config.ts` - Updated config
- CI/CD integration (GitHub Actions)

**Handoff Checklist**:
- [ ] All 15 scenarios passing
- [ ] Tests run in CI/CD
- [ ] Test reports generated
- [ ] No flaky tests (run 3x, all pass)

---

#### Task 6.2: Accessibility Audit & Fixes
**Objective**: Ensure WCAG 2.1 AA compliance  
**Acceptance Criteria**:
- [ ] Axe accessibility scan on all pages: 0 violations
- [ ] Manual keyboard navigation test
- [ ] Screen reader test (NVDA, JAWS, or macOS VoiceOver)
- [ ] Focus management correct in modals and forms
- [ ] Color contrast 4.5:1 for all text
- [ ] ARIA labels and descriptions where needed
- [ ] Form inputs linked to labels (`htmlFor`)
- [ ] Alt text for images

**Audit Process**:
- [ ] Automated scan (Axe DevTools)
- [ ] Manual keyboard navigation
- [ ] Screen reader testing
- [ ] fix critical issues (violations)
- [ ] fix major issues (warnings)

**Deliverables**:
- Accessibility audit report
- Fixed components (if violations found)
- Accessibility documentation

**Handoff Checklist**:
- [ ] Axe scan: 0 violations (all pages)
- [ ] Keyboard navigation test: all features accessible
- [ ] WCAG 2.1 AA compliant

---

#### Task 6.3: Performance Profiling & Optimization
**Objective**: Optimize build, runtime, and user metrics  
**Acceptance Criteria**:
- [ ] Lighthouse score 85+
- [ ] FCP (First Contentful Paint) < 2s
- [ ] LCP (Largest Contentful Paint) < 3s
- [ ] Build size < 500KB gzipped
- [ ] Bundle analysis showing no unused imports
- [ ] Code splitting by route
- [ ] React Query cache optimization

**Optimization Steps**:
1. Profile with Lighthouse, DevTools
2. Identify bottlenecks (render, network, compute)
3. Code splitting (lazy routes)
4. React Query cache tuning
5. Minify/compress assets
6. Remove unused dependencies

**Deliverables**:
- Performance budget in `package.json` (`bundlesize`)
- Bundle analysis report
- Lighthouse reports
- Optimization guide

**Handoff Checklist**:
- [ ] Lighthouse 85+
- [ ] FCP < 2s, LCP < 3s
- [ ] Bundle < 500KB gzipped
- [ ] Performance budget enforced in CI

---

#### Task 6.4: Regression Testing & Visual Snapshots
**Objective**: Prevent visual regressions during future changes  
**Acceptance Criteria**:
- [ ] Snapshot tests for all pages
- [ ] Visual regression tests (Percy or similar)
- [ ] Component snapshot tests
- [ ] All snapshots approved and committed

**Deliverables**:
- `src/**/__snapshots__/` - Jest snapshots
- Percy configuration (if using visual testing)
- Visual regression CI integration

**Handoff Checklist**:
- [ ] Snapshots committed to repo
- [ ] CI checks for snapshot changes

---

#### Task 6.5: Production Readiness Checklist
**Objective**: Validate everything before go-live  
**Acceptance Criteria**:
- [ ] All tests passing (unit, integration, E2E)
- [ ] Accessibility audit passed
- [ ] Performance budgets met
- [ ] Build succeeds (prod build tested)
- [ ] Environment variables documented
- [ ] Error handling and logging correct
- [ ] Analytics/monitoring set up
- [ ] Deployment plan documented

**Deliverables**:
- `PRODUCTION_CHECKLIST.md`
- Deployment guide
- Rollback plan
- Monitoring dashboard setup

**Handoff Checklist**:
- [ ] All boxes checked
- [ ] Stakeholder sign-off received

---

## COORDINATOR: Integration Agent
### Overall Orchestration

**Responsibilities**:
- Track all phases and specialist progress
- Identify blockers and escalate
- Manage cross-specialist dependencies
- Ensure handoffs happen on time
- Weekly sync with all specialists
- Update roadmap and communicate timeline

**Weekly Sync Topics**:
1. What's done this week?
2. What's blocked?
3. Are dependencies on track?
4. Is next phase ready to start?
5. Any design/architecture concerns?

**Escalation Triggers**:
- Specialist 2+ weeks behind
- Design system not meeting accessibility standards
- Component library not meeting test coverage (80%+)
- E2E tests failing consistently
- Performance budget not met

**Deliverables**:
- Weekly status report
- Master roadmap (Gantt chart)
- Blocker resolution log
- Final go/no-go decision for production

---

## Communication & Handoff Protocol

**During Phase**:
- Specialists work in parallel (where dependencies allow)
- Daily standup (async): Slack/email status
- Issues resolved in Slack #frontend-renovation channel

**At Phase End**:
- Specialist presents deliverables to Integration Agent
- Integration Agent reviews against acceptance criteria
- Sign-off checklist completed
- Next phase kicks off (or blocked if critical items missing)

**Blocker Escalation**:
- First try: resolve between specialists in Slack
- If unresolved after 2 hours: Integration Agent mediates
- If design/arch issue: escalate to God Mode Workflow Architect

---

## Success Metrics (Definition of Done)

**Phase 1 Done**: Design system complete, all tokens defined, Storybook ready
**Phase 2 Done**: 20+ components built, 90%+ test coverage, all stories in Storybook
**Phase 3 Done**: Stores architected, forms system working, 50% of features migrated
**Phase 4 Done**: All features migrated, E2E tests green, Lighthouse 85+, accessibility passed

**Overall Done**: Production ready, all tests passing, stakeholder sign-off

