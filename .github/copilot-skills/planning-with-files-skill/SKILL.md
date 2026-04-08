---
name: planning-with-files
description: Implements Manus-style persistent markdown planning using three-file pattern (task_plan.md, findings.md, progress.md) for goals persistence and context optimization. Use for multi-step tasks, research projects, complex development workflows, and long-running processes to establish external memory. Works with Claude Code, Cursor, Codex, and 40+ agents.
---

# Planning with Files – Persistent Markdown Memory

## Core Principle

Store goals, progress, and findings in **persistent markdown files**, not volatile context.

```
Context Window = RAM (volatile, limited)
Filesystem = Disk (persistent, unlimited)

→ Anything important gets written to disk.
```

## Why This Pattern Works

**The Problem with Context-Only:**
- Volatile memory — todo lists disappear on context reset
- Goal drift — After 50+ tool calls, original goals get forgotten
- Hidden errors — Failures aren't tracked, repetition happens
- Context stuffing — Everything crammed into context instead of stored

**The Solution: 3-File Pattern**
```markdown
task_plan.md      → Track phases and progress with checkboxes
findings.md       → Store research and findings (unlimited)
progress.md       → Session log and test results
```

This is the pattern that made **Manus worth $2 billion** when Meta acquired it in December 2025.

## Installation

**quickest way:**
```bash
npx skills add OthmanAdi/planning-with-files --skill planning-with-files -g
```

**Alternative (manual):**
```bash
git clone https://github.com/OthmanAdi/planning-with-files ~/.claude/skills/planning-with-files
```

Works with: Claude Code, Cursor, Codex, Continue, VS Code, Gemini CLI, Kilocode, Factory, Mastra, GitHub Copilot, and 30+ other agents.

## How It Works

### Step 1: Create Task Plan

Agent creates `task_plan.md`:

```markdown
# Task: [Your Task]

## Phases
- [ ] Phase 1: Research
- [ ] Phase 2: Planning
- [ ] Phase 3: Implementation
- [ ] Phase 4: Testing
- [ ] Phase 5: Deployment

## Current Phase
Phase 1: Research

## Progress
- Investigating [item]
- Found: [finding]

## Blockers
- [If any]

## Next Steps
- [Action item]
```

### Step 2: Store Findings

Research results stored in `findings.md`:

```markdown
# Findings

## Topic 1
Key insight: [Finding]
Source: [URL/Reference]

## Topic 2
Key insight: [Finding]
Source: [URL/Reference]

## Decision Log
- Decision: [What was decided]
  Rationale: [Why]
  Consequences: [Impact]
```

### Step 3: Track Progress

Session log in `progress.md`:

```markdown
# Progress Log

## Session 1: [Date]
- Started: [Time]
- Completed: [Task]
- Errors: [If any]
- Next: [What's next]

## Session 2: [Date]
- Continued: [From where]
- Completed: [Task]
- Blockers: [If any]
```

## The 5 Manus Principles

| Principle | How It Works | Benefit |
|-----------|------------|---------|
| **Filesystem as Memory** | Store in files, not context | Unlimited storage |
| **Attention Manipulation** | Re-read plan before decisions (hooks) | Stay on track |
| **Error Persistence** | Log failures in plan file | Avoid repetition |
| **Goal Tracking** | Checkboxes show progress | Never forget goals |
| **Completion Verification** | Stop hook checks all phases | Quality gates |

## Key Rules

1. **Create Plan First** — Never start without `task_plan.md`
2. **The 2-Action Rule** — Save findings after every 2 research/browser operations
3. **Log ALL Errors** — They help avoid repetition
4. **Never Repeat Failures** — Track attempts, mutate approach
5. **Update Status Always** — After every file write, note completion

## Workflow Activations

Agent automatically activates this skill at critical moments:

- **Before major decisions** → Pre-hook re-reads plan
- **After tool output** → Post-hook suggests file updates
- **On task completion** → Stop-hook verifies all phases done
- **On context reset** → Reads files to resume context

