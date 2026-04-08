---
name: context-engineering-kit
version: 2.2.3
description: Hand-crafted collection of advanced context engineering techniques and patterns (15+ plugins) with minimal token footprint. Includes Reflexion, Spec-Driven Development, Subagent-Driven Development, Code Review, Git, TDD, and more to improve agent result quality and predictability.
author: NeoLabHQ
license: GPL-3.0
keywords:
  - context-engineering
  - agent-reliability
  - specification-driven-development
  - subagent-orchestration
  - reflexion
  - lpm-as-judge
compatibility:
  - Claude Code
  - OpenCode
  - Cursor
  - Antigravity
  - Gemini CLI
allowed-tools:
  - node
  - python
  - shell
  - git
  - file-system
---

# Context Engineering Kit (CEK)

**15+ advanced context engineering plugins** focused on improving agent result quality, predictability, and reliability. Token-efficient patterns based on proven research and real production usage for 6+ months.

## Core Mission

Transform agent development from "vibe coding" to **reliable, auditable, specification-driven workflows** with **minimal token overhead** using context engineering patterns backed by peer-reviewed research.

## Use When

The user wants to:
- Ensure consistent, high-quality agent outputs
- Prevent hallucinations and missed requirements
- Build production-grade agent workflows
- Orchestrate complex multi-agent tasks
- Enforce code quality and architecture
- Reduce development cycles with reliable generation
- Track and improve agent decision-making
- Scale from simple to complex features

## Core Plugins (15+ Available)

### 🔄 **Reflexion** - Feedback & Refinement
- **/reflexion:reflect** - Self-critique and improvement
- **/reflexion:memorize** - Extract insights into CLAUDE.md
- **/reflexion:critique** - Multi-perspective debate

**Impact**: +8-21% output quality improvement

### 📋 **Spec-Driven Development (SDD)** - Production-Ready Code
- **/sdd:add-task** - Create task specification
- **/sdd:plan** - Detailed architecture planning
- **/sdd:implement** - Reliable implementation
- **/sdd:brainstorm** - Refine vague ideas

**Impact**: 94-99% accuracy on real production projects

### 👥 **Subagent-Driven Development (SADD)** - Multi-Agent Orchestration
- **/sadd:do-and-judge** - Single task with verification
- **/sadd:do-in-steps** - Complex tasks through sequential orchestration
- **/sadd:do-in-parallel** - Parallel execution with isolation
- **/sadd:do-competitively** - Competitive generation + multi-judge evaluation
- **/sadd:tree-of-thoughts** - Structured reasoning
- **/sadd:judge-with-debate** - Multi-agent debate verification
- **/sadd:launch-sub-agent** - Focused sub-agents with auto model selection

**Impact**: 90-92% accuracy, handles 20+ file changes

### 🔍 **Code Review** - Quality Gates
- **/code-review:review-local-changes** - Uncommitted code review
- **/code-review:review-pr** - Pull request analysis
  - Specialized agents: bug-hunter, code-quality-reviewer, contracts-reviewer
  - security-auditor, historical-context-reviewer, test-coverage-reviewer

### 🔗 **Git** - Workflow Automation
- **/git:commit** - Conventional commits with emoji
- **/git:create-pr** - Pull request creation
- **/git:analyze-issue** - GitHub issue → specification
- **/git:load-issues** - Load all open issues as markdown
- **/git:create-worktree** - Parallel branch development
- **/git:compare-worktrees** - Compare git worktrees
- **/git:merge-worktree** - Selective merging

### ✅ **Test-Driven Development (TDD)** - Code Quality Enforcement
- **/tdd:write-tests** - Systematic test coverage
- **/tdd:fix-tests** - Debug and fix failing tests

### 🏗️ **Domain-Driven Development (DDD)** - Architecture Quality
- **/ddd:setup-code-formatting** - Code style + quality rules
  - Clean Architecture, SOLID, Functional Programming patterns

### 🧠 **First Principles Framework (FPF)** - Auditable Decision-Making
- **/fpf:propose-hypotheses** - Generate competing alternatives
- **/fpf:status** - Show reasoning progress
- **/fpf:query** - Search knowledge base
- **/fpf:decay** - Manage evidence freshness
- **/fpf:actualize** - Reconcile knowledge with code

**Research-backed:** ADI cycle (Abduction-Deduction-Induction) with evidence tracking

### 🔄 **Kaizen** - Continuous Improvement
- **/kaizen:analyse** - Auto-select best analysis method
- **/kaizen:analyse-problem** - A3 one-page problem analysis
- **/kaizen:why** - Iterative Five Whys
- **/kaizen:root-cause-tracing** - Bug tracking through call stack
- **/kaizen:cause-and-effect** - Fishbone analysis
- **/kaizen:plan-do-check-act** - PDCA cycles

### ⚙️ **Customaize Agent** - Extension Development
- **/customaize-agent:create-agent** - Agent creation guide
- **/customaize-agent:create-command** - Custom commands
- **/customaize-agent:create-skill** - Effective skill development
- **/customaize-agent:create-hook** - Git hooks
- **/customaize-agent:test-skill** - Skill validation (RED-GREEN-REFACTOR)
- **/customaize-agent:test-prompt** - Prompt testing framework
- **/customaize-agent:apply-anthropic-skill-best-practices** - Official guidelines

### 📚 **Docs** - Documentation Management
- **/docs:update-docs** - Keep docs in sync with code
- **/docs:write-concisely** - Apply *Elements of Style* principles

