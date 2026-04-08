---
name: deep-research
description: Conducts enterprise-grade research with multi-source synthesis, citation tracking, and verification. Produces citation-backed reports through a structured pipeline with source credibility scoring. Use for "deep research", "comprehensive analysis", "research report", "compare X vs Y", "analyze trends", or "state of the art". Not for simple lookups, debugging, or quick questions.
---

# Deep Research – Citation-Backed Analysis

## Core Purpose

Deliver citation-backed, verified research reports through a structured pipeline with source credibility scoring, evidence persistence, and progressive context management.

**Autonomy Principle**: Operate independently. Infer assumptions from context. Only stop for critical errors.

## Decision Tree

```
Request Analysis
├── Simple lookup? → STOP: Use WebSearch
├── Debugging? → STOP: Use standard tools
└── Complex analysis needed? → CONTINUE

Mode Selection
├── Initial exploration → quick (3 phases, 2-5 min)
├── Standard research → standard (6 phases, 5-10 min) [DEFAULT]
├── Critical decision → deep (8 phases, 10-20 min)
└── Comprehensive review → ultradeep (8+ phases, 20-45 min)
```

**Default assumptions**: 
- Technical query = technical audience
- Comparison = balanced perspective
- Trend = recent 1-2 years

## Workflow Phases

| Phase | Name | Quick | Standard | Deep | UltraDeep |
|-------|------|-------|----------|------|-----------|
| 1 | SCOPE | Y | Y | Y | Y |
| 2 | PLAN | - | Y | Y | Y |
| 3 | RETRIEVE | Y | Y | Y | Y |
| 4 | TRIANGULATE | - | Y | Y | Y |
| 4.5 | OUTLINE REFINEMENT | - | Y | Y | Y |
| 5 | SYNTHESIZE | - | Y | Y | Y |
| 6 | CRITIQUE | - | - | Y | Y |
| 7 | REFINE | - | - | Y | Y |
| 8 | PACKAGE | Y | Y | Y | Y |

## Execution Workflow

### Phase 1: SCOPE
Define research boundary, audience level, and success criteria.

### Phase 2: PLAN (Standard+)
Map information landscape, identify key questions, plan retrieval strategy.

### Phase 3: RETRIEVE
Gather sources with credibility assessment. Minimum 10+ sources, 3+ per claim.

### Phase 4: TRIANGULATE (Standard+)
Cross-reference claims across sources. Surface contradictions and nuances.

### Phase 4.5: OUTLINE REFINEMENT (Standard+)
Structure findings into narrative with clear sections.

### Phase 5: SYNTHESIZE (Standard+)
Weave sources into cohesive analysis with immediate citations.

### Phase 6: CRITIQUE (Deep+)
Evaluate limitations, caveats, edge cases, assumptions.

### Phase 7: REFINE (Deep+)
Polish prose, strengthen weak sections, verify all citations.

### Phase 8: PACKAGE
Generate final report in markdown, HTML, and PDF with complete bibliography.

## Output Contract

### Required Sections

- **Executive Summary** (200-400 words)
- **Introduction** (scope, methodology, assumptions)
- **Main Analysis** (4-8 findings, 600-2,000 words each, cited)
- **Synthesis & Insights** (patterns, implications)
- **Limitations & Caveats**
- **Recommendations**
- **Bibliography** (COMPLETE — every citation, no placeholders)
- **Methodology Appendix**

### Quality Standards

- ✅ 10+ sources minimum, 3+ per major claim
- ✅ All claims cited immediately [N]
- ✅ No placeholders, no fabricated citations
- ✅ Prose-first (≥80%), bullets sparingly
- ✅ Citations complete and verifiable

### Output Files

All to `~/Documents/[Topic]_Research_[YYYYMMDD]/`:
- **Markdown** (primary source)
- **HTML** (auto-opened, professional styling)
- **PDF** (print-ready)

## Citation Format

**Inline citations**: [1], [2], [3]
**Bibliography**: Numbered list with full attribution

Example:
```
[1] Smith, J. (2024). "Research Title." Journal Name, Vol. 123.
     Retrieved from: https://example.com
```

## Research Quality Checklist

- [ ] 10+ sources identified
- [ ] 3+ sources per major claim
- [ ] All sources credible and verifiable
- [ ] Citations complete and accurate
- [ ] No placeholder citations
- [ ] Contradictions acknowledged
- [ ] Limitations clearly stated
- [ ] Assumptions documented
- [ ] Recommendations evidence-based
- [ ] Prose quality professional
- [ ] No AI hallucinations
- [ ] Bibliography complete

## When to Use This Skill

**USE for:**
- Comprehensive analysis of complex topics
- Technology comparisons and state-of-the-art reviews
- Multi-perspective investigations
- Market analysis and trend assessment
- Research reports and white papers
- Comparative studies (X vs Y analysis)
- Academic-style research
- Decision-making research

**DON'T use for:**
- Simple lookups or quick answers
- Debugging or technical problems
- 1-2 search answers
- Quick time-sensitive queries
- Questions answerable with ChatGPT directly

## Default Approach

- **Standard research mode** (6 phases, 5-10 minutes)
- Quick mode for exploration, deep for critical decisions
- Technical audience by default (use context cues)
- Balanced perspective unless specified
- Recent 1-2 years focus for trends

## Key Principles

1. **Independence**: Infer assumptions, don't ask unless critical errors
2. **Verification**: All claims require sources (minimum 3 per major claim)
3. **Transparency**: Clear limitations, caveats, and methodology
4. **Completeness**: Never ship with [citation needed] placeholders
5. **Professionalism**: Report quality matches research quality
6. **Deliverables**: Always produce markdown → HTML → PDF

## Example Research Report Structure

```
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

[Numbered, complete citations]

## Appendix: Methodology

[Research approach and source selection]
```

## When to Escalate Complexity

- Shift to "deep" mode if decision is critical
- Use "ultradeep" for comprehensive knowledge domain review
- More phases = more triangulation and critique
- Trade off: time vs. comprehensiveness

## Tools & Resources Loaded

- Methodology reference: `reference/methodology.md`
- Report assembly: `reference/report-assembly.md`
- HTML generation: `reference/html-generation.md`
- Quality gates: `reference/quality-gates.md`
- Templates: `templates/report_template.md`
