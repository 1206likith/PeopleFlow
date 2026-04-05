# Frontend Renovation: Integration Agent Playbook

**Coordinator**: Integration Agent  
**Start Date**: [Your decision]  
**Target Completion**: 12 weeks  
**Status**: Ready for kickoff

---

## Your Job as Integration Agent

You are responsible for orchestrating 6 Frontend Specialists across 4 phases to deliver a modern, scalable frontend. You don't code; you **coordinate, unblock, and ensure coherence**.

Think of yourself as a conductor ensuring all specialists play in harmony.

---

## Pre-Kickoff Checklist

Before starting any work, complete these:

- [ ] **Team alignment meeting** (30 min)
  - Review this playbook with all specialists
  - Confirm everyone understands their phase and tasks
  - Identify any concerns or unknowns upfront

- [ ] **Shared tools setup**
  - [ ] Slack channel: `#frontend-renovation`
  - [ ] Figma/design collaboration area (if needed)
  - [ ] GitHub project board with phases as columns
  - [ ] Weekly sync calendar (every Tuesday 2 PM, 30 min)

- [ ] **Repository setup**
  - [ ] Create branch `feature/frontend-modernization` (don't merge until fully done)
  - [ ] Add workflow docs to `docs/workflows/`
  - [ ] Ensure CI/CD configured (tests run on PR)

- [ ] **Stakeholder communication**
  - [ ] Notify backend team: frontend may break temporarily during refactor
  - [ ] Notify ops: plan for staging deployment to test
  - [ ] Set expectations: 12 weeks, iterative rollout

---

## Phase-by-Phase Coordinator Responsibilities

### PHASE 1: Design System (Weeks 1-3)
**Lead Specialist**: Frontend Specialist A1 (Design System)  
**Your Role**: Validate, accelerate, unblock

**Week 1 Checkpoint** (Fri, 3pm):
- [ ] Verify: Token taxonomy defined (colors, spacing, typography)
- [ ] Check: Figma design system aligned with token spec (if applicable)
- [ ] Unblock: If color choices unclear, facilitate design decision
- [ ] Output: `src/lib/design/tokens.ts` ready for code review

**Week 2 Checkpoint**:
- [ ] Verify: Tailwind config generates correct CSS
- [ ] Check: CSS variables rendering in DevTools
- [ ] Test: Theme switching works locally
- [ ] Output: `styles/` folder complete with themes

**Week 3 Checkpoint**:
- [ ] Verify: Storybook loads and displays tokens
- [ ] Check: WCAG contrast scores for all colors (should pass AA)
- [ ] Validate: Design team approves palette and token names
- [ ] **GATE**: Phase 1 sign-off (proceed to Phase 2 only if approved)

**If blocked**:
- Color choices not approved? → Escalate to design/product lead for decision
- WCAG issues? → Work with specialist to adjust palette
- Storybook config broken? → Consult Storybook docs, escalate if needed

---

### PHASE 2: Component Library (Weeks 4-6)
**Lead Specialist**: Frontend Specialist A2 (UI Components)  
**Supporting**: A3 (Layout), A0 (Arch)  
**Your Role**: Track coverage, ensure quality bar

**Weekly Checkpoints**:

**Week 4** (Core Components):
- [ ] Verify: Button, Input, Badge, Spinner implemented
- [ ] Check: 90%+ test coverage for each (run `npm run test`)
- [ ] Review: Tests cover variants (primary, secondary, disabled, loading)
- [ ] Output: 4 components ready, Storybook stories updated

**Week 5** (Form Components):
- [ ] Verify: FormGroup, Select, Checkbox, Radio, FileInput, TextArea done
- [ ] Check: All components work with React Hook Form
- [ ] Review: Accessibility audit pass (focus, ARIA labels, keyboard nav)
- [ ] Output: 6 form components ready, all accessible

**Week 6** (Complex + Layout Components):
- [ ] Verify: Modal, Dialog, Tabs, Alert, Card, Stack/Flex/Grid done
- [ ] Check: Modal focus trap working, Tabs keyboard nav working
- [ ] Review: All 20 components in Storybook with full stories
- [ ] Audit: Run Axe DevTools on each component in Storybook (0 violations)
- [ ] **GATE**: Component library complete and tested

**Quality Bar** (Don't proceed without):
- [ ] 90%+ test coverage across all components
- [ ] All components in Storybook with 3+ story variants
- [ ] Accessibility audit pass (0 critical violations)
- [ ] No hardcoded colors or spacing (all from tokens)

**If behind schedule**:
- Deprioritize compound components (Task 2.4) → Ship in Phase 3b
- Extend Phase 2 to Week 7 if needed (delays Phase 3, but better quality)

---

### PHASE 3: State & Forms (Weeks 7-9)
**Lead Specialist**: Frontend Specialist A4 (State) + A5 (Forms)  
**Supporting**: A6 (Feature Integration)  
**Your Role**: Coordinate dependency handoff

**Week 7** (State Management):
- [ ] Verify: 4 Zustand stores implemented (simulation, designer, analytics, settings)
- [ ] Check: Redux DevTools extension working
- [ ] Review: Store tests 80%+ coverage
- [ ] Output: State architecture complete, ready for consumption

**Week 8** (Forms):
- [ ] Verify: Zod schemas defined for all forms
- [ ] Check: React Hook Form integration working with UI components
- [ ] Review: MultiStepForm component working
- [ ] Output: Form system ready for feature migration

**Week 9** (Feature Migration - Part 1):
- [ ] Verify: Designer feature migrated (uses DesignerStore + forms)
- [ ] Check: Operations page migrated (uses new form system)
- [ ] Review: Integration tests passing for both features
- [ ] Output: 2/6 features refactored

**Dependency Management**:
- Week 7: State specialist does NOT need component lib yet (use default styles)
- Week 8: Forms specialist starts **as soon as** state is ready (some overlap OK)
- Week 9: Feature integration specialist depends on BOTH state + forms (hard dependency)

**If blocked**:
- Store design unclear? → Whiteboard with specialist, document pattern
- Form integration failing? → Debug RHF integration, add logging
- Feature migration failing? → Pair program with specialist if different person

---

### PHASE 4: Integration & Testing (Weeks 10-12)
**Lead Specialist**: Frontend Specialist A6 (Feature Migration) + A7 (Testing)  
**Your Role**: Final validation and go-live gate

**Week 10** (Feature Migration - Part 2):
- [ ] Verify: Simulation, Analytics, Scenarios, Home features migrated
- [ ] Check: All 6 features tested (integration tests green)
- [ ] Review: No visual regressions (manual check or visual regression tool)
- [ ] Output: All features on new stack

**Week 11** (E2E & Accessibility):
- [ ] Verify: 15+ E2E test scenarios written and passing
- [ ] Check: Axe accessibility scan passing on all pages (0 violations)
- [ ] Review: Screen reader testing done (manual)
- [ ] Output: E2E test suite ready, accessibility certified

**Week 12** (Performance & Production Readiness):
- [ ] Verify: Lighthouse score 85+ on all pages
- [ ] Check: FCP < 2s, LCP < 3s (measure on staging)
- [ ] Review: Bundle size < 500KB gzipped
- [ ] Output: Production readiness checklist completed
- [ ] **GATE**: Go/no-go decision for production deployment

**Final Sign-Off Requirements**:
- [ ] All manual tests pass
- [ ] E2E tests green
- [ ] Accessibility audit pass
- [ ] Performance budgets met
- [ ] Stakeholder approval (backend, ops, design)
- [ ] Rollback plan documented

**If not ready**:
- Fix issues in staging → Re-validate → Re-gate
- Do NOT merge to main or deploy until all gates pass

---

## Weekly Sync Agenda (30 min every Tuesday)

**Attendees**: All 6 specialists + Integration Agent (you)

**Agenda**:
1. **(5 min) Weekly status** - Each specialist: what's done, what's next
2. **(10 min) Blockers** - Any blocker affecting progress?
3. **(10 min) Dependencies** - Are cross-specialist handoffs on track?
4. **(5 min) Course correction** - Address any phase delays
5. **(Optional) Deep dive** - If complex issue needs 30+ min, schedule separate meeting

**Action Items**:
- Document decisions in Slack thread
- Update GitHub project board
- Post weekly summary to `#frontend-renovation`

---

## Blocker Resolution Playbook

**When a specialist is blocked** (can't proceed):

1. **First Response** (same day):
   - Understand the block (ask "what's stopping you?")
   - Is it a dependency on another specialist? → Coordinate with them
   - Is it a technical problem? → Offer to pair program or consult
   - Is it a design decision? → Escalate to God Mode Workflow Architect

2. **Escalation Triggers** (>2 hours blocked):
   - Specialist can't resolve → You (Integration Agent) mediates
   - Blocked on architecture decision → Escalate to God Mode Workflow Architect
   - Blocked on design → Escalate to product/design lead

3. **Documentation**:
   - Log blockers in `#frontend-renovation` Slack
   - Update GitHub issue with "blocked" label
   - Track resolution time (SLA: 24 hours to unblock)

**Example Blocks & Resolutions**:
- *"Form integration failing with RHF"* → You: debug together, check docs, escalate if needed
- *"Design system colors not meeting contrast"* → You: facilitate designer decision, iterate palette
- *"E2E test flaky"* → You: help add explicit waits, retry strategy, pair test writing

---

## Quality Gates (Don't Skip!)

**These are hard gates** - don't proceed without. If a gate is not met, the phase is not done.

| Gate | Criteria | How to Verify |
|------|----------|---------------|
| **Design System** | WCAG AA contrast pass | Run Axe on component in Storybook |
| **Component Library** | 90%+ test coverage | `npm run test -- --coverage` |
| **Component Library** | 0 accessibility violations | Axe DevTools on all components |
| **State Management** | Redux DevTools integration | Open DevTools, see action history |
| **Forms** | RHF + Zod integration working | Test form with validation errors |
| **Feature Migration** | Visual regressions isolated | Manual comparison or visual tool |
| **E2E Tests** | 15 scenarios passing | `npm run test:e2e` passes |
| **Accessibility** | WCAG 2.1 AA compliance | Full page Axe audit (0 violations) |
| **Performance** | Lighthouse 85+ | Lighthouse report on each route |
| **Bundle** | < 500KB gzipped | `npm run build && bundlesize check` |

**If gate fails**:
1. Understand why (gather metrics/logs)
2. Plan fix (document approach)
3. Assign to specialist
4. Re-test and reverify
5. Only then proceed

---

## Risk Mitigation Strategy

**Risk**: Design System design paralysis  
**Mitigation**: Use current dark theme as baseline; iterate in 1-week sprints, not perfect upfront

**Risk**: Component library bloats with too many variants  
**Mitigation**: Strict prop interface review; only ship variants that are used

**Risk**: State migration breaks features  
**Mitigation**: Ships old and new stores in parallel during migration (toggle via feature flag if needed)

**Risk**: E2E tests flaky  
**Mitigation**: Use explicit waits (not timeouts), test IDs for selectors, run tests locally 3x before committing

**Risk**: Performance budget not met  
**Mitigation**: Profile early (Week 11), address bottlenecks incrementally, don't wait until Week 12

**Risk**: Unplanned changes mid-project  
**Mitigation**: Freeze scope for 12 weeks; document feature requests for Phase 2 (next iteration)

---

## Communication Strategy

**Daily** (Async, Slack):
- Post status in `#frontend-renovation` thread (format: **Done** | **Today** | **Blocked?**)
- Link to PR/commit if pushing code

**Weekly** (Sync):
- 30-min sync (Tue 2 PM) with all specialists
- Document decisions and action items

**Bi-weekly** (Status to Stakeholders):
- Email summary: completed features, timeline, risks
- Attach screenshots if significant visual changes

**Monthly** (Presentation):
- Show progress to design/product/engineering leads
- Demo completed features
- Discuss plan for next month

---

## Definition of Success

**You succeed if**:
- ✅ All phases complete on time (or minor slip < 1 week)
- ✅ Quality gates met (no compromises)
- ✅ All tests passing (unit, integration, E2E, accessibility)
- ✅ Stakeholders happy (design, backend, ops, product)
- ✅ No regressions (old functionality works the same)
- ✅ Team morale high (reasonable pace, no crunch)

**You failed if**:
- ❌ Phases slip >2 weeks without recovery plan
- ❌ Quality gates compromised (shipped with known violations)
- ❌ Tests not passing before merge
- ❌ Production breaks after merge (rollback needed)
- ❌ Team burnout (unsustainable pace)

---

## Preparation Checklist for Kickoff

**1-2 weeks before starting**:
- [ ] Review this playbook with all specialists
- [ ] Confirm all 6 specialists available for duration
- [ ] Set up Slack channel, GitHub project, Figma space
- [ ] Schedule weekly syncs on calendar
- [ ] Brief backend/ops teams on incoming changes
- [ ] Create `feature/frontend-modernization` branch
- [ ] Prepare design tokens initial sketch (based on current theme)
- [ ] List all forms that need Zod schemas
- [ ] Identify E2E test scenarios
- [ ] Collect performance baselines (run Lighthouse on current frontend)

**Day 1 of Kickoff**:
- [ ] Team standup: Review playbook together
- [ ] Specialist A1 starts Task 1.1 (token design)
- [ ] Post kickoff announcement to `#frontend-renovation`
- [ ] First weekly sync scheduled

---

## Escalation Contacts

| Scenario | Escalate To | How | Urgency |
|----------|-------------|-----|---------|
| Design decision blocked | Product/Design Lead | Slack, schedule call | High |
| Architecture question | God Mode Workflow Architect | Tag in Slack or schedule 1:1 | High |
| Specialist unavailable | Team Lead | ASAP | Critical |
| Performance issue unknown | Backend Lead | Slack, investigate together | Medium |
| Accessibility question | A11y specialist | Slack, pair on fix | Medium |

---

## Next Steps: How to Start

**RIGHT NOW**:
1. Print/save this playbook (all 3 docs: WORKFLOW, TASKS, this PLAYBOOK)
2. Share with all 6 specialists
3. Schedule kickoff meeting (2 hrs): review + Q&A
4. Set up Slack channel and GitHub project
5. Confirm everyone available for 12 weeks

**Week 1 Kickoff**:
1. Monday: Team standup (1 hr)
2. Tuesday: First weekly sync (30 min)
3. Specialist A1 starts Task 1.1 (design tokens)
4. Post updates daily in Slack

**Your first 30 days**:
- Check in with each specialist daily (async or Slack)
- Facilitate dependencies (e.g., when A3 needs tokens from A1)
- Unblock any issues within 24 hours
- Update stakeholders with weekly status
- Track progress on GitHub project board

---

## Final Note

You're not coding; you're **enabling**. Your job is to remove friction, clarify ambiguity, and keep the team moving forward.

**Be decisive**:
- If a specialist is uncertain, help them decide
- If a blocker arises, solve it (or escalate if needed)
- If timeline slips, adjust plan and communicate changes

**Celebrate wins**:
- Phase 1 done? → Celebrate design system launch
- All components shipped? → Celebrate component library
- Features migrated? → Celebrate progress
- Go-live? → Celebrate shipping!

**You've got this.** 🚀

---

**Document Versions**:
- Workflow: `FRONTEND_RENOVATION_WORKFLOW.md`
- Tasks: `FRONTEND_RENOVATION_TASKS.md`
- This Playbook: `FRONTEND_RENOVATION_PLAYBOOK.md`

All in `docs/workflows/`

