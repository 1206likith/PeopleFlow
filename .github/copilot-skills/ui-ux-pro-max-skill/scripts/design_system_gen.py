#!/usr/bin/env python3
"""
Design System Generator - Create persistent design system for projects

Usage:
    python3 design_system_gen.py "SaaS dashboard" -p "MyProject"
    python3 design_system_gen.py "beauty spa" -p "Serenity Spa" --dark-mode
"""

import json
import argparse
from pathlib import Path
from datetime import datetime

# Design system templates
DESIGN_SYSTEM_TEMPLATE = """# Design System – {project_name}

**Generated**: {timestamp}
**Category**: {category}
**Style**: {style}

## Color Palette

- **Primary**: {primary} ({primary_name})
- **Secondary**: {secondary} ({secondary_name})
- **CTA**: {cta} ({cta_name})
- **Background**: {background} ({background_name})
- **Text**: {text} ({text_name})
- **Error**: #E53935 (Red)
- **Warning**: #F57C00 (Orange)
- **Success**: #43A047 (Green)

**Rationale**: {color_rationale}

## Typography

### Google Fonts Import
```css
@import url('https://fonts.googleapis.com/css2?family={display_font}:wght@400;700&family={body_font}:wght@400;500;700&display=swap');
```

### Font Stack
- **Display**: '{display_font}', serif
- **Body**: '{body_font}', sans-serif

### Sizes
- **h1**: 48px, 700 weight, line-height 1.2
- **h2**: 32px, 700 weight, line-height 1.3
- **h3**: 24px, 600 weight, line-height 1.4
- **Body**: 16px, 400 weight, line-height 1.6
- **Small**: 14px, 400 weight, line-height 1.5

## Spacing Grid

Base unit: 8px

- **xs**: 4px    (half-unit)
- **sm**: 8px
- **md**: 16px   (2x)
- **lg**: 24px   (3x)
- **xl**: 32px   (4x)
- **2xl**: 48px  (6x)
- **3xl**: 64px  (8x)
- **4xl**: 80px  (10x)
- **5xl**: 96px  (12x)

## UI Style & Effects

**Pattern**: {pattern}
- Format: {pattern_description}
- Section order: Hero → {sections}
- CTA placement: Above fold + repeated

**Style**: {ui_style}
- Key characteristics: {style_characteristics}

**Shadows**:
```css
--shadow-sm: 0 2px 4px rgba(0, 0, 0, 0.05);
--shadow-md: 0 4px 12px rgba(0, 0, 0, 0.1);
--shadow-lg: 0 8px 16px rgba(0, 0, 0, 0.12);
```

**Transitions**: 200-300ms ease-in-out

## Components

### Buttons
- **Primary**: CTA background, white text, 12px padding
- **Secondary**: Border (cta color), transparent bg, 12px padding
- **Ghost**: Text only (text color), no background
- **Hover**: Slight shadow + 5% darker
- **Focus**: Outline 2px offset 2px

### Cards
- **Shadow**: --shadow-md
- **Radius**: 12px
- **Padding**: 24px
- **Border**: None (shadow only)
- **Hover**: Subtle lift (shadow-lg)

### Forms
- **Input bg**: Light variant of background
- **Border**: 1px solid (secondary color)
- **Focus**: Border {primary}, blue outline 2px
- **Label**: 14px, 600 weight, margin-bottom 8px

### Navigation
- **Header**: Sticky, soft shadow
- **Links**: {text} color, underline on hover
- **Active**: {cta} color + underline

## Anti-Patterns

Avoid these at all costs:

- ❌ {anti_pattern_1}
- ❌ {anti_pattern_2}
- ❌ {anti_pattern_3}

## Accessibility Compliance

- Contrast ratio: ≥ 4.5:1 for normal text ✓
- Keyboard navigation: Full support ✓
- Focus indicators: Visible on all interactive elements ✓
- prefers-reduced-motion: Respected ✓
- Mobile touch targets: ≥ 48x48px ✓

## Responsive Breakpoints

- **Mobile**: 375px
- **Tablet**: 768px
- **Desktop**: 1024px
- **Wide**: 1440px (max-width)

## Implementation Examples

### React + Tailwind
```jsx
// Use CSS variables for colors
const Button = () => (
  <button className="px-3 py-2 rounded-md bg-[var(--color-cta)] text-white hover:shadow-md transition-shadow duration-300">
    Click me
  </button>
);
```

### HTML + CSS
```html
<button class="btn btn-primary">Click me</button>
```

```css
:root {{
  --color-primary: {primary};
  --color-secondary: {secondary};
  --color-cta: {cta};
}}

.btn-primary {{
  background-color: var(--color-cta);
  color: white;
  padding: 12px 24px;
  transition: all 300ms ease-in-out;
}}
```

## Next Steps

1. **Export tokens**: Use this file to generate design tokens for your framework
2. **Create overrides**: For multi-page projects, see `/pages/[page-name].md`
3. **Component library**: Build reusable components matching these specs
4. **Test accessibility**: Run axe DevTools or WAVE on your implementation
5. **Ship with confidence**: Run pre-delivery checklist before launch
"""

