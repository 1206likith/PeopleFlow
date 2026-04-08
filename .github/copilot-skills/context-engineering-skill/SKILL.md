---
name: context-engineering-collection
description: Comprehensive collection of skills for context engineering, multi-agent architectures, and production agent systems. Use when building, optimizing, or debugging agent systems that require effective context management, memory systems, tool design, or multi-agent coordination patterns.
---

# Context Engineering Collection – Agent Systems Design

## Overview

Structured guidance for building production-grade AI agent systems through effective context engineering.

**Core Principle**: Context is not just prompt text—it's the complete state available at inference time, including system instructions, tool definitions, retrieved documents, message history, and tool outputs.

## When to Activate

Activate these skills when:
- Building new agent systems from scratch
- Optimizing existing agent performance
- Debugging context-related failures
- Designing multi-agent architectures
- Creating or evaluating tools for agents
- Implementing memory and persistence layers

## Skill Map

### Foundational Context Engineering

**Understanding Context Fundamentals**
- Context quality matters more than quantity
- Lost-in-middle phenomenon (center of context gets less attention)
- U-shaped attention curves (beginning/end prioritized)
- Context poisoning (errors compound)
- Context distraction (irrelevant info overwhelms relevant)

**Recognizing Context Degradation**
Language models exhibit predictable degradation patterns as context grows. Monitor for:
- Lost-in-middle effect in middle of long contexts
- Severe attention drop-off
- Compounded errors across multiple tool calls
- Information overwhelming rather than informing

### Architectural Patterns

**Multi-Agent Coordination**
Three dominant patterns:
1. **Supervisor/Orchestrator** — Centralized control, one agent routes to specialists
2. **Peer-to-Peer Swarm** — Flexible handoffs between agents
3. **Hierarchical** — Complex decomposition with parent/child relationships

Critical insight: Sub-agents exist primarily to **isolate context**, not to simulate organizational roles.

**Memory System Design**
- **Simple Scratchpads** — Offload tool outputs, keep context clean
- **Vector RAG** — Semantic retrieval, but loses relationship information
- **Knowledge Graphs** — Structure preserved, requires engineering investment
- **File-System-as-Memory** — Just-in-time context loading, enables unlimited storage

**Filesystem-Based Context**
The filesystem provides single interface for storing/retrieving effectively unlimited context.

Key patterns:
- Scratch pads for tool output offloading
- Plan persistence for long-horizon tasks
- Sub-agent communication via shared files
- Dynamic skill loading

Agents use `ls`, `glob`, `grep`, `read_file` for targeted context discovery, often outperforming semantic search for structural queries.

**Hosted Agent Infrastructure**
Background coding agents run in remote sandboxed environments, not local machines.

Key patterns:
- Pre-built environment images refreshed regularly
- Warm sandbox pools for instant session starts
- Filesystem snapshots for session persistence
- Multiplayer support for collaborative sessions

Critical optimizations:
- Allow file reads before git sync completes (block only writes)
- Predictive sandbox warming
- Self-spawning agents for parallel execution

**Tool Design Principles**
Tools are contracts between deterministic systems and non-deterministic agents.

Principles:
- **Consolidation**: Prefer single comprehensive tools over narrow ones
- **Error Context**: Return contextual information in errors
- **Response Formats**: Support multiple formats for token efficiency
- **Namespacing**: Clear, logical namespacing

### Operational Excellence

**Context Compression**
When sessions exhaust memory, compression becomes mandatory.

Best practices:
- Optimize **tokens-per-task**, not tokens-per-request (critical distinction)
- Structured summarization with explicit sections:
  - Files processed
  - Key decisions made
  - Current state
  - Next steps
- Artifact trail integrity remains the weakest dimension across all methods

**Context Optimization**
Advanced techniques:
1. **Compaction** — Summarizing context near limits
2. **Observation Masking** — Replace verbose tool outputs with references
3. **Prefix Caching** — Reuse KV blocks across requests (Claude)
4. **Strategic Partitioning** — Split work across sub-agents with isolated contexts

**Evaluation Frameworks**
Production agent evaluation requires multi-dimensional rubrics:
- Factual accuracy
- Completeness of solution
- Tool efficiency (minimal API calls)
- Process quality (clear reasoning)

Effective patterns:
- LLM-as-judge for scalability
- Human evaluation for edge cases
- End-state evaluation for agents that mutate state

### Development Methodology

**Project Development**
Effective LLM project development begins with **task-model fit analysis**.

Pipeline stages (staged, idempotent architecture):
1. **Acquire** — Gather raw inputs
2. **Prepare** — Validate, preprocess, structure
3. **Process** — Apply agent/model
4. **Parse** — Extract structured output
5. **Render** — Deliver final result

File system state management enables debugging and caching.

**Structured Output Design**
- Explicit format specifications enable reliable parsing
- Schema validation at parse stage
- Graceful fallback for parse failures

**Best Practices**
- Start with minimal architecture
- Add complexity only when proven necessary
- Validate task-model fit before automation
- Prefer simple patterns to clever ones

## Core Concepts

The collection is organized around three core themes:

1. **Context Fundamentals** — Establish mental models of what context is, how attention mechanisms work, why context quality > quantity
2. **Architectural Patterns** — Structures and mechanisms enabling effective agent systems
3. **Operational Excellence** — Ongoing optimization and evaluation of production systems

## Practical Guidance

### Using Multiple Skills in Combination

- Start with **Fundamentals** to establish context management mental models
- Branch into **Architectural Patterns** based on system requirements
- Reference **Operational Excellence** when optimizing production systems

### Platform Agnostic

Works with:
- Claude Code
- Cursor
- Any agent framework supporting custom instructions or skills

## Key Principles

1. **Context Quality > Quantity** — Curate information for signal-to-noise ratio
2. **Information Architecture** — Explicit about what matters for the task
3. **Filesystem-as-Interface** — Leverage filesystem for structure and discovery
4. **Sub-agent Isolation** — Isolate context, not simulate organizational roles
5. **Staged Pipelines** — Idempotent stages with clear state transitions

## Quick Reference Table

| Aspect | Pattern | Benefit |
|--------|---------|---------|
| **Multiple agents** | Supervisor orchestrator | Centralized control, clear routing |
| **Memory** | Filesystem + scratchpad | Unlimited storage, targeted retrieval |
| **Tool design** | Comprehensive consolidation | Reduced cognitive load for agent |
| **Context limit** | Compaction + partitioning | Graceful degradation when full |
| **Evaluation** | Multi-dimensional rubrics | Holistic quality assessment |

## When to Use This Skill

Use this skill when:
- Designing multi-agent systems
- Optimizing agent performance at scale
- Building memory/persistence layers
- Standardizing tool interfaces
- Evaluating agent system quality
- Debugging context-related failures
- Creating hosted agent infrastructure
- Building production RAG systems

## Remember

Context engineering is not creative work—it's **systematic, measurable, and optimizable**. Start simple, measure what matters, and add complexity only when proven necessary.

The filesystem is your ally. Memory is a solved problem if you treat it as such.
