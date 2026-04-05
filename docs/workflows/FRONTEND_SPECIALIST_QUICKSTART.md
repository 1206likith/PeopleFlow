# Frontend Renovation: Specialist Quick Start Guide

**Print this and keep it open while working.**

---

## For Every Specialist

### Before You Start
- [ ] Read assign section in `FRONTEND_RENOVATION_TASKS.md`
- [ ] Understand your tasks and acceptance criteria
- [ ] Know your handoff dependencies (next specialist after you)
- [ ] Join `#frontend-renovation` Slack channel
- [ ] Attend kickoff meeting (Tuesday 2 PM)

### Daily Workflow
1. **Morning**: Check blockers - post standup in Slack (3 min)
   - Format: "Done: X | Today: Y | Blocked: Z (or none)"
2. **Work**: Execute your tasks for the week
3. **As needed**: Communicate with other specialists
   - Questions? → Ask in Slack
   - Blocker? → Escalate to Integration Agent (tag @integration)
4. **Friday 3pm**: Weekly checkpoint with Integration Agent (30 min sync)

### Code Quality Standards
- **Tests**: 80%+ coverage minimum, `npm run test -- --coverage`
- **TypeScript**: No `any` types, `tsc --noEmit` passes
- **Accessibility**: Axe audit 0 violations (critical)
- **Code Review**: Two approvals before merge

### Commit & PR Workflow
```bash
# Create branch for your task
git checkout -b feat/[your-task-name]

# Work, test, commit
git add .
git commit -m "Task X.Y: [description]"

# Push and create PR
git push origin feat/[your-task-name]
# Go to GitHub, create PR with description + # of acceptance criteria checked

# After 2 approvals, merge to feature/frontend-modernization
git merge [your-branch]
```

- **PR Template**: Describe task, link acceptance criteria, attach screenshots (if UI)
- **Review Groups**: Component specialists review each other, state lead reviews forms lead
- **Merge policy**: All checks pass + 2 approvals required

---

## Specialist A1: Design System Lead

**Phase**: Week 1-3  
**Tasks**: 1.1 - 1.5 (5 tasks)  
**Success**: All tokens defined, Tailwind working, Storybook ready

### Your First Week
1. **Day 1-2**: Define token taxonomy (Task 1.1)
   - Colors: semantic tokens (primary, secondary, danger, etc.)
   - Spacing: 4px base multiples (4, 8, 12, 16, 24, 32, 48, 64)
   - Typography: 6-8 sizes (xs: 12px → 2xl: 32px)
   - Shadows, radii, durations
   - Deliverable: `src/lib/design/tokens.ts`

2. **Day 3-5**: Tailwind integration (Task 1.2)
   - Update `tailwind.config.js` to reference tokens
   - Create CSS custom properties in `styles/variables.css`
   - Create theme variants (light, dark, high-contrast)
   - Test: `npm run build`, check colors in browser

3. **Friday**: Checkpoint with Integration Agent
   - Verify tokens exported and type-safe
   - Issue any clarifications for next task

### Key Resources
- Current theme: `tailwind.config.js` (existing colors, spacing)
- Tailwind docs: https://tailwindcss.com/docs/content-configuration
- WCAG contrast checker: https://webaim.org/resources/contrastchecker/
- Figma (if applicable): [Design system file link]

### When You're Done
- [ ] All tokens in `src/lib/design/tokens.ts` (TypeScript)
- [ ] Tailwind config uses tokens (no hardcoded values)
- [ ] CSS variables working (`npm run build`, colors visible)
- [ ] WCAG AA contrast passes for all text combinations
- [ ] Storybook showing design token page

### Handoff to A2 (Component Library Lead)
- All tokens finalized
- Tailwind config stable
- Storybook ready to showcase components

---

## Specialist A2: UI Component Library Lead

**Phase**: Week 4-6  
**Tasks**: 2.1 - 2.6 (6 tasks, 20+ components)  
**Success**: Component library complete, tested, in Storybook

### Your First Week (Week 4)
1. **Task 2.1**: Core components (Button, Input, Badge, Spinner)
   - Create `src/components/ui/Button/` folder
   - Implement component, tests, Storybook story
   - Repeat for Input, Badge, Spinner
   - Tests must have 90%+ coverage

2. **Key Pattern** (copy this for each component):
   ```
   src/components/ui/Button/
   ├── Button.tsx (component)
   ├── Button.test.tsx (tests)
   ├── Button.stories.tsx (Storybook)
   └── index.ts (export)
   ```

3. **Testing Template**:
   ```typescript
   // Button.test.tsx
   import { render, screen } from '@testing-library/react';
   import { Button } from './Button';

   describe('Button', () => {
     it('renders primary variant', () => {
       render(<Button variant="primary">Click me</Button>);
       expect(screen.getByRole('button')).toBeInTheDocument();
     });
     // ... more tests for each variant
   });
   ```

