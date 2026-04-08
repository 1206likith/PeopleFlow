---
name: superpowers
description: Complete workflow framework for AI-driven software development with subagent coordination, test-driven development, and automated code review. Use when developing software features end-to-end, planning complex implementations, debugging issues systematically, or coordinating multi-phase development projects. Essential for professional development workflows.
---

# Superpowers – AI-Driven Development Workflow

## Core Concept

Superpowers provides a complete software development workflow that guides your coding agent through design, planning, implementation, testing, and review—with subagent collaboration, systematic debugging, and quality gates at every step.

## How It Works

1. **Brainstorming** — Refine ideas, explore alternatives, validate design
2. **Git Worktrees** — Create isolated workspace on new branch
3. **Writing Plans** — Break work into bite-sized tasks with exact steps
4. **Subagent-Driven Development** — Execute tasks with automated review
5. **Test-Driven Development** — RED-GREEN-REFACTOR cycle
6. **Code Review** — Automated checks against plan and quality standards
7. **Finishing** — Verify, present options, clean up

## The Basic Workflow

### Phase 1: Brainstorming

**Activation**: Before writing code

**What happens**:
- Agent asks clarifying questions about intent
- Explores alternative approaches
- Presents design in readable sections
- Validates your approval
- Saves design document for reference

**Deliverable**: Approved design doc

### Phase 2: Using Git Worktrees

**Activation**: After design approval

**What happens**:
- Creates isolated workspace on new branch
- Runs project setup (install dependencies, etc.)
- Verifies clean test baseline (all tests pass)
- Confirms ready for development

**Benefits**: 
- Parallel development possible
- Easy rollback if needed
- Clean main branch

### Phase 3: Writing Plans

**Activation**: With approved design

**What happens**:
- Breaks work into bite-sized tasks (2-5 minute implementations)
- Each task has:
  - Exact file paths
  - Complete code to write
  - Verification steps
  - Success criteria
- Plan presented for approval

**Deliverable**: Detailed implementation plan

### Phase 4: Subagent-Driven Development

**Activation**: With approved plan

**What happens**:
- Dispatches fresh subagent per task
- Two-stage review:
  - **Stage 1**: Spec compliance (does it meet task spec?)
  - **Stage 2**: Code quality (is the code good?)
- OR: Batch execution with human checkpoints

**Result**: Completed features with quality assurance

### Phase 5: Test-Driven Development

**Activation**: During implementation

**Enforces RED-GREEN-REFACTOR cycle**:
1. **RED**: Write failing test
2. Watch it fail
3. **GREEN**: Write minimal code
4. Watch test pass
5. **REFACTOR**: Improve code
6. Commit

**Critical**: Code written before tests fails the test phase

### Phase 6: Requesting Code Review

**Activation**: Between tasks

**What is reviewed**:
- Against implementation plan (spec compliance)
- Against team standards (code quality)
- Critical issues block progress
- Minor issues noted for refinement

**Output**: Review report with issue severity

### Phase 7: Finishing Development Branch

**Activation**: When tasks complete

**What happens**:
- Verifies all tests pass
- Presents merge options:
  - Merge to main
  - Create PR
  - Keep branch
  - Discard changes
- Cleans up worktree

## Skills Library

### Testing

- **test-driven-development** — RED-GREEN-REFACTOR cycle with anti-patterns reference
  - What NOT to do in tests
  - Common pitfalls
  - Testing best practices

### Debugging

- **systematic-debugging** — 4-phase root cause process
  - Root-cause-tracing techniques
  - Defense-in-depth strategies
  - Condition-based-waiting patterns
- **verification-before-completion** — Ensure fix actually works

### Collaboration

- **brainstorming** — Socratic design refinement
- **writing-plans** — Detailed implementation plans
- **executing-plans** — Batch execution with checkpoints
- **dispatching-parallel-agents** — Concurrent subagent workflows
- **requesting-code-review** — Pre-review checklist
- **receiving-code-review** — Responding to feedback
- **using-git-worktrees** — Parallel development branches
- **finishing-a-development-branch** — Merge/PR decision workflow
- **subagent-driven-development** — Fast iteration with two-stage review

### Meta

