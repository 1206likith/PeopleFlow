# Quick Start Guide

## Your First Design System with UI UX Pro Max

### Step 1: Describe Your Project

Start by describing what you want to build:

```
/ui-ux-pro-max-skill Build a landing page for my SaaS invoicing tool
```

Or use the expanded mode:

```
/ui-ux-pro-max-skill
Create a design system for a B2B SaaS platform targeting accountants.
Key requirements:
- Professional, trustworthy feel
- Light mode (minimal dark mode)
- Conversion-focused (sign-up CTA prominent)
- Target tech stack: React + Tailwind
```

### Step 2: Review the Generated Design System

The AI will generate a comprehensive design system that includes:

- **Colors**: Brand palette with accessibility validated
- **Typography**: Font pairs from Google Fonts with sizing scale
- **Components**: Button, card, form styles with variants
- **Layout**: Spacing grid, responsive breakpoints
- **Effects**: Shadows, transitions, animations
- **Checklist**: Pre-delivery validation

### Step 3: Save Your Design System (Optional)

For multi-page projects, persist your design system:

```bash
# Install script dependencies (if needed)
python3 -m pip install requests

# Generate and save to design-system/MASTER.md
cd your-project
python3 ~/.copilot/skills/ui-ux-pro-max-skill/scripts/design_system_gen.py \
    "B2B SaaS - Invoicing" -p "InvoiceApp"

# Creates:
# design-system/MASTER.md (global design system)
# design-system/pages/ (for page-specific overrides)
```

### Step 4: Check Accessibility

Before shipping, validate color contrast:

```bash
python3 ~/.copilot/skills/ui-ux-pro-max-skill/scripts/accessibility_check.py \
    design-system/MASTER.md
```

Output:
```
✓ Text on Background    Ratio: 10.25x  AAA (enhanced)
✓ Primary on Background Ratio: 5.12x   AA (at least 18.66px bold)
✓ CTA on Background     Ratio: 4.85x   AA (at least 18.66px bold)
```

### Step 5: Implement in Your Stack

Use the design tokens to build components. Examples:

**React + Tailwind:**
```jsx
const colors = {
  primary: 'rgb(232, 180, 184)',    // #E8B4B8
  cta: 'rgb(212, 175, 55)',         // #D4AF37
  bg: 'rgb(255, 245, 245)',         // #FFF5F5
};

export default function Button({ children }) {
  return (
    <button 
      className="px-6 py-3 rounded-lg text-white font-semibold transition-all duration-300 hover:shadow-lg"
      style={{ backgroundColor: colors.cta }}
    >
      {children}
    </button>
  );
}
```

**HTML + CSS:**
```html
<style>
  :root {
    --color-primary: #E8B4B8;
    --color-cta: #D4AF37;
    --color-bg: #FFF5F5;
  }
  
  .btn-primary {
    background: var(--color-cta);
    padding: 12px 24px;
    border-radius: 12px;
  }
</style>

<button class="btn-primary">Click me</button>
```

### Step 6: Multi-Page Projects – Use Hierarchy

For consistent design across pages:

1. **Global rules in MASTER.md** (colors, typography, base components)
2. **Page overrides in pages/dashboard.md** (only deviations)
3. **Automatic hierarchy**: Dashboard uses MASTER colors + its own layout

Example:

```markdown
# pages/dashboard.md

## Color Overrides
- Background: #1A1A1A (dark mode, instead of warm white)
- Text: #F0F0F0

## Layout Overrides
- Grid: 12 columns (vs 8 for landing page)
- Max-width: 1920px (vs 1440px)
```

### Step 7: Pre-Delivery Validation

Before shipping, run through the [Pre-Delivery Checklist](../references/checklist.md):

- [ ] Colors: No bright neon, ≥4.5:1 contrast
- [ ] Typography: Proper hierarchy, sizes consistent
- [ ] Icons: SVG-based, no emoji
- [ ] Responsive: Works at 375px, 768px, 1024px, 1440px
- [ ] Accessibility: Keyboard nav, focus states, alt text
- [ ] Performance: Lighthouse ≥90

### Common Workflows

#### Workflow A: "Quick Landing Page"
1. Describe: "SaaS B2B invoicing landing page"
2. Get: Design system + React code
3. Customize: Swap logo, content
4. Ship: ~30 min

#### Workflow B: "Complete Design System"
1. Describe: "Beauty spa multi-page site"
2. Save: `design_system_gen.py "beauty spa" -p "Serenity Spa"`
3. Override: `design-system/pages/homepage.md`, `booking.md`, etc.
4. Implement: Use MASTER + page-specific rules
5. Ship: ~2-3 days for entire site

#### Workflow C: "Dark Mode Variant"
1. Load: MASTER design system
2. Override: `pages/dark-mode.md` with new colors
3. Test: Contrast checker
4. Ship: Dark mode ready

### Troubleshooting

**Q: Colors don't look good on my background**
A: Use the accessibility checker:
```bash
python3 accessibility_check.py --colors "#YOURCOLOR" "#BACKGROUND"
```

**Q: Typography feels off**
A: Check the font pairing recommendation from the design system. May need
to increase line-height or letter-spacing.

**Q: Mobile looks cramped**
A: Ensure `<meta name="viewport" content="width=device-width">` is set.
Test at actual breakpoints: 375px, 768px, 1024px.

**Q: Keyboard navigation not working**
A: Add focus states to all interactive elements:
```css
button:focus {
  outline: 2px solid var(--color-cta);
  outline-offset: 2px;
}
```

### Next Steps

1. **Read**: [Design System Persistence Guide](../references/design-system-hierarchy.md)
2. **Explore**: [Industry Categories](../references/industry-categories.md) – See if yours is listed
3. **Validate**: [Pre-Delivery Checklist](../references/checklist.md) – 20-min validation
4. **Examples**: Check [HTML](./example-spa-landing.html) and [React](./example-dashboard.tsx) examples

### Getting Help

- **Design system not matching my brand?** Describe specific colors/fonts in follow-up prompt
- **Component code not working?** Provide framework (React, Vue, etc.) in request
- **Accessibility concerns?** Run the checker or ask for specific WCAG level
- **Anti-patterns detected?** Ask "What should I avoid for [industry]?"

---

**Remember**: The power of UI UX Pro Max is the industry-specific reasoning. The more
specific you are about your product (not just "SaaS" but "SaaS for small accounting firms"),
the better the recommendations.