4. **Storybook Template**:
   ```typescript
   // Button.stories.tsx
   import { Button } from './Button';

   export default {
     title: 'UI/Button',
     component: Button,
   };

   export const Primary = () => <Button variant="primary">Primary</Button>;
   export const Secondary = () => <Button variant="secondary">Secondary</Button>;
   // ... one story per variant
   ```

### Week 5-6
- Task 2.2: Form components (FormGroup, Select, Checkbox, Radio)
- Task 2.3: Complex components (Modal, Tabs, Alert, Card)
- Task 2.4: Compound components (MenuButton, etc.)

### Acceptance Criteria Checklist
- [ ] 20 components implemented
- [ ] 90%+ test coverage per component (`npm run test -- --coverage`)
- [ ] All stories in Storybook
- [ ] Axe audit: 0 violations per component
- [ ] Each component uses design system tokens (no hardcoded colors)
- [ ] TypeScript strict mode: no `any` types

### Key Tools
- Test: `npm run test -- Button.test.tsx`
- Build Storybook: `npm run storybook`
- Check coverage: `npm run test -- --coverage`
- Accessibility: Install Axe DevTools browser extension

### When You're Done
- All components in Storybook
- All tests passing
- A3 can now refactor layout using these components

---

## Specialist A3: Layout & Compound Components Lead

**Phase**: Week 4-6 (parallel with A2)  
**Tasks**: Part of 2.4 - 2.5 (layout refactor)  
**Success**: Layout components refactored, using new design system

### Parallel with A2
- While A2 builds atomic components, you start layout refactor (wait for Button, Input first)
- Refactor `PageShell`, `TopNav`, `SideNav` to use new components
- All colors/spacing from tokens (no hardcoded `#abc123` or `px-12`)