## Research Workflow

For research tasks:

1. **Create findings.md** — Start research with structure
2. **Log sources** — URL + excerpt for each finding
3. **Track progress** — Note what's been researched vs. todo
4. **Synthesize** — Combine findings into actionable insights
5. **Verify** — Confirm no findings contradict each other

## Development Workflow

For multi-step builds:

1. **task_plan.md** — Break feature into phases
2. **progress.md** — Log test results and errors
3. **findings.md** — Notes on architecture, dependencies
4. **Update plan** — After each phase, check off progress
5. **Verify** — All tests pass before final checkbox

## Benchmark Results

Formally evaluated using Anthropic's skill-creator framework:

| Metric | With Planning | Baseline |
|--------|--------------|----------|
| **Pass rate** | 96.7% (29/30) | 6.7% (2/30) |
| **3-file pattern followed** | 5/5 evals | 0/5 evals |
| **Blind A/B wins** | 3/3 (100%) | 0/3 |
| **Average rubric score** | 10.0/10 | 6.8/10 |

## Quick Commands

| Command | What It Does |
|---------|-------------|
| `/plan` | Start planning session (v2.11.0+) |
| `/plan:status` | Show planning progress at a glance |
| `/planning` | Original start command |

## When to Use

**Use for:**
- Multi-step tasks (3+ steps)
- Research projects
- Building/creating projects
- Tasks spanning 50+ tool calls
- Long-running sessions

**Skip for:**
- Simple questions
- Single-file edits
- Quick lookups

## File Structure Example

```
project/
├── task_plan.md          → Main tracking file
├── findings.md           → Research results
├── progress.md           → Session logs
└── [your files]          → Your actual project
```

## Hooks Integration

**Pre-Tool Hook**: Re-reads plan before major decisions
- Prevents goal drift
- Keeps focus clear

**Post-Tool Hook**: Suggests updating files after tool calls
- Keeps findings current
- Maintains session log

**Stop Hook**: Verifies all task phases completed
- Ensures nothing forgotten
- Quality gate before finish

## Platform Support

Works seamlessly with:
- Claude Code
- Cursor
- Codex
- Continue
- Gemini CLI
- Kilocode
- Factory AI
- GitHub Copilot
- Mastra
- OpenCode
- CodeBuddy
- Pi Agent

## Pro Tips

1. **Checkpoint often** — After each major phase, update files
2. **Cross-reference** — Link findings.md → task_plan.md decisions
3. **Session handoff** — In progress.md, note exact state for next session
4. **Error analysis** — When stuck, review progress.md for patterns

## When to Use This Skill

Use this skill when:
- Task spans multiple agent sessions
- External memory is critical
- Goal drift is a risk
- Research needs synthesis
- Complex workflows need tracking
- Long-running processes are involved
- Team coordination needed

## Real-World Example

**Research Task: "Evaluate React vs Vue for our project"**

**task_plan.md:**
```markdown
# React vs Vue Evaluation

## Phases
- [ ] Research React ecosystem
- [ ] Research Vue ecosystem
- [ ] Compare performance metrics
- [ ] Compare community size
- [ ] Recommendation with rationale
```

**findings.md:** (after research)
```markdown
# React
- Ecosystem: Massive (1M+ npm packages)
- Learning curve: Moderate
- Performance: Excellent with optimization

# Vue
- Ecosystem: Growing (50k+ packages)
- Learning curve: Gentle
- Performance: Excellent out-of-box

# Recommendation
React for large teams, Vue for rapid prototyping
```

**progress.md:**
```markdown
Session 1: Researched React ecosystem
Session 2: Researched Vue ecosystem
Session 3: Compared metrics
Session 4: Drafted recommendation
```

## Remember

This isn't just organization—it's **context engineering**. External memory lets your agent work more effectively by freeing context for reasoning.

The files become your agent's working memory on disk.
