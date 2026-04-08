# Design System Persistence & Hierarchy

For multi-page projects, UI UX Pro Max supports hierarchical design system storage with MASTER + page-specific overrides.

## folder Structure

```
project-root/
├── design-system/
│   ├── MASTER.md           # Global source of truth
│   ├── pages/
│   │   ├── homepage.md     # Override for homepage only
│   │   ├── dashboard.md    # Override for dashboard
│   │   └── checkout.md     # Override for checkout
│   └── components/         # Shared component specifications
│       ├── buttons.md
│       └── cards.md
```

## MASTER.md Format

The global design system includes:

```markdown
# Design System – [Project Name]

## Color Palette
- **Primary**: #E8B4B8 (Soft Pink)
- **Secondary**: #A8D5BA (Sage Green)
- **CTA**: #D4AF37 (Gold)
- **Background**: #FFF5F5 (Warm White)
- **Text**: #2D3436 (Charcoal)

## Typography
- **Display**: Cormorant Garamond (Google Fonts)
- **Body**: Montserrat (Google Fonts)
- **Sizes**: h1=48px, h2=32px, body=16px

## Spacing Grid
- Base: 8px
- Scale: 8, 16, 24, 32, 48, 64, 80, 96

## Style & Effects
- **Pattern**: Hero + Social Proof
- **UI Style**: Soft UI Evolution
- **Shadows**: Soft (0 4px 12px rgba), Medium (0 8px 16px rgba)
- **Transitions**: 200-300ms ease-in-out

## Components
- Buttons: Primary (CTA color), Secondary (border), Ghost (text)
- Cards: Soft shadow, rounded corners (12px), padding 24px
- Forms: Light input backgrounds, clear focus states
- Navigation: Sticky header with soft shadow

## Anti-Patterns
- No bright neon colors
- No harsh gradients
- No playful animations for this brand
```

## Page Override Format

A page-override file (`pages/dashboard.md`) includes ONLY deviations:

```markdown
# Dashboard Page – Design System Overrides

**Applies to**: /dashboard and related pages

## Color Overrides
- **Background**: Dark mode #1A1A1A (instead of warm white)
- **Text**: #F0F0F0 (instead of charcoal)
- Chart colors: See chart palette below

## Component Overrides
- Grid layout: 12 columns (instead of standard 8)
- Charts: Glassmorphism cards with blur effect

## Pattern Override
- No hero section on this page
- Dashboard-specific sidebar navigation

## Notes
Dark mode active; reduced motion respected; data density increased.
```

## Hierarchy Retrieval Algorithm

When building a specific page:

1. **Load MASTER.md** - Get all global rules
2. **Check for page-override** - `design-system/pages/[page-name].md`
3. **Merge rules**:
   - If page file exists: Use page rules + MASTER rules (page overrides)
   - If no page file: Use MASTER rules exclusively

## Context Prompt for AI

Use this prompt when referencing your design system:

```
I am building the [Page Name] page for [Project Name].

Please read the design system files:
1. design-system/MASTER.md - Global design system
2. Check if design-system/pages/[page-name].md exists
3. If page file exists, prioritize its rules (overrides take precedence)
4. If not, use MASTER rules exclusively

Design the [Page Name] page following all applicable rules.
Generate [React/Vue/HTML] code with:
- Colors from palette
- Typography from hierarchy
- Components matching specs
- All spacing/transitions defined
```

## Persistence Commands

### Generate and persist (CLI):
```bash
uipro search "SaaS dashboard" --design-system --persist -p "MyApp"
```

This creates:
- `design-system/MASTER.md` (complete system)
- Empty `design-system/pages/` folder

### Create page override:
```bash
uipro search "dark mode analytics" --design-system --persist -p "MyApp" --page "dashboard"
```

This creates:
- `design-system/pages/dashboard.md` with page-specific rules

## Benefits

| Use Case | How Hierarchy Helps |
|----------|-------------------|
| Multi-page site | Consistent baseline + page-specific tweaks |
| Dark mode | MASTER defines light mode, page overrides for dark |
| A/B testing | MASTER as control, alternative pages as experiments |
| Team collab | MASTER as shared source, devs customize per page |
| Maintenance | Change colors once in MASTER, update globally |

## Example: SaaS App

```
MASTER.md
├── Primary brand colors
├── Standard typography
├── Component specs (buttons, cards, forms)
└── Animation timings

pages/landing.md       # Hero-focused, conversion CTAs
pages/dashboard.md     # Dark mode, data density, sidebar nav
pages/settings.md      # Minimal, form-heavy
pages/pricing.md       # Feature showcase, comparison table
```

Each page inherits MASTER but can override layout, colors, or component behavior.

## Best Practices

1. **Keep MASTER stable** - Only update for global changes
2. **Use page overrides** for: Dark mode, layouts, specific copy
3. **Document rationale** - Why does this page differ from MASTER?
4. **Test hierarchy** - Build a page using only MASTER, then with overrides
5. **Sync with team** - Use version control for design-system/ folder

