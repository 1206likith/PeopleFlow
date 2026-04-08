---
name: docx
description: Use this skill whenever the user wants to create, read, edit, or manipulate Word documents (.docx files). Triggers include any mention of 'Word doc', 'word document', '.docx', or requests to produce professional documents with formatting like tables of contents, headings, page numbers, or letterheads. Also use when extracting or reorganizing content from .docx files, inserting or replacing images, performing find-and-replace, working with tracked changes or comments, or converting content into a polished Word document.
---

# DOCX – Creating and Editing Word Documents

## Overview

Create, read, edit, and analyze Word documents (.docx files). Use for reports, proposals, letters, and formatted documents with tables, images, and complex layouts.

## Quick Reference

| Task | Approach |
|------|----------|
| Read/analyze content | `pandoc document.docx -o output.md` |
| Create new document | Use docx-js library |
| Edit existing document | Unpack XML → edit → repack |
| Extract images | Unpack → extract from media folder |
| Add tracked changes | Edit XML with proper markup |

## Reading Content

### Extract Text and Metadata

```bash
# Convert to Markdown
pandoc document.docx -o output.md

# Get raw XML
python scripts/office/unpack.py document.docx unpacked/

# Track changes during extraction
pandoc --track-changes=all document.docx -o output.md
```

## Creating New Documents

### Setup

Install docx library:
```bash
npm install -g docx
```

### Basic Document

```javascript
const { Document, Packer, Paragraph, TextRun } = require('docx');
const fs = require('fs');

const doc = new Document({
  sections: [{
    children: [
      new Paragraph({
        children: [new TextRun("Hello World")]
      }),
      new Paragraph({
        children: [new TextRun("This is a paragraph")]
      })
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("output.docx", buffer);
});
```

### Critical Settings for docx-js

**IMPORTANT: Always set page size explicitly** — docx-js defaults to A4.

```javascript
sections: [{
  properties: {
    page: {
      size: {
        width: 12240,    // 8.5 inches (US Letter width)
        height: 15840    // 11 inches (US Letter height)
      },
      margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } // 1" margins
    }
  },
  children: [/* content */]
}]
```

**For landscape orientation**: Pass portrait dimensions and let docx-js handle swap:
```javascript
size: {
  width: 12240,    // SHORT edge
  height: 15840,   // LONG edge
  orientation: PageOrientation.LANDSCAPE
},
```

## Document Components

### Headings

```javascript
const { HeadingLevel } = require('docx');

new Paragraph({
  heading: HeadingLevel.HEADING_1,
  children: [new TextRun("Chapter 1")]
})

// CRITICAL: Set outlineLevel for TOC (0 for H1, 1 for H2, etc.)
// Use exact style IDs: "Heading1", "Heading2", etc.
```

### Lists

```javascript
// Bullets (NEVER use unicode bullets)
new Paragraph({
  numbering: { reference: "bullets", level: 0 },
  children: [new TextRun("Bullet item")]
})

// Numbered Lists
new Paragraph({
  numbering: { reference: "numbers", level: 0 },
  children: [new TextRun("Numbered item")]
})
```

### Tables

**CRITICAL: Tables need dual widths** — set both `columnWidths` on table AND `width` on each cell.

```javascript
new Table({
  width: { size: 9360, type: WidthType.DXA },  // Always DXA, never PERCENTAGE
  columnWidths: [4680, 4680],  // Must sum to table width
  rows: [
    new TableRow({
      children: [
        new TableCell({
          borders: { /* ... */ },
          width: { size: 4680, type: WidthType.DXA },  // Also set cell width
          margins: { top: 80, bottom: 80, left: 120, right: 120 },
          children: [new Paragraph("Cell content")]
        })
      ]
    })
  ]
})
```

### Images

```javascript
// CRITICAL: type parameter is REQUIRED
new Paragraph({
  children: [new ImageRun({
    type: "png",  // Required: png, jpg, jpeg, gif, bmp, svg
    data: fs.readFileSync("image.png"),
    transformation: { width: 200, height: 150 },
    altText: {
      title: "Title",
      description: "Description",
      name: "Name"
    }
  })]
})
```

### Page Breaks

```javascript
// CRITICAL: PageBreak must be inside a Paragraph
new Paragraph({ children: [new PageBreak()] })

// Or use pageBreakBefore
new Paragraph({ pageBreakBefore: true, children: [new TextRun("New page")] })
```

### Headers and Footers

```javascript
sections: [{
  properties: {
    page: { margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } }
  },
  headers: {
    default: new Header({ 
      children: [new Paragraph("Header text")] 
    })
  },
  footers: {
    default: new Footer({
      children: [new Paragraph("Page "), new PageNumber()]
    })
  },
  children: [/* content */]
}]
```

## Editing Existing Documents

### Step 1: Unpack

```bash
python scripts/office/unpack.py document.docx unpacked/
```

### Step 2: Edit XML

Edit files in `unpacked/word/`. Use smart quotes for professional typography:

| Entity | Character |
|--------|-----------|
| `&#x2018;` | ' (left single) |
| `&#x2019;` | ' (right single/apostrophe) |
| `&#x201C;` | " (left double) |
| `&#x201D;` | " (right double) |

Example:
```xml
<w:t>Here&#x2019;s a quote: &#x201C;Hello&#x201D;</w:t>
```

### Tracked Changes

```xml
<!-- Insertion -->
<w:ins w:id="1" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r><w:t>inserted text</w:t></w:r>
</w:ins>

<!-- Deletion (use w:delText instead of w:t) -->
<w:del w:id="2" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r><w:delText>deleted text</w:delText></w:r>
</w:del>
```

### Comments

```bash
python scripts/comment.py unpacked/ 0 "Comment text"
python scripts/comment.py unpacked/ 1 "Reply text" --parent 0
```

Then add markers to document.xml (comment markers are siblings of `<w:r>`, never inside):

```xml
<w:commentRangeStart w:id="0"/>
<w:r><w:t>text to comment</w:t></w:r>
<w:commentRangeEnd w:id="0"/>
<w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr>
  <w:commentReference w:id="0"/>
</w:r>
```

### Step 3: Pack

```bash
python scripts/office/pack.py unpacked/ output.docx --original document.docx
```

Auto-repair will fix common issues.

## Critical Rules for docx-js

- **Set page size explicitly**: Use US Letter (12240 x 15840 DXA)
- **Never use `\n`**: Use separate Paragraph elements
- **Never use unicode bullets**: Use `LevelFormat.BULLET` with numbering config
- **PageBreak must be in Paragraph**: Never standalone
- **ImageRun requires `type`**: Always specify png/jpg/etc
- **Always set table `width` with DXA**: Never use `WidthType.PERCENTAGE`
- **Tables need dual widths**: `columnWidths` array AND cell `width`, both must match
- **Always add cell margins**: Makes content readable
- **Use `ShadingType.CLEAR`**: Never SOLID for table shading
- **Override built-in heading styles**: Use exact IDs ("Heading1", "Heading2", etc.)
- **Include `outlineLevel`**: Required for Table of Contents

## When to Use This Skill

Use this skill when:
- User wants to create, read, edit, or manipulate .docx files
- Generate professional documents (reports, proposals, letters)
- Extract or reorganize content from Word documents
- Insert, replace, or update images
- Perform find-and-replace operations
- Work with tracked changes or comments
- Convert content into a polished Word document
- The primary deliverable is a .docx file
