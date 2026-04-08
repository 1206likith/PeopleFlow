---
name: pptx
description: Use this skill any time a .pptx file is involved in any way — as input, output, or both. This includes creating slide decks, pitch decks, or presentations; reading, parsing, or extracting text from any .pptx file; editing, modifying, or updating existing presentations; combining or splitting slide files; working with templates, layouts, speaker notes, or comments. Trigger whenever the user mentions "deck," "slides," "presentation," or references a .pptx filename, regardless of what they plan to do with the content afterward.
---

# PPTX Skill – Creating and Editing Presentations

## Overview

Create, read, edit, and manage PowerPoint presentations (.pptx files). Use for slide decks, pitch presentations, and visual storytelling.

## Quick Reference

| Task | Guide |
|------|-------|
| Read/analyze content | `python -m markitdown presentation.pptx` |
| Extract text | `python -m markitdown presentation.pptx > output.txt` |
| Edit slides | Unpack → modify → pack |
| Create from scratch | Use pptxgenjs library |
| Visual QA | Convert to images and inspect |

## Reading Content

### Extract Text

```bash
python -m markitdown presentation.pptx
```

### Convert to Images for Review

```bash
python scripts/office/soffice.py --headless --convert-to pdf output.pptx
pdftoppm -jpeg -r 150 output.pdf slide
```

This creates `slide-01.jpg`, `slide-02.jpg`, etc.

## Creating from Scratch

Use **pptxgenjs** library:

```bash
npm install -g pptxgenjs
```

### Basic Slide Creation (JavaScript)

```javascript
const Presentation = require("pptxgenjs");
const pres = new Presentation();

const slide = pres.addSlide();
slide.background = { color: "FFFFFF" };
slide.addText("Hello World", { x: 0.5, y: 0.5, fontSize: 44, bold: true });

pres.writeFile({ fileName: "output.pptx" });
```

## Design Philosophy: Create Bold, Content-Informed Slides

### Color Palettes (Pick One)

Choose a color palette designed for YOUR topic, not generic corporate blue:

- **Midnight Executive**: Navy (#1E2761) + Ice Blue (#CADCFC) + White
- **Forest & Moss**: Forest Green (#2C5F2D) + Moss (#97BC62) + Cream
- **Coral Energy**: Coral (#F96167) + Gold (#F9E795) + Navy (#2F3C7E)
- **Ocean Gradient**: Deep Blue (#065A82) + Teal (#1C7293) + Midnight
- **Sage Calm**: Sage (#84B59F) + Eucalyptus (#69A297) + Slate

### Dominance Principle

- **60-70%**: Dominant color (background or primary element)
- **20-30%**: Secondary color (supporting elements)
- **5-10%**: Accent color (CTAs, highlights, emphasis)

Never give all colors equal weight.

### Visual Elements

**Every slide needs a visual element** — image, chart, icon, or shape. Text-only slides are forgettable.

### Typography

Choose an interesting font pairing with personality:

| Header Font | Body Font |
|-------------|-----------|
| Georgia | Calibri |
| Arial Black | Arial |
| Cambria | Calibri Light |
| Palatino | Garamond |
| Impact | Arial |

**Sizing:**
- Slide title: 36-44pt bold
- Section header: 20-24pt bold
- Body text: 14-16pt
- Captions: 10-12pt muted

### Layout Variety

Don't repeat the same layout:
- Two-column (text left, illustration right)
- Icon + text rows (icon in colored circle)
- 2x2 or 2x3 grid layout
- Half-bleed image (full left/right side) with content overlay

## Editing Workflow

### Step 1: Unpack Presentation

```bash
python scripts/office/unpack.py presentation.pptx unpacked/
```

### Step 2: Edit Content and XML

Edit files in `unpacked/ppt/slides/` for slide content.

### Step 3: Pack Back to PPTX

```bash
python scripts/office/pack.py unpacked/ output.pptx --original presentation.pptx
```

## Quality Assurance (Required)

### Content QA

```bash
python -m markitdown output.pptx
```

Check for missing content, typos, wrong order.

### Visual QA (Use Subagents)

Convert slides to images and inspect for:
- Overlapping elements
- Text overflow or cut-off
- Uneven gaps between elements
- Low contrast text
- Low-contrast icons
- Insufficient margins (< 0.5" from edges)
- Misaligned columns or elements

## Common Mistakes to Avoid

- ❌ Text-only slides → ✅ Add images, charts, icons
- ❌ Multiple layout types randomly → ✅ Maintain consistent layout structure
- ❌ Center body text → ✅ Left-align paragraphs
- ❌ Default to blue → ✅ Pick colors specific to topic
- ❌ All colors equal weight → ✅ Use 60-20-10 dominance principle
- ❌ Generic fonts (Arial, Inter) → ✅ Choose distinctive fonts with personality
- ❌ Accent lines under titles → ✅ Use whitespace or background color

## Dependencies

```bash
pip install "markitdown[pptx]"
pip install Pillow

npm install -g pptxgenjs

# For PDF/image conversion:
# LibreOffice (auto-configured)
# Poppler (pdftoppm)
```

## Workflow Summary

1. **Analyze** content requirements
2. **Choose color palette** specific to topic/audience
3. **Design** layout structure (consistent across slides)
4. **Create or edit** slides
5. **Add visuals** (images, charts, icons, shapes)
6. **Convert to images** for visual QA
7. **Fix issues** found during QA
8. **Re-verify** affected slides

## When to Use This Skill

Use this skill when:
- User wants to create a presentation or slide deck
- Need to read, extract, or analyze presentation content
- Edit or update existing PowerPoint files
- Combine or split slide files
- Add visual design to presentations
- The primary deliverable is a .pptx file
