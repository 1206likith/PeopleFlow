---
name: ui-ux-pro-max-skill
description: 'AI-powered design system generation and UI/UX expertise. Use when: building landing pages, designing dashboards, creating mobile UIs, choosing colors/typography, implementing design systems. Generates industry-specific design recommendations from 161 reasoning rules, 67 styles, and 161 color palettes.'
argument-hint: 'Describe the UI/UX task: "Build landing page for SaaS product", "Design dashboard", "Create mobile app", etc.'
user-invocable: true
---

# UI UX Pro Max Skill

## When to Use

- **Building UIs**: Landing pages, dashboards, mobile apps, portfolios
- **Design decisions**: Need colors, typography, patterns, or style recommendations
- **Design systems**: Generate complete, cohesive design systems for projects
- **Multi-stack work**: React, Vue, Next.js, Svelte, SwiftUI, Flutter, HTML+Tailwind, etc.
- **Pre-delivery**: Validate UI/UX against industry anti-patterns and best practices

## What This Skill Provides

A comprehensive design intelligence system with:
- **161 Industry-specific reasoning rules** (SaaS, Fintech, Healthcare, E-commerce, etc.)
- **67 UI Styles** (Glassmorphism, Claymorphism, Minimalism, Neumorphism, Bento Grid, etc.)
- **161 Color Palettes** aligned 1:1 with product types
- **57 Typography Pairings** with Google Fonts imports
- **99 UX Guidelines** for best practices and accessibility
- **25+ Chart types** for dashboards and analytics
- **Pre-delivery checklist** covering colors, spacing, accessibility, responsiveness

## How to Use

### Option 1: Interactive Mode
Simply describe what you want to build:
```
Build a landing page for my beauty spa business
Create a dashboard for healthcare analytics  
Design a portfolio site with dark mode
Make a mobile app UI for e-commerce
```

### Option 2: Design System Generation
Use the design system generator to create a complete system:
```
/ui-ux-pro-max-skill Generate design system for fintech banking app
```

### Option 3: Domain-Specific Search
Search for specific styles, colors, or typography:
```
I need glassmorphism UI patterns for a SaaS dashboard
What typography works best for a luxury e-commerce site?
Show me dark mode color palettes for crypto platforms
```

## Workflow

1. **Describe the project** - Product type, target audience, brand personality
2. **Design system generated** - AI analyzes and recommends:
   - Landing page pattern (hero, social proof, testimonials, etc.)
   - UI style (Glassmorphism, Claymorphism, Minimalism, etc.)
   - Industry-specific colors and typography
   - Key animations and effects
   - Anti-patterns to avoid
3. **Get stack-specific code** - React, Vue, Next.js, Svelte, SwiftUI, Flutter, etc.
4. **Pre-delivery validation** - Check against accessibility, responsiveness, best practices

## Supported Tech Stacks

| Category | Frameworks | Default |
|----------|-----------|---------|
| Web | React, Next.js, Astro, Vue, Nuxt.js, Nuxt UI, Svelte, Angular, Laravel | HTML+Tailwind |
| Mobile | SwiftUI (iOS), Jetpack Compose (Android), React Native, Flutter | React Native |
| Markup | HTML + Tailwind, shadcn/ui | HTML+Tailwind |

## Key Features by Use Case

### Landing Page Design
- Pattern matching (24 patterns): Hero-centric, Social proof, Storytelling, etc.
- Color psychology aligned with industry
- Conversion-focused section ordering
- Mobile-optimized responsive breakpoints

### Dashboard/Analytics
- 25+ chart type recommendations
- BI-specific style variants
- Dark/light mode support
- Data visualization best practices

### Design System Generation
- Complete color system (primary, secondary, CTA, background, text)
- Typography hierarchy with Google Fonts imports
- Spacing and layout grid
- Component patterns (buttons, cards, forms, modals)
- Accessibility compliance (WCAG AA minimum)

### Mobile App UI
- Platform-specific guidelines (iOS SwiftUI, Android Jetpack Compose)
- Navigation patterns
- Touch-friendly interactions
- Performance considerations

## Pre-Delivery Checklist

The skill verifies:
- ✓ No emoji icons (SVG-based instead: Heroicons, Lucide)
- ✓ Cursor-pointer on all clickable elements
- ✓ Smooth transitions (150-300ms)
- ✓ Text contrast 4.5:1 minimum for accessibility
- ✓ Focus states visible for keyboard navigation
- ✓ `prefers-reduced-motion` respected
- ✓ Responsive at 375px, 768px, 1024px, 1440px
- ✓ No anti-patterns for industry (e.g., avoid AI purple/pink in banking)