PAGE_OVERRIDE_TEMPLATE = """# {page_name} Page – Design System Overrides

**Applies to**: /{page_slug}*

**Rationale**: {override_rationale}

## Color Overrides

{color_overrides_section}

## Layout Overrides

- **Grid**: {grid_cols} columns
- **Max-width**: {max_width}
- **Padding**: {padding}

## Component Overrides

{component_overrides_section}

## Typography Overrides

{typography_overrides_section}

## Special Effects

{effects_section}

## Notes

{notes}
"""


def generate_design_system(project_name, category, output_dir=None):
    """Generate a design system MASTER file"""
    
    if output_dir is None:
        output_dir = Path("design-system")
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Example data - in real implementation, use actual reasoning engine data
    data = {
        "project_name": project_name,
        "timestamp": datetime.now().isoformat(),
        "category": category,
        "style": "Soft UI Evolution",
        "primary": "#E8B4B8",
        "primary_name": "Soft Pink",
        "secondary": "#A8D5BA",
        "secondary_name": "Sage Green",
        "cta": "#D4AF37",
        "cta_name": "Gold",
        "background": "#FFF5F5",
        "background_name": "Warm White",
        "text": "#2D3436",
        "text_name": "Charcoal",
        "color_rationale": "Calming palette with premium gold accents for luxury feel",
        "display_font": "Cormorant+Garamond",
        "body_font": "Montserrat",
        "pattern": "Hero + Social Proof",
        "pattern_description": "Emotion-driven with trust elements",
        "sections": "Services → Testimonials → Booking → Contact",
        "ui_style": "Soft UI Evolution",
        "style_characteristics": "Soft shadows, subtle depth, calming, premium feel, organic shapes",
        "anti_pattern_1": "Bright neon colors or harsh contrasts",
        "anti_pattern_2": "Rapid flash animations or jarring transitions",
        "anti_pattern_3": "AI purple/pink gradients (avoid generic SaaS look)",
    }
    
    # Generate MASTER.md
    master_content = DESIGN_SYSTEM_TEMPLATE.format(**data)
    master_path = output_dir / "MASTER.md"
    master_path.write_text(master_content)
    print(f"✓ Generated {master_path}")
    
    # Create pages directory
    pages_dir = output_dir / "pages"
    pages_dir.mkdir(exist_ok=True)
    print(f"✓ Created {pages_dir} for page-specific overrides")
    
    # Create README
    readme = """# Design System

This folder contains the design system for your project.

## Structure

- **MASTER.md** - Global source of truth for colors, typography, components, etc.
- **pages/** - Page-specific overrides (only include deviations from MASTER)

## Usage

When building a page, follow these steps:

1. Read `MASTER.md` for base rules
2. Check if `pages/[page-name].md` exists
3. If page file exists, override MASTER rules as needed
4. Implement using specified colors, typography, and components

## Creating Page Overrides

```bash
python3 design_system_gen.py --page "dashboard" \\
    --color-override "background:#1A1A1A" \\
    --typography-override "size-body:14px"
```

## Hierarchy Example

```
MASTER.md defines:
- Primary color: #E8B4B8
- Body font size: 16px

pages/dashboard.md overrides:
- Primary color: Not overridden (uses #E8B4B8)
- Body font size: 14px (different density)
- New: Dark mode background #1A1A1A
```

## Integration

Import into your components:

**React:
```jsx
import designSystem from '../design-system/MASTER.md';
// Create design tokens from theme data
```

**HTML:
```html
<!-- Load CSS variables -->
<link rel="stylesheet" href="design-system/_tokens.css">
```

See [Design System Persistence Guide](../../references/design-system-hierarchy.md) for full details.
"""
    
    readme_path = output_dir / "README.md"
    readme_path.write_text(readme)
    print(f"✓ Generated {readme_path}")
    
    print(f"\\n✨ Design system created at {output_dir}")
    print(f"   Next: Add page overrides to {pages_dir}/")


def main():
    parser = argparse.ArgumentParser(
        description="Generate persistent design system for projects"
    )
    parser.add_argument("category", help="Product category (e.g., 'beauty spa', 'SaaS')")
    parser.add_argument("-p", "--project", default="MyProject", help="Project name")
    parser.add_argument("-o", "--output", help="Output directory (default: design-system/)")
    parser.add_argument("--dark-mode", action="store_true", help="Include dark mode variants")
    parser.add_argument("--page", help="Generate page-specific override")
    
    args = parser.parse_args()
    
    generate_design_system(args.project, args.category, args.output)
    
    if args.page:
        print(f"\\n💡 Tip: Create page overrides with --page '{args.page}'")


if __name__ == "__main__":
    main()
