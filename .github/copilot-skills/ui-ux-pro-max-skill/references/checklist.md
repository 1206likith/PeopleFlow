# Pre-Delivery Checklist

Complete this checklist before shipping UI/UX. The UI UX Pro Max skill automates most validation.

## Visual Design

- [ ] **Colors**: No bright neon colors (specific exceptions only for branding)
- [ ] **Contrast**: Text contrast ≥ 4.5:1 (WCAG AA)
- [ ] **Consistency**: All buttons/cards follow design tokens
- [ ] **Spacing**: Grid-aligned (8px base recommended)
- [ ] **Shadows**: Soft, intentional (brand-appropriate)

## Typography

- [ ] **Font imports**: Google Fonts or system fallbacks declared
- [ ] **Hierarchy**: Clear h1, h2, h3, body, small text sizes
- [ ] **Line height**: ≥ 1.5 for body text, ≥ 1.2 for headings
- [ ] **Font weights**: Only necessary weights loaded (not all)

## Interactive Elements

- [ ] **Clickables**: All interactive elements have `cursor-pointer`
- [ ] **Hover states**: Visible feedback on hover (color, shadow, scale)
- [ ] **Active states**: Distinct active/selected state (not hover)
- [ ] **Transitions**: 150-300ms smooth easing (not instant jumps)
- [ ] **No blinks**: No flash of unstyled content (FOUC)

## Accessibility

- [ ] **Focus states**: Keyboard tab visible + focused outline
- [ ] **Alt text**: All images have meaningful alt attributes
- [ ] **ARIA labels**: Form inputs properly labeled
- [ ] **Semantic HTML**: Use `<button>`, `<nav>`, `<main>`, etc. (not divs)
- [ ] **Color alone**: Don't rely on color to convey meaning (use icons/text too)
- [ ] **Motion**: `prefers-reduced-motion` respected (no forced animations)
- [ ] **Keyboard nav**: All features accessible without mouse

## Responsiveness

- [ ] **Mobile (375px)**: All content visible, readable, usable
- [ ] **Tablet (768px)**: Layout optimized for mid-size screens
- [ ] **Desktop (1024px)**: Full experience
- [ ] **Wide (1440px)**: Doesn't stretch beyond max-width
- [ ] **Touch targets**: Buttons ≥ 48x48px on mobile
- [ ] **Images**: Responsive (srcset for scalable images)

## Icons & Images

- [ ] **No emojis as icons**: Use SVG icons (Heroicons, Lucide, Feather)
- [ ] **SVG optimization**: Icons compressed, no excess metadata
- [ ] **Icon sizing**: Consistent sizing across UI (16px, 24px, 32px)
- [ ] **Images**: Optimized, lazy-loaded where appropriate
- [ ] **Aspect ratios**: Locked to prevent layout shift (CLS)

## Animations & Interactions

- [ ] **Purposeful**: Every animation has intention (not decorative)
- [ ] **Duration**: 200-400ms for most animations
- [ ] **Easing**: Use ease-in-out or similar (not linear jumps)
- [ ] **GPU-accelerated**: Transform/opacity (not layout properties)
- [ ] **Mobile performance**: Reduced animations on slower devices

## Code Quality

- [ ] **Consistent naming**: BEM, camelCase, or clear convention
- [ ] **No inline styles**: Use CSS classes/modules
- [ ] **No hardcoded colors**: Use design tokens/variables
- [ ] **No !important**: Cascade should work naturally
- [ ] **Responsive images**: Picture element, srcset
- [ ] **Minified CSS/JS**: Production-ready builds

## Browser Compatibility

- [ ] **Modern engines**: Works in Chrome, Firefox, Safari, Edge
- [ ] **Mobile browsers**: iOS Safari, Android Chrome
- [ ] **Fallbacks**: Graceful degradation for older browsers
- [ ] **No console errors**: Check DevTools for warnings/errors

## Performance

- [ ] **Lighthouse score**: ≥90 performance, ≥90 accessibility
- [ ] **Bundle size**: CSS+JS optimized
- [ ] **Paint performance**: First paint < 2s
- [ ] **Jank-free**: 60fps scrolling/interactions
- [ ] **Core Web Vitals**: LCP < 2.5s, CLS < 0.1, FID < 100ms

## Industry Anti-Patterns

### Tech/SaaS
- [ ] Feature-focused, not over-designed
- [ ] Clear information hierarchy
- [ ] Credibility signals (testimonials, logos)

### Finance/Banking
- [ ] No "AI" purple/pink gradients
- [ ] Professional, trustworthy tone
- [ ] Security indicators visible

### Healthcare
- [ ] HIPAA-compliant (no exposed data)
- [ ] Calming, accessible color palette
- [ ] Clear trust signals

### E-commerce
- [ ] High-contrast CTAs
- [ ] Social proof visible
- [ ] Clear pricing and checkout flow

### Luxury
- [ ] Premium spacing (generous white space)
- [ ] Elegant typography (serif preferred)
- [ ] High-quality imagery
- [ ] Subtle animations (not flashy)

## Validation Script

```bash
# Run automated checks
npm run lint:css
npm run lint:a11y
npm run lighthouse

# Accessibility audit
axe devtools [URL]

# Manual checks
# 1. Zoom to 200% - Still readable?
# 2. Disable CSS - Content readable in order?
# 3. Keyboard-only - Can you navigate?
# 4. Dark mode - Colors still visible?
# 5. Screen reader - Content makes sense?
```

## Sign-Off Criteria

Before marking as complete:

- [ ] Checklist 100% complete
- [ ] No console errors
- [ ] Lighthouse ≥ 90 (performance + accessibility)
- [ ] Tested on 2+ browsers
- [ ] Tested on mobile (375px, 768px)
- [ ] Keyboard navigation functional
- [ ] Design tokens documented
- [ ] Team review passed