### 🛠️ **Tech Stack** - Language/Framework Best Practices
- **/tech-stack:add-typescript-best-practices** - Setup CLAUDE.md rules
- Support for Python, JavaScript, Go, Rust, Java, etc.

### 🔌 **MCP** - External Tool Integration
- **/mcp:setup-context7-mcp** - Technology documentation
- **/mcp:setup-serena-mcp** - Semantic code retrieval
- **/mcp:setup-codemap-cli** - Codebase visualization
- **/mcp:setup-arxiv-mcp** - Academic paper search
- **/mcp:build-mcp** - Create MCP servers

## Agent Reliability Engineering: Quality vs Token Cost

**Comparison table of approaches** by accuracy on production projects (6+ months real usage):

| Approach | 1-3 files | 4-10 files | 10-20 files | 20+ files | Token Overhead |
|----------|----------|----------|-----------|-----------|----------------|
| One-shot prompt | 60-80% | 30-50% | 5-30% | 1-20% | 0 |
| `/reflect` | 68-91% | 49-71% | 13-41% | 1-30% | 1-3k |
| `/reflect + /memorize` | 79-87% | 60-79% | 34-42% | 5-30% | 2-5k |
| `/do-and-judge` | 90% | 83% | 60% | 30% | 1.5-3x |
| `/do-in-steps` | 92% | 90% | 71% | 50% | 3-5x |
| `/plan + /implement` | 94% | 93% | 85% | 70% | 5-20x |
| `/brainstorm + /plan + /implement` | 95% | 95% | 90% | 80% | 5-20x |
| `/plan + human review + /implement` | 99% | 99% | 99% | 95% | 5-35x |

**Choose based on:**
- Small changes? → Use `/reflect` (1-3k tokens)
- Medium tasks? → Use `/do-and-judge` (1.5-3x)
- Large/complex? → Use `/plan + /implement` (5-20x)
- Production-critical? → Add human review (5-35x)

## Installation

```bash
# Claude Code
/plugin marketplace add NeoLabHQ/context-engineering-kit
/plugin install reflexion@NeoLabHQ/context-engineering-kit
(install other plugins as needed)

# Cursor, Codex, OpenCode, etc.
npx skills add NeoLabHQ/context-engineering-kit
# Select which plugins to install
```

## Quick Start Workflow

```bash
# 1. Simple task with reflection
> claude "implement user authentication, then reflect"

# 2. Complex task with SDD
> /sdd:add-task "Design and implement payment processing"
> /sdd:plan
> /sdd:implement  # Working code in 30min-few days

# 3. Multi-file with subagent orchestration
> /sadd:do-in-steps "Refactor authentication module files into 3 parts"

# 4. Large project with human review
> /sdd:plan --human-in-the-loop "Complex analytics pipeline"
```

## Research Foundation

**15+ peer-reviewed papers** backing the patterns:

- [Self-Refine](https://arxiv.org/abs/2303.17651) - Core refinement loop
- [Reflexion](https://arxiv.org/abs/2303.11366) - Memory integration
- [LLM-as-Judge](https://arxiv.org/abs/2306.05685) - Evaluation patterns
- [Tree of Thoughts](https://arxiv.org/abs/2305.10601) - Structured exploration
- [Agentic Context Engineering](https://arxiv.org/abs/2510.04618) - Memory curation (+10.6% baseline)
- [Solving Million-Step Tasks with Zero Errors](https://arxiv.org/abs/2511.09030) - MAKER pattern
- [Chain-of-Verification](https://arxiv.org/abs/2309.11495) - Hallucination reduction
- [Verbalized Sampling](https://arxiv.org/abs/2510.01171) - 2-3x improvement on diverse ideas

## Key Concepts

### 🧠 **Context Rot Prevention**
Context isolation of independent agents keeps LLMs at peak performance even in long sessions

### 📊 **Progressive Disclosure**
Load context in layers—start compact, expand only when needed

### 🔍 **LLM-as-Judge**
Use evidence-based rubrics and scoring instead of estimates

### 🏗️ **Multi-Agent Orchestration**
Divide complex tasks into focused sub-agent sprints with context isolation

### 📝 **Specification-Driven Development**
Based on arc42 standard—eliminate specs that don't improve code quality

### 🎯 **MAKER Pattern**
Multi-agent voting + clean-state launches + filesystem memory = zero-error tasks

## Configuration

Primary file: `./CLAUDE.md` (and optional `.CLAUDE.local.md` for personal settings)

Tracks:
- Installed plugins
- Code quality rules
- Tech stack best practices
- MCP integrations
- Custom refactoring patterns

## Related Skills

- `planning-with-files-skill` - Manus-style persistent planning
- `task-master-skill` - Task management and PRD parsing
- `deep-research-skill` - Citation-backed research

## Community

- **GitHub**: https://github.com/NeoLabHQ/context-engineering-kit
- **Docs**: https://cek.neolab.finance/
- **Issues**: [Report bugs](https://github.com/NeoLabHQ/context-engineering-kit/issues)
- **Discussions**: [Share ideas](https://github.com/NeoLabHQ/context-engineering-kit/discussions)

## Support

- Full docs at [cek.neolab.finance](https://cek.neolab.finance/)
- Recommended starting plugins: **SDD** and **SADD**
- Enterprise support via [K-Dense](https://www.neolab.finance/)

**Built by NeoLabHQ** | GPL-3.0 License | 768 GitHub stars
