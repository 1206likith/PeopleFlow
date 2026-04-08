---
name: deep-research-enterprise
description: Enterprise-grade research skill for Claude Code with 8-phase pipeline, multi-provider search, source credibility scoring, and automated validation. Produces citation-backed reports with 10+ sources, 3+ per claim. Use for critical decisions, complex topics, comprehensive analysis, market research, and high-rigor requirements.
---

# Deep Research Enterprise – Citation-Backed Analysis

## Overview

Enterprise-grade research engine for Claude Code. Produces citation-backed reports with source credibility scoring, multi-provider search, and automated validation.

**Outperforms:** OpenAI o1, Gemini Deep Research, Claude Desktop in quality and verification.

## When to Use

Use this skill for:
- Critical business decisions
- Complex technical topics
- State-of-the-art research
- Market analysis and trends
- Competitive intelligence
- Academic research
- High-rigor requirements
- Compliance and verification

## Installation

```bash
git clone https://github.com/199-biotechnologies/claude-deep-research-skill.git \
  ~/.claude/skills/deep-research

# Optional: install search-cli for multi-provider aggregation
brew tap 199-biotechnologies/tap && brew install search-cli
search config set keys.brave YOUR_BRAVE_API_KEY
```

No additional dependencies required for basic usage (uses default WebSearch).

## Quick Start

```
deep research on quantum computing trends

deep research in ultradeep mode: compare PostgreSQL vs Supabase for our stack
```

## Research Modes

| Mode | Phases | Duration | Best For |
|------|--------|----------|----------|
| **Quick** | 3 | 2-5 min | Initial exploration |
| **Standard** | 6 | 5-10 min | Most research (DEFAULT) |
| **Deep** | 8 | 10-20 min | Complex topics, critical decisions |
| **UltraDeep** | 8+ | 20-45 min | Comprehensive reports, maximum rigor |

## 8-Phase Pipeline

```
SCOPE → PLAN → RETRIEVE → TRIANGULATE → OUTLINE → SYNTHESIZE → CRITIQUE → PACKAGE
```

### Phase 1: SCOPE
Define research boundary, audience, success criteria

### Phase 2: PLAN
Map information landscape, identify key questions

### Phase 3: RETRIEVE
Parallel search: 5-10 concurrent searches + 2-3 focused sub-agents
Returns structured evidence objects with source attribution

**Step 0 (Pre-search):** Retrieves current date before searches (prevents stale year assumptions)

**First Finish:** Adaptive quality thresholds by mode

### Phase 4: TRIANGULATE
Cross-reference claims across sources
Surface contradictions and nuances
Track evidence persistence

### Phase 5: OUTLINE REFINEMENT
Structure findings into narrative with clear sections

### Phase 6: SYNTHESIZE
Weave sources into cohesive analysis with immediate citations
Prose-first (≥80%), bullets sparingly

### Phase 7: CRITIQUE
Multi-persona red teaming:
- Skeptical Practitioner (finds holes)
- Adversarial Reviewer (challenges claims)
- Implementation Engineer (practical concerns)

**Loop-back capability:** Phase 7 can return to Phase 3 with delta-queries if critical gaps found

### Phase 8: PACKAGE
Generate final deliverables in multiple formats
Auto-continuation for reports >18K words

## Report Quality Standards

✅ **Required:**
- 10+ sources minimum, **3+ per major claim**
- Executive summary (200-400 words)
- Findings (600-2,000 words each, prose-first ≥80%)
- Full bibliography with URLs, **no placeholders**
- Automated validation: 9 checks + DOI/URL verification + hallucination detection

### Output Files

Reports saved to `~/Documents/[Topic]_Research_[Date]/`:
- **Markdown** (primary source of truth)
- **HTML** (McKinsey-style, auto-opened in browser)
- **PDF** (professional print-ready via WeasyPrint)

## Validation & Verification

### Automated Checks (9 checks)

` validate_report.py` verifies:
1. Structure completeness
2. Citation formatting
3. Word count per section
4. Markdown validity
5. URL accessibility
6. DOI resolution
7. Cross-reference consistency
8. Hallucination detection
9. Bibliography completeness

### Verification Loop

```
Validate → Fix issues → Retry (max 3 cycles)
```

If validation fails, agent automatically fixes and re-validates.

## Search Tools

Configure based on your needs:

| Tool | Always Available | Setup | Capabilities |
|------|----------------|-------|--------------|
| **WebSearch** | Yes ✅ | None | Standard web search |
| **Exa MCP** | Optional | MCP config | Semantic/neural search |
| **search-cli** | Optional | `brew install` + API keys | Multi-provider aggregation |

**search-cli providers:**
- Brave Search
- Serper
- Exa
- Jina
- Firecrawl

## Architecture

