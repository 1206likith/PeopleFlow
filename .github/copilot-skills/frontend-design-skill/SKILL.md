---
name: frontend-design
description: Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, artifacts, posters, or applications. Generates creative, polished code and UI design that avoids generic AI aesthetics. Build landing pages, dashboards, React components, HTML/CSS layouts, or beautifully styled web UIs.
---

# Frontend Design – Creating Distinctive UIs

## Core Principle

**CREATE NO GENERIC AI INTERFACES.** Design with intention, commit to a distinctive aesthetic direction, and execute with precision.

## Design Thinking Framework

Before coding, understand the context and commit to a BOLD aesthetic direction.

### 5 Critical Questions

1. **Purpose**: What problem does this interface solve? Who uses it?
2. **Tone**: Pick an extreme:
   - Brutally minimal, Maximalist chaos, Retro-futuristic
   - Organic/natural, Luxury/refined, Playful/toy-like
   - Editorial/magazine, Brutalist/raw, Art deco/geometric
   - Soft/pastel, Industrial/utilitarian
3. **Constraints**: Technical requirements (framework, performance, accessibility)?
4. **Differentiation**: What's UNFORGETTABLE? What's the one thing someone remembers?
5. **Visual Direction**: How does this aesthetic live in color, typography, space, motion?

**CRITICAL**: Choose a clear conceptual direction and execute it with precision. Bold maximalism and refined minimalism both work — the key is intentionality.

## Frontend Aesthetics Guidelines

### Typography

Choose fonts that are beautiful, unique, and interesting:
- **Avoid**: Arial, Inter, Roboto, system fonts (generic)
- **Do**: Distinctive choices that elevate the interface
- **Pair**: A distinctive display font with a refined body font
- **Examples**: Georgia + Calibri, Cormorant + Montserrat, Playfair + Lato

### Color & Theme

- Command a cohesive aesthetic with CSS variables
- Dominant colors (60-70%) with sharp accents (5-10%)
- High-impact, personality-driven palettes
- Never timid, evenly-distributed colors

### Motion

- Use animations for effects and micro-interactions
- Prioritize CSS-only solutions for HTML
- Use Motion library for React when available
- Focus on high-impact moments:
  - One well-orchestrated page load with staggered reveals
  - Scroll-triggered effects
  - Hover states that surprise

### Spatial Composition

- Unexpected layouts, Asymmetry, Overlap
- Diagonal flow, Grid-breaking elements
- Generous negative space OR controlled density
- Intentional visual hierarchy

### Backgrounds & Visual Details

Create atmosphere and depth:
- Contextual effects and textures
- Creative forms: gradient meshes, noise textures, geometric patterns
- Layered transparencies, dramatic shadows
- Decorative borders, custom cursors, grain overlays

## What NOT to Do (AI Slop Indicators)

❌ **Avoid generic aesthetics:**
- Overused font families (Inter, Roboto, Arial)
- Clichéd color schemes (especially purple gradients on white)
- Predictable layouts and component patterns
- Cookie-cutter design lacking context-specific character
- Space Grotesk or other overused choices

✅ **Instead:**
- Interpret creatively, make unexpected choices
- Design specifically for context
- Vary between light/dark themes, different fonts, different aesthetics
- Every design should be unique

## Implementation Approach

Match implementation complexity to the aesthetic vision:

- **Maximalist designs**: Elaborate code with extensive animations and effects
- **Minimalist/refined designs**: Restraint, precision, careful spacing/typography, subtle details
- **Elegance**: Comes from executing the vision well

### HTML/CSS Starting Point

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Distinctive Design</title>
  <link href="https://fonts.googleapis.com/css2?family=[DISPLAY]+[BODY]" rel="stylesheet">
  <style>
    :root {
      --color-primary: #...;
      --color-secondary: #...;
      --font-display: '[Display Font]', serif;
      --font-body: '[Body Font]', sans-serif;
    }
    
    body {
      font-family: var(--font-body);
      color: var(--color-text);
      background: var(--color-bg);
    }
    
    h1, h2, h3 {
      font-family: var(--font-display);
    }
    
    /* Your distinctive design here */
  </style>
</head>
<body>
  <!-- Content -->
</body>
</html>
```

### React + TypeScript

```tsx
import { useState } from "react";

export default function App() {
  return (
    <div className="unique-aesthetic">
      {/* Distinctive design with custom styles */}
    </div>
  );
}
```

## Design Decision Examples

### Minimalist Luxury
- Clean serif typography, ample whitespace
- Accent color used sparingly
- Smooth animations, refined interactions
- Focus on negative space

### Brutalist Energy
- Bold, angular layouts, dark backgrounds
- Heavy typefaces, stark contrasts
- Intentional "rough" aesthetic
- Geometric forms, thick borders

### Organic Warmth
- Rounded forms, earthy palette
- Natural materials feel (paper texture)
- Fluid, flowing layouts
- Playful typography

### Editorial Power
- Large typography as visual element
- Strategic use of color blocks
- Magazine-like composition
- Visual hierarchy through size/weight

## Quality Checklist

- [ ] **Not generic**: Could this design be swapped for another without noticing?
- [ ] **Intentional**: Every color, font, spacing choice has purpose
- [ ] **Distinctive**: What makes this unforgettable?
- [ ] **Production-grade**: Works across browsers, responsive, accessible
- [ ] **WCAG AA minimum**: Text contrast ≥ 4.5:1
- [ ] **Functional**: All interactions work smoothly
- [ ] **Performance**: Fast load times, smooth animations
- [ ] **Keyboard accessible**: Tab navigation, focus states visible

## Common Patterns (Use Creatively!)

### Hero Section
```html
<section class="hero">
  <h1>Bold Statement</h1>
  <p>Supporting context</p>
  <button>Action</button>
</section>
```

### Feature Grid
```html
<div class="features">
  <div class="feature">
    <img src="icon.svg" alt="">
    <h3>Feature Title</h3>
    <p>Description</p>
  </div>
  <!-- Repeat -->
</div>
```

### Navigation
```html
<nav class="nav">
  <a href="/">Home</a>
  <a href="/about">About</a>
  <a href="/contact">Contact</a>
</nav>
```

## When to Use This Skill

Use this skill when:
- User asks to build web components, pages, or applications
- Need to create landing pages, dashboards, or UIs
- Building React components or HTML/CSS interfaces
- User wants styled, beautiful web UIs
- Creating posters or visual web content
- The goal is production-grade, distinctive design
- Styling/beautifying any web interface

## Remember

Claude is capable of extraordinary creative work. Don't hold back — show what can truly be created when thinking outside the box and committing fully to a distinctive vision.

Every design should be unique, intentional, and unforgettable. No generic aesthetics. Ever.