- **writing-skills** — Create new skills following best practices (includes testing methodology)
- **using-superpowers** — Introduction to skills system

## Philosophy

**Core Principles**:
1. **Test-Driven Development** — Always write tests first
2. **Systematic over Ad-Hoc** — Process > guessing
3. **Complexity Reduction** — Simplicity as primary goal
4. **Evidence over Claims** — Verify before declaring success

## Skill Triggering

**The agent checks for relevant skills before any task.** Skills are not suggestions—they're mandatory workflows.

When you ask to:
- "Plan this feature" → **brainstorming** activates
- "Help me debug this" → **systematic-debugging** activates
- "Implement task 3" → **subagent-driven-development** activates
- "Write tests" → **test-driven-development** activates

No manual invocation required—skills activate automatically based on context.

## Usage Patterns

### Pattern 1: Feature Development

```
"I want to build a user dashboard showing recent activity"
↓
brainstorming: Refine requirements, explore designs
↓
writing-plans: Break into tasks
↓
subagent-driven-development: Execute tasks
↓
finishing-a-development-branch: Merge when done
```

### Pattern 2: Bug Fixing

```
"Payments are failing in production"
↓
systematic-debugging: Root cause analysis
↓
Plan fix
↓
writing-plans: Create test-first approach
↓
test-driven-development: Fix with coverage
↓
verification-before-completion: Confirm fix works
```

### Pattern 3: Parallel Development

```
"We need features A, B, and C"
↓
brainstorming: Design all three
↓
using-git-worktrees: Create branch per feature
↓
dispatching-parallel-agents: Three agents work simultaneously
↓
finishing-a-development-branch: Merge each feature
```

## Best Practices

### Design Phase

- Spend time in brainstorming—better design = faster implementation
- Get explicit approval before moving to planning
- Document design decisions (important for reviews)

### Planning Phase

- Create tasks of 2-5 minute implementations
- Be specific about file paths and code changes
- Include clear verification steps
- Plan for common gotchas

### Implementation Phase

- Follow RED-GREEN-REFACTOR strictly
- One task = one PR (or merge)
- Keep commits atomic
- Run full test suite before moving on

### Code Review Phase

- Address critical issues before proceeding
- Fix minor issues before merging to main
- Hold yourself to team quality standards
- Learn from review feedback

### Finishing Phase

- Verify tests still pass after all tasks
- Clean up branches
- Update documentation
- Communicate merge to team

## Systematic Debugging Approach

When **systematic-debugging** activates:

1. **Reproduce** — Consistently trigger the bug
2. **Hypothesize** — Form testable hypothesis about cause
3. **Test** — Design test to verify/refute hypothesis
4. **Verify** — Confirm root cause
5. **Fix** — Implement minimal fix
6. **Verify Again** — Confirm fix resolves issue

Never guess. Always verify.

## Writing Effective Implementation Plans

Good plans include:

**Per task:**
- Clear title
- Exact file paths (src/components/Widget.tsx)
- Complete code to write (not pseudo-code)
- Step-by-step verification (how to test)
- Success criteria (must match spec)

**Example:**
```markdown
## Task 3: Add Delete Button to Widget

File: src/components/Widget.tsx

1. Import DeleteIcon from @/icons
2. Add <button onClick={handleDelete}> with icon
3. Test: Component renders button
4. Test: Clicking fires handleDelete callback
5. Test: Button disabled when id='root'

Verification:
- npm run test passes
- Component renders correctly
- No console errors
```

## When to Use Superpowers

Use Superpowers when:
- Building software features from scratch
- Complex multi-step implementations
- Team development workflows
- Quality is non-negotiable
- Learning effective development processes
- Coordinating multiple agents
- Needs systematic debugging

**Not ideal for:**
- Simple one-line fixes
- Scripting tasks
- Configuration changes (might still activate, but overkill)

## Key Takeaway

Superpowers turns your coding agent from "write some code" into a **professional development workflow**—with design validation, test coverage, quality review, and systematic problem-solving.

The skills don't just execute tasks—they ensure you're building thoughtfully, testing thoroughly, and reviewing carefully.

**Your agent has Superpowers because it follows them automatically. No manual invocation required.**