```
deep-research/
├── SKILL.md                          # Skill entry point (lean, ~100 lines)
├── reference/
│   ├── methodology.md                # 8-phase pipeline details
│   ├── report-assembly.md            # Progressive generation strategy
│   ├── quality-gates.md              # Validation standards
│   ├── html-generation.md            # McKinsey HTML conversion
│   ├── continuation.md               # Auto-continuation protocol
│   └── weasyprint_guidelines.md      # PDF generation
├── templates/
│   ├── report_template.md            # Report structure template
│   └── mckinsey_report_template.html # HTML report template
├── scripts/
│   ├── validate_report.py            # 9-check structure validator
│   ├── verify_citations.py           # DOI/URL/hallucination checker
│   ├── source_evaluator.py           # Source credibility scoring
│   ├── citation_manager.py           # Citation tracking
│   ├── md_to_html.py                 # Markdown to HTML converter
│   ├── verify_html.py                # HTML verification
│   └── research_engine.py            # Core orchestration
└── tests/
    └── fixtures/                     # Test report fixtures
```

## Key Features

### Source Credibility Scoring

Each source evaluated on:
- Publication authority
- Domain expertise
- Citation frequency
- Recency
- Methodology rigor

### Disk-Persisted Citations

`sources.json` survives context compaction—citations persist across continuation agents.

### Multi-Persona Red Teaming

Deep/UltraDeep modes include:
- **Skeptical Practitioner**: "What's wrong with this approach?"
- **Adversarial Reviewer**: "What contradicts this claim?"
- **Implementation Engineer**: "Can this actually work?"

### Critique Loop-Back

If Phase 7 (Critique) finds critical gaps:
- Returns to Phase 3 (Retrieve) with refined delta-queries
- Fills gaps with additional sources
- Re-synthesizes with new evidence

### Auto-Continuation

Reports exceeding 18K words automatically continue via recursive agent spawning:
- Context preservation across agents
- Seamless document assembly
- Maintains citation integrity

## Quality Checklist

- [ ] 10+ sources identified
- [ ] 3+ sources per major claim
- [ ] All sources credible and verifiable
- [ ] Executive summary complete (200-400 words)
- [ ] All claims cited immediately
- [ ] No placeholder citations
- [ ] Contradictions acknowledged
- [ ] Limitations clearly stated
- [ ] Assumptions documented
- [ ] Recommendations evidence-based
- [ ] Prose quality professional
- [ ] No AI hallucinations detected
- [ ] PDF renders correctly
- [ ] HTML opens in browser

## Report Structure

```markdown
# [Topic] Analysis & Research Report

## Executive Summary
[200-400 word overview of key findings]

## Introduction
[Define scope, audience, methodology, assumptions]

## Key Finding 1: [Title]
[Evidence and analysis with citations]

## Key Finding 2: [Title]
[Evidence and analysis with citations]

## Synthesis & Insights
[Patterns and implications across findings]

## Limitations & Caveats
[Honest assessment of research boundaries]

## Recommendations
[Evidence-based recommendations]

## Bibliography
[Numbered, complete citations with URLs]

## Appendix: Methodology
[Research approach and source selection]
```

## Citation Format

**Inline citations**: [1], [2], [3]

**Bibliography example:**
```
[1] Smith, J. (2024). "Research Title." Journal Name, Vol. 123.
     Retrieved from: https://example.com/article
     DOI: 10.1234/example.doi
```

## Default Approach

- **Standard research mode** (6 phases, 5-10 minutes) ← Default
- **Quick mode** for exploration
- **Deep mode** for critical decisions
- **UltraDeep mode** for comprehensive reviews
- Technical audience by default (context cues override)
- Balanced perspective unless specified
- Recent 1-2 years focus for trends

## When to Use This Skill

Use this skill when:
- Research must be citation-backed
- Quality is non-negotiable
- Sources must be verified
- Multi-perspective investigation needed
- Critical business decisions
- Market analysis
- Technology evaluation
- Academic research
- Compliance requirements
- State-of-the-art assessment

**Don't use for:**
- Simple lookups
- Quick 1-2 sentence answers
- Debugging technical problems
- Real-time operational issues

## Escalating Complexity

- **Quick → Standard** → Standard issues, slight complexity increase
- **Standard → Deep** → Critical decision or complex topic requires more rigor
- **Deep → UltraDeep** → Comprehensive knowledge domain review needed
- More phases = more triangulation and critique, trades time for comprehensiveness

## Key Principles

1. **Independence** — Infer assumptions, don't ask unless critical errors
2. **Verification** — All claims require sources (minimum 3 per major claim)
3. **Transparency** — Clear limitations, caveats, and methodology
4. **Completeness** — Never ship with [citation needed] placeholders
5. **Professionalism** — Report quality matches research quality

## Real-World Example

**Request:** "Deep research: compare PostgreSQL vs Supabase for our startup tech stack"

**Result:**
- Executive summary of trade-offs
- Deep dives: PostgreSQL (10+ sources), Supabase (8+ sources)
- Synthesis: When to use each
- Critical caveats: Scaling limits, team expertise
- Recommendation: PostgreSQL for complex queries, Supabase for rapid MVP

**Quality:** Every claim backed by 3+ sources, full bibliography, HTML+PDF reports.

## Remember

This isn't generic research—it's **verifiable, traceable, and defensible**. Every claim has sources. Every source is real.

The goal: Research you can actually cite in professional contexts.
