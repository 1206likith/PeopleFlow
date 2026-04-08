---
name: humanizer
version: 1.0.0
description: Detect and remove AI-generated text patterns from writing. Identifies 29+ distinct AI writing patterns (inflated significance, vague attributions, superficial analysis, elegant variation, passive voice, em dash overuse) with before/after examples and voice calibration.
author: blader
license: MIT
keywords:
  - writing
  - ai-detection
  - humanization
  - content
  - editing
  - voice
compatibility:
  - Claude Code
  - Cursor
  - Codex
allowed-tools:
  - node
  - python
  - file-system
---

# Humanizer - Remove AI Writing Patterns

**Detect and remove AI-generated text patterns** from your writing. Identifies 29+ distinct patterns that make text sound "AI" and provides specific rewrites for each.

## Use When

The user wants to:
- Remove AI-generated text characteristics
- Match a specific writing voice/sample
- Make content sound more human and authentic
- Improve blog posts, landing pages, or content
- Calibrate writing to match brand voice
- Identify overused AI patterns in text
- Polish generated content for publication
- Maintain consistency with existing writing samples

## The Problem

AI writing often has recognizable patterns:
- Overuse of certain transitions ("Moreover", "Furthermore")
- Inflated significance ("groundbreaking", "revolutionary")
- Vague attributions ("many experts believe")
- Superficial -ing analysis ("analyzing the landscape")
- Repetitive structures
- Excessive passive voice
- Overdone em dashes and hyphenated pairs

**This skill identifies all 29 patterns and fixes them.**

## 29 AI Writing Patterns

### Content Patterns (6)
1. **Undue emphasis on significance** - "groundbreaking," "revolutionary," "cutting-edge"
2. **Vague attributions** - "many experts believe," "studies show"
3. **Redundant descriptors** - "uniquely unique," "truly understand"
4. **Optimistic bias** - overstate benefits, understate risks
5. **Superlative stacking** - "best," "most," "greatest" in same paragraph
6. **Filler phrases** - "It is important to note"

### Language Patterns (13)
7. **Superficial -ing analysis** - "analyzing the landscape," "exploring opportunities"
8. **Rule of three** - "simplicity, scalability, and sustainability"
9. **Elegant variation** - synonyms forced unnecessarily
10. **Passive voice overuse** - "it is believed that"
11. **Em dash overuse** - excessive — interruptions —
12. **Hyphenated word pairs** - "cutting-edge," "game-changing," "next-gen"
13. **Signposting/announcements** - "Let me explain," "Here's the thing"
14. **Hedging language** - "arguably," "perhaps," "somewhat"
15. **Sophisticated vocabulary** - forced complexity
16. **Abstract nouns** - "implementation," "optimization," "leveraging"
17. **To + infinitive constructions** - "to harness," "to unlock"
18. **Conjunction openings** - "And," "But" starting sentences
19. **Rhetorical questions** - "Did you know?"

### Style Patterns (7)
20. **Bullet point lists** - overused structuring
21. **All-caps emphasis** - "CRITICAL," "IMPORTANT"
22. **Emoji usage** - 🚀 overuse
23. **Short sentence fragments** - Choppy writing.
24. **Numbered lists** - "Here are 5 reasons"
25. **Bold emphasis** - **Too many** **bold words**
26. **Quote over-quotation** - Excessive block quotes
27. **Acronym introduction** - Unnecessary TLAs (Three Letter Acronyms)

### Communication Patterns (3)
28. **Excessive politeness** - "If you don't mind," "If I may"
29. **Indirect requests** - "Would you perhaps consider"

## How It Works

### Step 1: Voice Calibration
Provide a writing sample you want to match:

```
"I built this because the existing tools were frustrating. 
They're bloated and slow. So I spent a weekend hacking 
something that actually works. It's been useful."
```

The skill analyzes:
- Pattern frequency
- Sentence length
- Vocabulary level
- Voice characteristics
- Common transitions

### Step 2: Pattern Detection
Scans your text for all 29 patterns:

```
Input: "Groundbreaking AI tools are revolutionizing the landscape..."

Detected:
- "Groundbreaking AI tools" → Undue significance (Pattern #1)
- "revolutionizing the landscape" → Superficial -ing (Pattern #7)
- "Moreover, it is important to note" → Filler (Pattern #6)
```

### Step 3: Rewriting
Provides specific rewrites matching target voice:

```
Before: "Groundbreaking AI tools are revolutionizing the landscape 
to unlock new opportunities for forward-thinking enterprises."

After: "AI tools let us do things differently. 
They solve real problems we were struggling with."
```

## Before/After Example

### Example: Blog Post Intro

**Before (AI-generated):**
```
In today's rapidly evolving digital landscape, the importance of robust cybersecurity 
measures cannot be overstated. Groundbreaking technologies have emerged to revolutionize 
the way organizations approach data protection. This article explores the multifaceted 
dimensions of contemporary security challenges while providing actionable insights to 
fortify your digital infrastructure.
```

