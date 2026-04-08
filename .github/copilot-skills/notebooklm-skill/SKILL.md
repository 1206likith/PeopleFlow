---
name: notebooklm-skill
description: Claude Code skill enabling direct communication with Google NotebookLM notebooks for source-grounded research. Use when you need to query personal documentation or knowledge bases, reduce hallucinations with source-only answers, and get citation-backed research directly from your uploaded documents without copy-pasting between browser and editor.
---

# NotebookLM Claude Code Skill – Document-Grounded Research

## Overview

Query your Google NotebookLM notebooks directly from Claude Code for source-grounded, citation-backed answers from Gemini—without copy-pasting between browser and editor.

**Critical**: This skill works **ONLY with local Claude Code**, NOT the web UI (sandbox restrictions).

## The Problem

When Claude Code tries to search documentation manually:
- ❌ Massive token consumption (reading multiple files repeatedly)
- ❌ Inaccurate retrieval (keyword search, misses context)
- ❌ Hallucinations (invents APIs when it can't find things)
- ❌ Manual copy-paste (switching between NotebookLM browser and editor constantly)

## The Solution

```
Your Task → Claude asks NotebookLM → Gemini synthesizes answer → Claude writes correct code

No more copy-paste dance.
```

Your Claude Code agent asks NotebookLM questions directly and gets answers straight back in the CLI—without ever leaving the editor.

## Why NotebookLM, Not Local RAG?

| Method | Token Cost | Setup Time | Hallucinations | Retrieval Quality |
|--------|-----------|-----------|---------------|--------------------|
| **Feed docs to Claude** | 🔴 Very high | Instant | Yes (fills gaps) | Variable |
| **Web search** | 🟡 Medium | Instant | High (unreliable) | Hit or miss |
| **Local RAG** | 🟡 Medium-High | Hours | Medium (gaps) | Depends on setup |
| **NotebookLM Skill** | 🟢 Minimal | 5 min | Minimal (grounded) | Expert synthesis |

**NotebookLM advantages:**
- ✅ Pre-processed by Gemini: Upload docs once, instant expert knowledge
- ✅ Natural language Q&A: Actual understanding and synthesis, not just retrieval
- ✅ Multi-source correlation: Connects information across 50+ documents
- ✅ Citation-backed: Every answer includes source references
- ✅ No infrastructure: No vector DBs, embeddings, or chunking strategies needed

## Installation

**Simplest way:**

```bash
# 1. Create skills directory (if it doesn't exist)
mkdir -p ~/.claude/skills

# 2. Clone this repository
cd ~/.claude/skills
git clone https://github.com/PleasePrompto/notebooklm-skill notebooklm

# 3. That's it! Open Claude Code and say:
"What skills do I have?"
```

**First use automatic setup:**
- Creates an isolated Python environment (`.venv`)
- Installs all dependencies including Google Chrome
- Sets up browser automation
- Everything self-contained in skill folder

## Quick Start

### 1. Verify Skill Is Loaded

In Claude Code:
```
"What skills do I have?"
```

Claude will list your available skills including NotebookLM.

### 2. Authenticate with Google (One-Time)

```
"Set up NotebookLM authentication"
```

A Chrome window opens → Log in with your Google account → Authentication persists across sessions.

### 3. Create Your Knowledge Base

Go to [notebooklm.google.com](https://notebooklm.google.com/):
- Create a new notebook
- Upload your documents:
  - 📄 PDFs, Google Docs, markdown files
  - 🔗 Websites and GitHub repos
  - 🎥 YouTube videos
  - 📚 Multiple sources per notebook
- Settings → Share → Anyone with link → Copy link

### 4. Add to Your Library

**Option A: Smart Add (Recommended)**
```
"Query this notebook about its content and add it to my library: [your-link]"
```

Claude automatically discovers what's in the notebook and adds it with metadata.

**Option B: Manual Add**
```
"Add this NotebookLM to my library: [your-link]"
```

Claude will ask for name and topics, then save it.

### 5. Start Researching

```
"What does my React docs say about hooks?"
```

Claude automatically:
- Selects the right notebook from your library
- Asks comprehensive questions
- Gets answers directly from NotebookLM
- Uses that knowledge to help with your task

## Common Commands

| Command | What It Does |
|---------|------------|
| `"Set up NotebookLM authentication"` | Opens Chrome for Google login |
| `"Add [link] to my NotebookLM library"` | Saves notebook with metadata |
| `"Show my NotebookLM notebooks"` | Lists all saved notebooks |
| `"Ask my API docs about [topic]"` | Queries the relevant notebook |
| `"Use the React notebook"` | Sets active notebook |
| `"Clear NotebookLM data"` | Fresh start (keeps library) |

## Real-World Examples

### Example 1: Workshop Manual Query

**You ask:** "Check my Suzuki GSR 600 workshop manual for brake fluid type, engine oil specs, and rear axle torque."

**Claude:**
- Authenticates with NotebookLM
- Asks comprehensive questions about each specification
- Follows up when prompted "Is that ALL you need to know?"
- Returns accurate specs: DOT 4 brake fluid, SAE 10W-40 oil, 100 N·m rear axle torque

### Example 2: Building Without Hallucinations

**You ask:** "I need to build an n8n workflow for Gmail spam filtering. Use my n8n notebook."

**Claude's internal process:**
- Loads NotebookLM skill
- Activates n8n notebook
- Asks comprehensive questions with follow-ups
- Synthesizes complete answer from multiple queries

**Result:** Working workflow on first try, no debugging hallucinated APIs.

## How It Works

### Architecture

```
~/.claude/skills/notebooklm/
├── SKILL.md                 # Skill entry point
├── scripts/                 # Python automation scripts
│   ├── ask_question.py      # Query NotebookLM
│   ├── notebook_manager.py  # Library management
│   └── auth_manager.py      # Google authentication
├── .venv/                   # Isolated Python environment (auto-created)
└── data/                    # Local notebook library
    ├── library.json         # Saved notebooks with metadata
    ├── auth_info.json       # Authentication status
    └── browser_state/       # Browser cookies and session
```

### Session Model

**Stateless approach:**
- Each question opens a fresh browser
- Asks the question, gets the answer
- Closes browser immediately
- Your notebook library persists

**Benefits:**
- No persistent chat context needed
- Each question is independent
- Automatic follow-up mechanism

Each answer includes "Is that ALL you need to know?" to prompt comprehensive follow-ups.

## Core Features

### Source-Grounded Responses

NotebookLM significantly reduces hallucinations by answering **exclusively from your uploaded documents**. If information isn't available, it indicates uncertainty rather than inventing content.

### Direct Integration

No copy-paste between browser and editor. Claude asks and receives answers programmatically within the editor.

### Smart Library Management

Save NotebookLM links with tags and descriptions. Claude auto-selects the right notebook for your task.

### Automatic Authentication

One-time Google login, then authentication persists across sessions.

### Self-Contained

Everything runs in the skill folder with an isolated Python environment. No global installations needed.

### Human-Like Automation

Uses realistic typing speeds and interaction patterns to avoid detection.

## Data Storage

All data stored locally within skill directory:

```
~/.claude/skills/notebooklm/data/
├── library.json           # Notebook library with metadata
├── auth_info.json         # Authentication status info
└── browser_state/         # Browser cookies and session data
```

**Security Note:**
- `data/` directory contains sensitive authentication data
- Automatically excluded from git via `.gitignore`
- NEVER manually commit or share `data/` contents

## Limitations

### Skill-Specific
- Local Claude Code only (web UI runs in sandbox without network)
- No session persistence (each question independent)
- No follow-up context (can't reference "the previous answer")

### NotebookLM
- Rate limits on free tier
- Manual upload required (documents must be in NotebookLM first)
- Notebooks must be shared publicly

## Troubleshooting

### Skill Not Found
```bash
# Make sure it's in the right location
ls ~/.claude/skills/notebooklm/
# Should show: SKILL.md, scripts/, etc.
```

### Authentication Issues
Say: `"Reset NotebookLM authentication"`

### Browser Crashes
Say: `"Clear NotebookLM browser data"`

### Dependencies Issues
```bash
# Manual reinstall if needed
cd ~/.claude/skills/notebooklm
rm -rf .venv
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## Tech Stack

- **Patchright**: Browser automation (Playwright-based)
- **Python**: Implementation language
- **Stealth techniques**: Human-like typing and interaction patterns

## When to Use This Skill

Use this skill when:
- You need to query personal documentation
- Reducing hallucinations with source-only answers
- Research must cite sources
- Documentation is extensive (50+ documents)
- Building features based on your knowledge base
- Multi-source research and synthesis
- API documentation queries

**vs. standard web search:**
- NotebookLM: Document-based, grounded, your knowledge
- Web search: Internet-based, external sources, potentially outdated

## Key Commands Summary

```
Set up NotebookLM          → Authenticate once
Add notebook link          → Save to library
Query with specific docs   → Get grounded answers
Show all notebooks         → See what you have saved
Clear and reset           → Fresh start if needed
```

## Remember

Without this skill: NotebookLM in browser → Copy answer → Paste in Claude → Copy next question → Back to browser...

**With this skill:** Claude researches directly → Gets answers instantly → Writes correct code

Stop the copy-paste dance. Start getting accurate, grounded answers directly in Claude Code.
