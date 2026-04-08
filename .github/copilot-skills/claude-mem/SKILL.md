---
name: claude-mem
version: 6.5.0
description: Persistent memory compression system for Claude Code that automatically captures tool usage, generates semantic summaries, and makes previous session context available to current sessions using progressive disclosure.
author: Alex Newman (@thedotmack)
license: AGPL-3.0
keywords:
  - memory
  - context
  - persistence
  - session
  - knowledge-base
compatibility:
  - Claude Code
  - Gemini CLI
  - Cursor (partial)
allowed-tools:
  - node
  - bun
  - sqlite
  - file-system
---

# Claude-Mem: Persistent Memory for Claude Code

**Persistent memory compression system** that:
- **Captures** tool usage observations automatically across sessions
- **Compresses** into semantic summaries (token-efficient)
- **Surfaces** previous context via 4 MCP search tools
- **Progressive disclosure** layer pattern reduces token waste

## Use When

The user wants to:
- Maintain project knowledge across sessions
- Search past work and decisions
- Build on previous implementations without re-explaining context
- Prevent repeating mistakes from earlier sessions
- Access rich context with minimal token cost
- Search project history with natural language

## Core Concept: Progressive Disclosure

Claude-Mem uses a **3-layer token-efficient workflow** to prevent context bloat:

```
Layer 1: search()           → Compact index (~50-100 tokens)
                              ↓ (user reviews, picks IDs)
Layer 2: timeline()         → Chronological context (~100-300 tokens)
                              ↓ (user identifies relevant entries)
Layer 3: get_observations() → Full details (~500-1,000 tokens only for selected IDs)
```

This reduces token usage by **~10x** compared to bulk loading all memories.

## Architecture Overview

**5 Lifecycle Hooks** capture observations automatically:
1. **SessionStart** - Initialize session context
2. **UserPromptSubmit** - Pre-process user requests
3. **PostToolUse** - Capture tool results (files, tests, endpoints)
4. **Stop** - Capture final decisions
5. **SessionEnd** - Archive and summarize

**Backend Components:**
- **SQLite Database** - Persistent storage with FTS5 search
- **Chroma Vector DB** - Semantic embedding + keyword hybrid search
- **Worker Service** - HTTP API on port 37777 + web viewer UI
- **mem-search Skill** - Natural language query interface

## MCP Search Tools

### 1. `search` - Find relevant entries
```
search(query="authentication bug", type="bugfix", limit=10)
→ Returns: [ID: 123, ID: 456, ID: 789] with compacted text snippets
```

### 2. `timeline` - See chronological context around a result
```
timeline(observation_id=456, window=5)
→ Returns: 5 entries before/after ID 456 chronologically
```

### 3. `get_observations` - Fetch full details (use last)
```
get_observations(ids=[456, 789])
→ Returns: Complete observation data for selected IDs only
```

## Installation

```bash
# Claude Code (recommended)
/plugin marketplace add thedotmack/claude-mem
/plugin install claude-mem

# Or via npmx
npx claude-mem install

# Or Gemini CLI
npx claude-mem install --ide gemini-cli
```

## Setup

1. **Install** via command above
2. **Restart** Claude Code or Gemini CLI
3. **Context** from previous sessions automatically appears in new sessions

Settings configurable in `~/.claude-mem/settings.json`:
- Worker port (default: 37777)
- Data directory
- AI model selection
- Context injection settings

## Core Features

### 🧠 Automatic Operation
- Hooks trigger silently—no manual intervention
- Captures relevant tool outputs automatically
- Generates summaries nightly (optional)

### 📊 Progressive Disclosure  
- Search fast (50-100 tokens)
- Timeline for context (100-300 tokens)
- Full details only when needed (500-1000 tokens)

### 🔍 Search Tools
- **Full-text search** across all observations
- **Semantic search** using vector embeddings (Chroma)
- **Filter by type** (code, test, decision, etc.)
- **Filter by date** range

### 🖥️ Web Viewer UI
- Real-time memory stream at `http://localhost:37777`
- Browse session history
- Search interface
- Export observations

### 🔗 Citations & References
- Every observation gets unique ID
- Reference past work: `mem:123` in prompts
- Access via API: `http://localhost:37777/api/observation/{id}`

### 🧪 Beta Features
- **Endless Mode** - Biomimetic memory for extended sessions
- Version switching in web UI settings

## Usage Workflow

### Scenario 1: Fixing Recurring Bug
```
> claude "there's a race condition in the auth service"

Claude-Mem searches memory for "race condition" + "auth"
→ Surfaces past investigation: mem:456
→ Claude reviews previous analysis and solutions
→ Applies proven fix with context from mem:456
```

### Scenario 2: Reviewing Architecture Decision
```
> claude "should we use Redis or Memcached?"

Claude-Mem searches for "caching strategy" discussions
→ Returns 3 past evaluations with reasoning
→ Claude reviews trade-offs analyzed before
→ Maintains consistency with previous decision
```

### Scenario 3: Continuing After Session Break
```
Session 1: Implement auth module (mem:900-950)
Session 2: "continue where we left off"
→ Claude-Mem loads full context from previous session
→ Claude has complete understanding without re-explaining
```

## Data Storage

**SQLite Database** (`~/.claude-mem/db.sqlite`):
- `sessions` - Session metadata
- `observations` - Full observation records
- `summaries` - Compressed session summaries
- `fts_observations` - Full-text search index

**Chroma Vector DB** - Semantic embeddings for hybrid search

## Configuration

File: `~/.claude-mem/settings.json`

```json
{
  "worker_port": 37777,
  "data_dir": "~/.claude-mem",
  "model": "claude-3-5-sonnet",
  "progressive_disclosure": true,
  "daily_summaries": true,
  "search_limit": 10,
  "context_window": 3000
}
```

## Security & Privacy

- ✅ Runs locally—data stays on your machine
- ✅ Optional cloud compute via Modal for heavy workloads
- ✅ No data sent to external APIs unless explicitly configured
- ✅ All hooks run with user permissions
- ✅ Review security considerations in Claude Code docs

## Related Skills

- `context-engineering-skill` - Agentic context patterns
- `planning-with-files-skill` - Persistent markdown planning

## Troubleshooting

**Memory not persisting?**
→ Check that `~/.claude-mem/` directory exists
→ Verify hooks are running (check logs)

**Search returning no results?**
→ Try broader query terms
→ Check data directory has observations

**Performance slow?**
→ Reduce context_window in settings.json
→ Use search → timeline → get_observations workflow

## Resources

- [Installation guide](https://docs.claude-mem.ai/installation)
- [Usage guide](https://docs.claude-mem.ai/usage/getting-started)
- [Architecture docs](https://docs.claude-mem.ai/architecture/overview)
- [API reference](https://docs.claude-mem.ai/architecture/database)
- [Troubleshooting](https://docs.claude-mem.ai/troubleshooting)

## Official Links

- **GitHub**: https://github.com/thedotmack/claude-mem
- **Docs**: https://docs.claude-mem.ai/
- **Twitter**: [@Claude_Memory](https://x.com/Claude_Memory)
- **Discord**: [Join Community](https://discord.com/invite/J4wttp9vDu)