### Dependencies
- Blocked on: Button, Input, Card (wait for A2 to finish Task 2.1)
- Blocks: Nothing (you're supporting)

---

## Specialist A4: State Management Lead

**Phase**: Week 7-8  
**Tasks**: 3.1 - 3.4 (state architecture)  
**Success**: 4 Zustand stores complete, Redux DevTools working

### Your Workflow
1. **Task 3.1**: Design 4 stores (simulation, designer, analytics, settings)
   - Define normalized state shape
   - Create selectors (prevent unnecessary re-renders)
   - Implement actions (type-safe)
   - Add tests (state transitions)

2. **Store Template**:
   ```typescript
   // simulationStore.ts
   import create from 'zustand';

   interface SimulationState {
     runs: Record<string, SimulationRun>;
     selectedRunId: string | null;
     // ... more state
   }

   interface SimulationActions {
     setSelectedRun: (id: string) => void;
     // ... more actions
   }

   export const useSimulationStore = create<SimulationState & SimulationActions>((set, get) => ({
     runs: {},
     selectedRunId: null,
     setSelectedRun: (id: string) => set({ selectedRunId: id }),
     // ... more
   }));

   // Selectors (prevent re-renders)
   export const selectSelectedRun = (state: SimulationState) => 
     state.runs[state.selectedRunId || ''] || null;
   ```

3. **Task 3.2**: Redux DevTools integration
   - Install Redux DevTools browser extension
   - Add middleware to each store
   - Verify state history visible in DevTools

4. **Task 3.3**: Type safety
   - No `any` types
   - Selectors have inferred return types
   - `tsc --noEmit` passes

5. **Task 3.4**: API synchronization
   - When API mutation succeeds, update store
   - Optimistic updates for performance
   - Error handling (rollback)

### Acceptance Criteria
- [ ] 4 stores implemented (simulation, designer, analytics, settings)
- [ ] Each store has 80%+ test coverage
- [ ] Redux DevTools shows state updates
- [ ] All types inferred (no explicit types needed for selectors)
- [ ] Persistence works (localStorage)

### Handoff to A5 (Forms Lead)
- Stores ready for consumption
- Persistence middleware working
- DevTools integration verified

---

## Specialist A5: Forms System Lead

**Phase**: Week 8-9  
**Tasks**: 4.1 - 4.5 (forms + React Hook Form)  
**Success**: Forms working with Zod validation, RHF integrated

### Your Start
- **Blocker**: Task 2.1 (at least Button, Input, FormGroup components) must be done
- **Start**: As soon as A4 has stores ready

### Your Workflow
1. **Task 4.1**: Zod schemas
   - Define schemas for all forms (floor plan, exits, scenarios, operations)
   - Use discriminated unions for complex types
   - Validate on both client and server

2. **Task 4.2**: React Hook Form integration
   - Create form wrappers that connect RHF to UI components
   - Controlled inputs that report validation errors
   - Form submission handling

3. **Task 4.3**: Multi-step forms
   - Implement MultiStepForm component
   - Step validation before advancing
   - State persistence (localStorage or store)

4. **Example**:
   ```typescript
   // floorPlanSchema.ts
   import { z } from 'zod';

   export const floorPlanSchema = z.object({
     name: z.string().min(1, 'Name required'),
     width: z.number().positive(),
     height: z.number().positive(),
     imageFile: z.instanceof(File),
   });

   export type FloorPlan = z.infer<typeof floorPlanSchema>;
   ```

### Acceptance Criteria
- [ ] Zod schemas for all 5 form types
- [ ] RHF integration with UI components
- [ ] MultiStepForm working
- [ ] API responses validated at client boundary
- [ ] All tests passing (80%+ coverage)

### Handoff to A6 (Feature Integration)
- Forms ready to migrate features
- Zod schemas finalized
- RHF patterns documented

---

## Specialist A6: Feature Integration Lead

**Phase**: Week 9-11  
**Tasks**: 5.1 - 5.5 (migrate all 6 features)  
**Success**: All features refactored, working on new stack

### Your Tasks (1 feature per week, roughly)
1. **Week 9**: Designer feature (Task 5.1)
   - Use DesignerStore (state management)
   - Use new components (Button, Input, Card, Modal)
   - Use MultiStepForm for exit config
   - Add tests (80%+ coverage)

2. **Week 9-10**: Operations page (Task 5.2)
   - Use new form system (Zod + RHF)
   - Handle command responses
   - Error display

3. **Week 10**: Simulation feature (Task 5.3)
   - Use SimulationStore
   - WebSocket integration with store
   - Canvas rendering unchanged

4. **Week 10**: Analytics feature (Task 5.4)
   - Use AnalyticsStore
   - Filter forms reactive
   - Export formats correct

5. **Week 11**: Scenarios + Home (Task 5.5)
   - Quick refactor (smaller features)
   - Navigation working properly

### Template for Each Feature
```typescript
// FeaturePage.tsx
import { useFeatureStore } from '@/lib/state/stores/featureStore';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';

export function FeaturePage() {
  const { data, actions } = useFeatureStore();
  
  return (
    <Card>
      <Button onClick={() => actions.doSomething()}>Action</Button>
      {/* ... */}
    </Card>
  );
}
```

### Acceptance Criteria (Per Feature)
- [ ] Feature uses new state store (if applicable)
- [ ] Feature uses new components (no custom-styled divs)
- [ ] Feature has 70%+ test coverage
- [ ] No visual regressions (compare before/after)
- [ ] API calls working end-to-end
- [ ] Accessibility audit pass

### Handoff to A7 (Testing)
- All features migrated
- No broken functionality
- Tests passing

---

## Specialist A7: Testing & Performance Lead

**Phase**: Week 11-12  
**Tasks**: 6.1 - 6.5 (E2E, accessibility, performance)  
**Success**: Production ready, all tests green, budget met

### Your Workflow
1. **Task 6.1**: E2E tests (Playwright)
   - Write 15 test scenarios covering all features
   - Test happy path + error handling
   - Ensure tests are not flaky (explicit waits)

2. **Task 6.2**: Accessibility audit
   - Run Axe on all pages (0 violations)
   - Manual screen reader testing
   - Focus management check

3. **Task 6.3**: Performance
   - Lighthouse score 85+ on all pages
   - FCP < 2s, LCP < 3s
   - Bundle < 500KB gzipped

4. **Task 6.4**: Visual regression tests
   - Snapshot tests for all pages
   - Commit snapshots to repo

5. **Task 6.5**: Production readiness
   - Final checklist (all tests pass, budgets met)
   - Rollback plan
   - Deployment guide

### E2E Test Example
```typescript
// tests/e2e/simulation.spec.ts
import { test, expect } from '@playwright/test';

test('simulation happy path', async ({ page }) => {
  await page.goto('/simulation');
  await page.click('button:has-text("Create")');
  await page.fill('input[name="simulation"]', 'Test Sim');
  await page.click('button:has-text("Run")');
  await expect(page.locator('[data-testid="results"]')).toBeVisible();
});
```

### Acceptance Criteria
- [ ] 15 E2E scenarios passing
- [ ] 0 accessibility violations (Axe)
- [ ] Lighthouse 85+
- [ ] Bundle < 500KB gzipped
- [ ] All manual tests passed

---

## Quick Slack Commands

Post these in `#frontend-renovation` when needed:

**Daily standup**:
```
Done: X component completed and tests passing
Today: Starting Y component
Blocked: None
```

**When blocked**:
```
@integration BLOCKED on [issue]
Details: [what's preventing progress]
Needed by: [when you need it]
```

**When PR ready**:
```
PR: Task X.Y ready for review
Link: [GitHub PR URL]
Acceptance criteria: [checklist]
Screenshots: [if UI change]
```

**Weekly sync reminder**:
Tuesday 2 PM - All specialists + Integration Agent
Agenda: Status | Blockers | Dependencies | Course correction

---

## Contact & Escalation

- **Questions on tasks?** → Post in Slack or ask Integration Agent
- **Blocked?** → Tag @integration in Slack (ASAP)
- **Architecture question?** → Ask Integration Agent, escalate to God Mode if needed
- **Design issue?** → Escalate to product/design lead via Integration Agent

---

## You've Got This! 🚀

Take it task by task. Test as you go. Communicate early if blocked. 

All dates are estimates; quality is not negotiable. If you need more time, say so early.

**Weekly sync Tuesdays at 2 PM** - See you there!

