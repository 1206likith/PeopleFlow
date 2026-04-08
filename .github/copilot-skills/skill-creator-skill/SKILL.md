---
name: skill-creator
description: Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, edit, or optimize an existing skill, run evals to test a skill, benchmark skill performance with variance analysis, or optimize a skill's description for better triggering accuracy.
---

# Skill Creator – Building Agent Skills

## Overview

A comprehensive workflow for creating new skills and iteratively improving existing ones through evaluation, benchmarking, and user feedback.

## Core Workflow

1. **Capture Intent** — Understand what the skill should do
2. **Interview & Research** — Gather requirements and edge cases
3. **Write SKILL.md** — Draft the skill
4. **Run Test Cases** — Evaluate with sample prompts
5. **Review Results** — Qualitative and quantitative feedback
6. **Iterate** — Improve based on feedback
7. **Optimize Description** — Fine-tune triggering accuracy

## Step 1: Capture Intent

Start by understanding the user's intent. If conversation history shows a workflow, extract:
- Tools used
- Sequence of steps
- Corrections made
- Input/output formats observed

### Key Questions

1. What should this skill enable Claude to do?
2. When should this skill trigger? (What user phrases/contexts?)
3. What's the expected output format?
4. Should we set up test cases? (Yes for objective outputs, optional for subjective)

## Step 2: Interview & Research

Proactively ask about:
- Edge cases
- Input/output formats
- Example files
- Success criteria
- Dependencies

Check available MCPs and similar skills. Come prepared with context.

## Step 3: Write SKILL.md

### YAML Frontmatter

```yaml
---
name: skill-name                # Required: 1-64 chars, lowercase, hyphens
description: 'What and when to use. Max 1024 chars. Include trigger keywords.'
argument-hint: 'Optional: shown for slash invocation'
user-invocable: true            # Optional: show as slash command (default: true)
disable-model-invocation: false # Optional: disable auto-loading (default: false)
---
```

### Description Guidelines

- **Include trigger phrases**: "Use when...", "Trigger for...", specific keywords
- **Be pushy**: Don't undertrigger. Include adjacent use cases
- **What + When**: Both what it does AND when to use it
- **Example**: "Use whenever user mentions X, Y, or Z, even if they don't explicitly ask for this skill."

### Body Content

- What the skill accomplishes
- When to use (detailed triggers)
- Step-by-step procedures
- Quick reference sections
- Common tasks
- Best practices
- Resources

### Structure Tips

- Keep SKILL.md under 500 lines (progressive disclosure)
- Reference bundled files clearly
- Organize by domain if supporting multiple variants
- Include table of contents for large reference files

## Step 4: Create Test Cases

### Test Prompt Format

Create 2-3 realistic test prompts. Save to `evals/evals.json`:

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "User's actual task prompt",
      "expected_output": "Description of expected result",
      "files": []
    }
  ]
}
```

### Good Test Cases

- Substantive enough that Claude benefits from consulting the skill
- Real-world examples users would actually type
- 2-3 test cases minimum
- Include edge cases and common variations

## Step 5: Run Test Cases

### Parallel Execution

Spawn WITH-SKILL and BASELINE runs simultaneously:

**With-skill run:**
```
Execute this task:
- Skill path: <path-to-skill>
- Task: <eval prompt>
- Save outputs to: <workspace>/iteration-<N>/eval-<ID>/with_skill/outputs/
```

**Baseline run** (same prompt, no skill or old version):
```
Same task, no skill path
- Save to: <workspace>/iteration-<N>/eval-<ID>/without_skill/outputs/
```

### While Runs Process

Draft assertions for each test case. Good assertions:
- Objectively verifiable
- Descriptive names
- Read clearly in benchmark viewer
- For subjective outputs (writing, design): qualitative only

## Step 6: Review Results

Use `generate_review.py` to launch visual reviewer:

```bash
python <skill-path>/eval-viewer/generate_review.py \
  <workspace>/iteration-N \
  --skill-name "my-skill" \
  --benchmark <workspace>/iteration-N/benchmark.json
```

This shows:
- **Outputs tab**: View each test case result, leave feedback
- **Benchmark tab**: Quantitative stats (pass rates, timing, tokens)

## Step 7: Iterate

Based on user feedback, improve the skill:

1. **Generalize from feedback** — Think about broad patterns, not just these examples
2. **Keep prompt lean** — Remove things not pulling weight
3. **Explain the why** — Help the model understand importance, not just rules
4. **Look for repeated work** — If subagents all write similar scripts, bundle it

### The Iteration Loop

1. Apply improvements to skill
2. Rerun all test cases into new `iteration-<N+1>/` directory
3. Launch reviewer with `--previous-workspace` pointing to previous iteration
4. Wait for user feedback
5. Read `feedback.json`, improve again, repeat

**Continue until:**
- User is happy
- Feedback is all empty (everything looks good)
- Not making meaningful progress

## Step 8: Optimize Description

### Generate Trigger Eval Queries

Create 20 realistic eval queries (mix should-trigger and should-not-trigger):

```json
[
  {"query": "detailed user request...", "should_trigger": true},
  {"query": "adjacent but different request...", "should_trigger": false}
]
```

### Run Optimization Loop

```bash
python -m scripts.run_loop \
  --eval-set <path-to-trigger-eval.json> \
  --skill-path <path-to-skill> \
  --model <model-id> \
  --max-iterations 5
```

This optimizes description for accurate triggering based on evaluation.

## Skill Structure

```
skill-name/
├── SKILL.md              # Required
├── scripts/              # Executable code (optional)
├── references/           # Documentation files (optional)
├── assets/               # Templates, boilerplate (optional)
└── evals/               # Test cases and results
    ├── evals.json       # Test prompts
    └── iteration-1/     # Results
```

## Skill Writing Principles

### Progressive Disclosure

1. **Metadata** (~100 words): Discovery layer
2. **SKILL.md body** (<500 lines): Context when triggered
3. **Bundled resources**: Unlimited, loaded on demand

### Output Formats

Define clearly:
```markdown
## Report structure
ALWAYS use this exact template:
# [Title]
## Executive summary
## Key findings
```

### Examples

Use consistent format:
```markdown
## Commit message format
**Example 1:**
Input: Added user authentication with JWT tokens
Output: feat(auth): implement JWT-based authentication
```

## Principle of Lack of Surprise

Skills must:
- ✅ Contain no malware or exploit code
- ✅ Not compromise system security
- ✅ Match described intent
- ✅ Be benign and helpful

## When to Use This Skill

Use this skill when:
- User wants to create a new skill from scratch
- Edit or optimize an existing skill
- Run evaluations to test a skill
- Benchmark skill performance
- Optimize skill description for triggering
- Measure and improve overall skill quality

## Key Takeaway

The goal is creating generalizable skills that work across contexts, not over-fitting to a few examples. Keep skills lean, explain the why, and iterate based on real-world feedback.