**Detected Patterns:**
- Undue significance ("cannot be overstated", "groundbreaking")
- Vague attribution ("today's rapidly evolving")
- Superficial -ing ("exploring", "providing")
- Abstract nouns ("dimensions", "infrastructure")
- Passive voice ("have emerged")
- Em dash overuse
- Sophisticated vocabulary ("multifaceted")

**After (Humanized):**
```
Hackers are getting better. Your company needs stronger defenses.

We'll look at real security problems you face and show you 
what actually works. No theory. Just practical steps.
```

## Installation

```bash
# Claude Code
/plugin marketplace add blader/humanizer
/plugin install humanizer@blader

# Or manual
git clone https://github.com/blader/humanizer.git
npm install
npm run build
```

## Usage

### Detection Only
```
> Analyze this text for AI patterns
> Show me what sounds "AI" in this content
```

### Voice Calibration
```
> Here's my writing sample: [paste sample]
> Now remove AI patterns to match this voice
```

### Full Rewriting
```
> Here's my AI-generated text. Here's my voice sample. 
> Rewrite to sound like me.
```

### Batch Processing
```
> Remove AI patterns from all these blog posts
> Match voice across: [file1.md, file2.md, file3.md]
```

## Configuration

Create `.humanizer.json`:

```json
{
  "targetVoice": {
    "formality": "casual",
    "vocabulary": "simple",
    "sentenceLength": "short",
    "patterns": {
      "passive_voice": false,
      "em_dashes": false,
      "hyphenated_pairs": false
    }
  },
  "patterns_to_ignore": [20, 21, 22],
  "min_changes": 0.1,
  "preserve_structure": false
}
```

## Pattern Reference

| # | Pattern | Example | Fix |
|----|---------|---------|-----|
| 1 | Undue significance | "groundbreaking" | "new" |
| 2 | Vague attribution | "many experts" | "specific person" |
| 3 | Redundant descriptors | "truly understand" | "understand" |
| 4 | Optimistic bias | "completely solve" | "help with" |
| 5 | Superlative stacking | "best, most, greatest" | vary adjectives |
| 6 | Filler | "It is important to note" | delete |
| 7 | -ing analysis | "analyzing the landscape" | direct statement |
| 8 | Rule of three | "easy, fast, secure" | 1-2 items |
| 9 | Elegant variation | "varied synonyms" | consistent |
| 10 | Passive voice | "it is believed" | "I believe" |
| 11 | Em dash overuse | "multiple — throughout" | periods |
| 12 | Hyphenated pairs | "cutting-edge" | "new" |
| 13 | Signposting | "Let me explain" | start directly |
| 14 | Hedging | "arguably" | direct claim |
| 15 | Sophistication | "multifaceted" | "complex" |
| 16 | Abstract nouns | "leveraging" | "use" |
| 17 | To + infinitive | "to harness" | "harness" |
| 18 | Conjunction starts | "And she said" | "She said" |
| 19 | Rhetorical questions | "Did you know?" | statement |
| 20 | Bullet lists | overuse | paragraphs |
| 21 | ALL CAPS | emphasis | **bold** |
| 22 | Emojis | 🚀 overuse | none |
| 23 | Fragments | Short. Punchy. | full sentences |
| 24 | Numbered lists | "5 reasons" | narrative |
| 25 | **Bold** | excess | minimal |
| 26 | Quotes | blockquote spam | inline |
| 27 | Acronyms | TLA | spell out |
| 28 | Politeness | "If you don't mind" | direct |
| 29 | Indirect | "Would you consider" | "Do this" |

## Advanced Features

### Voice Profile Matching
```
Analyze target sample → Extract voice fingerprint →
Apply to your text → Iterative refinement
```

### Parallel Detection
Process multiple files simultaneously with consistent voice

### Pattern Frequency Reports
```
Your text: 47 patterns detected
- Pattern #11 (em dash): 12x
- Pattern #12 (hyphenated): 8x
- Pattern #7 (-ing analysis): 11x
```

### Voice Calibration Strength
- **Light**: Remove obvious AI patterns only
- **Medium**: Remove 70% of patterns
- **Heavy**: Aggressive humanization

## Related Skills

- `deep-research-skill` - Research-backed content
- `marketingskills/copywriting` - Brand voice consistency
- `claudeblog-skill` - Blog writing with human touch

## Limitations

- Can't detect all patterns (some are context-dependent)
- Voice matching requires good sample (200+ words)
- Domain-specific jargon may be flagged incorrectly
- Creative writing may need manual review

## Output Formats

- **Annotated**: Show which pattern triggered each change
- **Tracked Changes**: Show before/after with diffs
- **Clean**: Just the rewritten text
- **Report**: Statistics on patterns found and fixed

## Resources

- [Pattern guide](docs/patterns.md) - Deep dive on each pattern
- [Voice calibration](docs/voice-calibration.md) - How matching works
- [Examples](docs/examples.md) - Real before/after library
- [GitHub](https://github.com/blader/humanizer)

## Support

- GitHub Issues: [Report bugs](https://github.com/blader/humanizer/issues)
- Discussions: [Share ideas](https://github.com/blader/humanizer/discussions)

Built by [@blader](https://github.com/blader) | MIT License