## Industry Examples

**Tech/SaaS**: Clean, minimal, focus on features and CTAs
**Finance**: Trust-focused, professional, avoiding "AI" aesthetics
**Healthcare**: Calm, accessible, HIPAA-compliant design
**E-commerce**: Conversion-optimized, trust signals, social proof
**Luxury**:Elegant typography, premium spacing, gold/silver accents
**Startups**: Modern, bold, emoji-light, tech-forward
**Nonprofits**: Warm, human-centric, clear calls-to-action

## Advanced: Design System Persistence

For multi-page projects, save your design system to get consistent UIs:

Use the [save-design-system script](./scripts/persist_design_system.py) to:
1. Generate and save `design-system/MASTER.md` (global source of truth)
2. Create `design-system/pages/<page-name>.md` (page-specific overrides)
3. Retrieve hierarchically: page-specific rules override master when present

See [Design System Reference](./references/design-system-hierarchy.md) for details.

## Design System Output Example

```
+------------------------+
| STYLE: Soft UI Evolution|
| COLORS: Sage + Blush    |
| TYPOGRAPHY: Cormorant  |
| PATTERN: Hero + Social  |
| EFFECTS: Soft shadows   |
+------------------------+

PRE-CHECKS:
[ ] No bright neons
[ ] Smooth transitions
[ ] WCAG AA contrast
[ ] 4 breakpoints
```

## Common Workflows

### Workflow: "Build SaaS landing page"
1. AI identifies: SaaS → Conversion-focused pattern
2. Recommends: Minimalism or Glassmorphism style
3. Generates: Color palette (brand trust), typography (readability)
4. Outputs: React + Tailwind code with design tokens
5. Checklist: Validates 10 pre-delivery criteria

### Workflow: "Design startup dashboard"
1. Identifies: Analytics + Startup market → Modern, data-centric
2. Recommends: Bento Grid or AI-Native UI style
3. Generates: Chart recommendations (25 types), color contrast rules
4. Outputs: React + shadcn/ui component code
5. Checklist: Accessibility focus

### Workflow: "Luxury e-commerce mobile app"
1. Identifies: E-commerce luxury → Trust + premium feel
2. Recommends: Soft UI or Neumorphism, gold accents
3. Selects: Typography (serif for luxury), spacing (generous)
4. Outputs: SwiftUI code with design tokens for iOS
5. Checklist: Touch-friendly, contrast, dark mode support

## Quick Reference: Commands

```bash
# Generate design system (CLI)
python3 .claude/skills/ui-ux-pro-max/scripts/search.py "beauty spa" --design-system

# With product name
python3 ... --design-system -p "Serenity Spa"

# Save to files (hierarchical)
python3 ... --design-system --persist

# Search specific domain
python3 ... "glassmorphism" --domain style
python3 ... "Cormorant Garamond" --domain typography
python3 ... "dashboard" --domain chart

# Stack-specific guidelines
python3 ... "form validation" --stack react
python3 ... "responsive layout" --stack html-tailwind
```

See [CLI Reference](./references/cli-commands.md) for all commands.

## Resources

- [Design System Persistence & Hierarchy](./references/design-system-hierarchy.md)
- [Industry Categories (161 types)](./references/industry-categories.md)
- [Available Styles (67 types)](./references/styles-catalog.md)
- [Color Psychology Guide](./references/colors.md)
- [Typography Pairings (57 combinations)](./references/typography.md)
- [UX Anti-Patterns by Industry](./references/anti-patterns.md)
- [Accessibility & Pre-delivery Checklist](./references/checklist.md)

## Tips & Best Practices

1. **Be specific** about product type (e.g., "SaaS B2B invoicing tool" vs just "SaaS")
2. **Mention stack early** if you have preference (React, Vue, SwiftUI, etc.)
3. **Use persisted design systems** for multi-page projects to ensure consistency
4. **Request dark mode** if needed — it's available across most styles
5. **Ask for component code** after getting design tokens (buttons, cards, forms)
6. **Validate accessibility** — the skill enforces WCAG AA pre-delivery
7. **Check anti-patterns** for your industry before shipping

## About UI UX Pro Max

- **Repository**: [github.com/nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
- **Website**: [uupm.cc](https://uupm.cc/)
- **Latest**: v2.5.0 with 161 reasoning rules, 67 styles, skills expansion
- **Open source**: MIT license, 60k+ GitHub stars

