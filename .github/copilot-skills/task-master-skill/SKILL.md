---
name: task-master-ai
description: AI-driven task management system for software development using Claude. Use when organizing development projects, breaking down requirements into tasks, tracking progress, managing dependencies, parsing PRDs, or coordinating complex multi-step development workflows. Works with Cursor, Claude Code, and VS Code via MCP.
---

# Task Master AI – Development Task Management

## Overview

Task Master is a comprehensive task management system for AI-driven development. It parses PRDs, generates structured tasks, manages dependencies, provides research capabilities, and tracks progress across complex development projects.

## When to Use

Use Task Master when:
- Initializing new development projects
- Breaking down complex requirements into tasks
- Parsing PRDs into structured task lists
- Tracking task progress and dependencies
- Needing research for implementation decisions
- Coordinating multi-step development workflows
- Working with Cursor, Claude Code, or VS Code

## Installation

### Option 1: MCP (Recommended)

**Cursor/Windsurf/VS Code**:
```json
{
  "mcpServers": {
    "task-master-ai": {
      "command": "npx",
      "args": ["-y", "task-master-ai"],
      "env": {
        "ANTHROPIC_API_KEY": "YOUR_KEY",
        "TASK_MASTER_TOOLS": "standard"
      }
    }
  }
}
```

**Claude Code**:
```bash
claude mcp add task-master-ai -- npx -y task-master-ai
```

### Option 2: Command Line

```bash
npm install -g task-master-ai
task-master init
```

## Core Workflow

### 1. Initialize Project

```bash
task-master init
```

Prompts for project details, sets up task structure:
- `.taskmaster/` directory created
- Configuration files generated
- Templates provided

### 2. Parse PRD

Place PRD at `.taskmaster/docs/prd.txt` then:

```bash
task-master parse-prd my-prd.txt
```

Or in chat:
```
Can you parse my PRD at scripts/prd.txt?
```

PRD parsing breaks requirements into:
- Core features
- Dependencies
- Subtasks
- Success criteria

### 3. Task Lifecycle

**Available tasks states:**
- `backlog` — Awaiting implementation
- `in-progress` — Currently being worked on
- `review` — Awaiting code review
- `done` — Completed

**Move tasks between states:**
```bash
task-master move --from=5 --from-tag=backlog --to-tag=in-progress
task-master move --from=5,6,7 --from-tag=backlog --to-tag=done
```

### 4. Get Next Task

```bash
task-master next
```

Displays highest-priority task based on:
- Dependencies
- Complexity
- Sequence

### 5. View Specific Tasks

```bash
task-master show 1,3,5
```

### 6. Research Fresh Information

```bash
task-master research "Latest JWT best practices"
```

### 7. Expand Tasks

For complex tasks, request expansion:
```bash
Can you expand task 4?
Can you expand all tasks?
```

## Common Chat Commands

**Parsing & Planning:**
```
Can you parse my PRD at docs/prd.txt?
What's the next task I should work on?
```

**Implementation:**
```
Can you help me implement task 3?
Can you show me tasks 1, 3, and 5?
```

**Research:**
```
Research React Query v5 migration strategies
Research the latest best practices for JWT auth
```

**Task Management:**
```
Expand task 4 into subtasks
Move task 5 to done
What are our current blockers?
```

## Project Setup

### Required: PRD (Product Requirements Document)

Location: `.taskmaster/docs/prd.txt` or `scripts/prd.txt`

**Template:**

```
PROJECT: [Project Name]
VERSION: [Version]
DATE: [YYYY-MM-DD]

OVERVIEW
--------
[High-level description]

REQUIREMENTS
------------
[Numbered feature list]

DEPENDENCIES
------------
[External dependencies, services, tools]

SUCCESS CRITERIA
----------------
[How to measure success]

TIMELINE
--------
[Expected milestones]

NOTES
-----
[Additional context]
```

**Pro tip**: More detailed PRD = better generated tasks

### Project Structure

```
.taskmaster/
├── docs/
│   └── prd.txt
├── tasks/
│   ├── backlog.md
│   ├── in-progress.md
│   ├── review.md
│   └── done.md
├── config.json
└── templates/
    └── example_prd.txt
```

## Tool Loading Configuration

Optimize token usage with selective tool loading:

| Mode | Tools | Context | Use Case |
|------|-------|---------|----------|
| `all` | 36 | ~21,000 | Complete feature set |
| `standard` | 15 | ~10,000 | Common operations |
| `core` | 7 | ~5,000 | Essential daily workflow |

**Configure in MCP:**
```json
"env": {
  "TASK_MASTER_TOOLS": "standard"
}
```

### Standard Tools (Default recommended)

- `get_tasks` — List all tasks
- `next_task` — Get next priority task
- `get_task` — Show specific task
- `set_task_status` — Update task status
- `parse_prd` — Convert PRD to tasks
- `expand_task` — Break down a task
- `add_task` — Create new task
- `initialize_project` — Set up new project
- `generate` — Generate implementation code
- `add_subtask` — Add subtask to existing task

## Advanced Features

### Task Dependencies

Tasks can have prerequisites. Task Master respects dependencies when determining next task.

```bash
task-master move --from=5 --from-tag=backlog --to-tag=in-progress --with-dependencies
```

### Task Complexity Analysis

Get complexity report:
```bash
task-master complexity-report
```

Shows:
- Estimated effort per task
- Dependency graph
- Critical path

### Research Model

Task Master supports multiple AI models for research and implementation:

**Configure in chat:**
```
Change the main, research and fallback models to claude-opus, perplexity, and claude-sonnet respectively
```

**Available models:**
- Claude (via Anthropic)
- GPT-4 (via OpenAI)
- Gemini (via Google)
- Perplexity (for research)
- OpenRouter (bridge to many models)
- Claude Code (no API key required)

### API Key Requirements

At least ONE required (can mix providers):
- `ANTHROPIC_API_KEY` — Claude models
- `OPENAI_API_KEY` — GPT models
- `GOOGLE_API_KEY` — Gemini
- `PERPLEXITY_API_KEY` — Research model
- `OPENROUTER_API_KEY` — Multi-model bridge
- Claude Code CLI (no key needed)

## Task Structure

Tasks contain:
- **ID**: Unique identifier
- **Title**: Task name
- **Description**: What to do
- **Acceptance Criteria**: How to verify completion
- **Estimated Effort**: Time estimate
- **Dependencies**: Prerequisites
- **Status**: Current state
- **Subtasks**: Breakdown

### Task Example

```markdown
## Task 3: Implement User Authentication

**Effort**: 4 hours
**Dependencies**: Task 1 (Database setup)
**Status**: backlog

### Description
Add JWT-based authentication to the API

### Acceptance Criteria
- [ ] POST /auth/login returns JWT token
- [ ] Middleware validates tokens
- [ ] Invalid tokens return 401
- [ ] Tests cover all scenarios

### Subtasks
- [ ] Create login endpoint
- [ ] Add JWT validation middleware
- [ ] Write unit tests
- [ ] Integration test with frontend
```

## Quality Checklist

For each task before implementation:
- [ ] Clear acceptance criteria
- [ ] Dependencies identified
- [ ] Effort estimated reasonably
- [ ] No blockers
- [ ] Resources available (data, APIs, etc.)

## When to Use Task Master

Use when:
- Starting new software projects
- Complex multi-phase development
- Team coordination needed
- Requirements must be tracked
- Progress visibility important
- AI assistance desired at each step
- Working with Cursor or Claude Code

**Not ideal for:**
- Simple one-off scripts
- Small bug fixes
- Trivial tasks

## Key Principles

1. **PRD First** — Parse requirements before generating tasks
2. **Structured Tasks** — Clear acceptance criteria enable verification
3. **Dependencies Matter** — Respect task ordering
4. **Incremental Progress** — Small tasks (2-5 minute implementations) preferred
5. **Research First** — Use research before implementation

## Troubleshooting

**`task-master init` not responding:**
```bash
node node_modules/claude-task-master/scripts/init.js
```

**API key not recognized:**
- Check `.env` or MCP config has correct key names
- Verify API key is valid
- Restart editor after changing keys

**0 tools enabled:**
- Restart editor
- Verify API keys in MCP configuration
- Check `TASK_MASTER_TOOLS` setting

## Remember

Task Master is designed to work **with** your AI assistant, not instead of it. The more detailed your PRD, the better the generated tasks. Use research features liberally before implementing. Always verify completed tasks against acceptance criteria.
