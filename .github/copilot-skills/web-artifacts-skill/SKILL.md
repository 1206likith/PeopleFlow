---
name: web-artifacts-builder
description: Suite of tools for creating elaborate, multi-component claude.ai HTML artifacts using modern frontend web technologies (React, Tailwind CSS, shadcn/ui). Use for complex artifacts requiring state management, routing, or shadcn/ui components - not for simple single-file HTML/JSX artifacts. Build web apps, dashboards, and interactive UIs.
---

# Web Artifacts Builder

## Overview

Create production-grade HTML artifacts using React, TypeScript, Tailwind CSS, and shadcn/ui components. For complex, interactive web applications.

## Quick Start

### Step 1: Initialize Project

```bash
bash scripts/init-artifact.sh <project-name>
cd <project-name>
```

This creates:
- ✅ React + TypeScript (via Vite)
- ✅ Tailwind CSS 3.4.1
- ✅ Path aliases (`@/`) configured
- ✅ 40+ shadcn/ui components pre-installed
- ✅ All Radix UI dependencies
- ✅ Parcel configured for bundling
- ✅ Node 18+ compatibility

### Step 2: Develop Your Artifact

Edit generated files under `src/`:
- `App.tsx` — Main component
- `index.css` — Global styles  
- `components/` — Reusable components

### Step 3: Bundle to Single HTML File

```bash
bash scripts/bundle-artifact.sh
```

Creates `bundle.html` — a self-contained artifact with all JavaScript, CSS, and dependencies inlined. This file can be directly shared in Claude conversations as an artifact.

### Step 4: Share Artifact

Share the bundled `bundle.html` file with the user so they can view it as an artifact in the conversation.

### Step 5: Testing (Optional)

Use available tools (Playwright, Puppeteer) to test the artifact if needed. Generally avoid upfront testing as it adds latency.

## Stack Details

- **Frontend**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS 3.4.1
- **Components**: shadcn/ui (40+ pre-installed)
- **Component Library**: Radix UI
- **Bundling**: Parcel
- **Package Manager**: Node.js/npm

## Design Guidelines

**AVOID "AI SLOP":**
- ❌ Excessive centered layouts
- ❌ Purple gradients
- ❌ Uniform rounded corners
- ❌ Inter font (generic)

**DO:**
- ✅ Intentional, purposeful design
- ✅ Unique aesthetic direction
- ✅ Purposeful spacing and layout
- ✅ Thoughtful typography
- ✅ High-quality visual hierarchy

## Common Development Tasks

### Adding shadcn/ui Components

Components are pre-installed. Use directly:

```tsx
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export function MyComponent() {
  return (
    <Card>
      <CardHeader>Title</CardHeader>
      <CardContent>
        <Button>Click me</Button>
      </CardContent>
    </Card>
  );
}
```

### Styling with Tailwind CSS

```tsx
<div className="flex flex-col gap-4 p-6 bg-gradient-to-br from-blue-50 to-indigo-50">
  <h1 className="text-3xl font-bold text-gray-900">Heading</h1>
  <p className="text-gray-600">Paragraph text</p>
</div>
```

### State Management

Use React hooks:

```tsx
import { useState } from "react";

export function Counter() {
  const [count, setCount] = useState(0);

  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>Increment</button>
    </div>
  );
}
```

### Routing (Optional)

```tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/about" element={<About />} />
      </Routes>
    </BrowserRouter>
  );
}
```

## Bundling Requirements

**Requirements for bundling:**
- Your project must have an `index.html` in the root directory
- All components and styles must be importable from the entry point

**What the script does:**
- Installs bundling dependencies (parcel, html-inline)
- Creates `.parcelrc` config with path alias support
- Builds with Parcel (no source maps)
- Inlines all assets into single HTML using html-inline

## Artifact Delivery

Once bundled (`bundle.html`), the artifact can be:
- Shared directly in conversation
- Viewed in browser
- Interacted with fully
- Downloaded by user

The single HTML file contains everything needed to run the React application.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Path aliases not working | Check `.parcelrc` config and `tsconfig.json` |
| Styles not applying | Ensure Tailwind CSS is imported in `index.css` |
| Components not appearing | Verify imports and component paths |
| Bundle too large | Optimize assets, tree-shake unused code |
| TypeScript errors | Update type definitions, check `tsconfig.json` |

## When to Use This Skill

Use this skill when:
- Creating complex, interactive web applications
- Building dashboards or data visualizations
- Need state management or routing
- Want to use shadcn/ui components
- The artifact requires Tailwind CSS styling
- Multi-component or multi-page artifacts needed
- Production-grade quality required

**Don't use for:** Simple single-file HTML/CSS artifacts (use basic HTML instead)

## References

- **shadcn/ui components**: https://ui.shadcn.com/docs/components
- **Tailwind CSS**: https://tailwindcss.com/docs
- **React Documentation**: https://react.dev
- **TypeScript**: https://www.typescriptlang.org/docs/
