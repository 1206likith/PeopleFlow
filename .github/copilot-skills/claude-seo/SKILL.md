---
name: claude-seo
version: 1.7.2
description: Comprehensive SEO analysis and auditing skill for Claude Code. Covers technical SEO, on-page optimization, content quality (E-E-A-T), schema markup, AI search optimization (GEO), local SEO, and Google API integrations.
author: AgriciDaniel
license: MIT
keywords:
  - SEO
  - search-engine-optimization
  - content
  - auditing
  - technical-seo
  - schema-markup
  - google-apis
compatibility:
  - Claude Code
  - Cursor
  - OpenCode
allowed-tools:
  - python
  - node
  - shell
  - api-requests
  - file-system
---

# Claude SEO - Enterprise SEO Skill

**Comprehensive SEO analysis and auditing framework** for Claude Code providing:
- **Full site audits** with parallel sub-agent delegation
- **15+ specialized skills** for deep analysis (technical, content, schema, images, etc.)
- **Google APIs integration** (Search Console, PageSpeed, CrUX, GA4)
- **Google SEO reports** (PDF/HTML with charts)
- **AI search optimization** (GEO) for AI Overviews, ChatGPT, Perplexity

## Use When

The user wants to:
- Audit a website for SEO issues
- Analyze single page performance
- Check schema markup correctness
- Optimize for AI search engines (Google AI, ChatGPT, Perplexity)
- Generate SEO-optimized competitors comparison pages
- Set up programmatic SEO at scale
- Configure hreflang for multi-language sites
- Analyze local SEO and Google Business Profile
- Generate PDF/HTML SEO report with metrics

## Core Commands

### `/seo audit <url>` - Full Site Audit
Comprehensive analysis with parallel subagent delegation:
- Technical SEO (9 categories)
- Content quality & E-E-A-T
- On-page optimization
- Schema markup analysis
- Image optimization
- Sitemap validation
- Core Web Vitals

### `/seo page <url>` - Deep Single Page Analysis
- Heading hierarchy and keyword optimization
- Internal/external link analysis
- Readability scores
- Content length vs competitors
- E-E-A-T signals

### `/seo schema <url>` - Schema & Structured Data
- Detection (JSON-LD, Microdata, RDFa)
- Validation against Google schema types
- Generation with templates
- Error reporting

### `/seo geo <url>` - AI Search Optimization (GEO)
New for 2026: Optimize for:
- Google AI Overviews
- ChatGPT web search
- Perplexity
- Other AI-powered search engines

### `/seo technical <url>` - Technical SEO Audit (9 Categories)
1. **Core Web Vitals** - LCP, INP, CLS metrics
2. **Mobile responsiveness** - Viewport settings, touch targets
3. **URL structure** - Consistency, trailing slashes
4. **Crawlability** - robots.txt, sitemap, Disallow rules
5. **Redirects** - Chains, loops, cross-domain
6. **Duplicate content** - Near-duplicates, canonical tags
7. **SSL/HTTPS** - Certificate validation, mixed content
8. **Speed** - Server response time, resource optimization
9. **Indexing** - Noindex tags, canonical implementation

### `/seo content <url>` - E-E-A-T Analysis
Evaluates **September 2025 Quality Rater Guidelines**:
- **Experience** - First-hand knowledge signals
- **Expertise** - Author credentials, depth
- **Authoritativeness** - Industry recognition, citations
- **Trustworthiness** - Contact info, transparency, security

### `/seo sitemap [generate|<url>]` - Sitemap Management
- Analyze existing XML sitemap
- Generate new sitemap with industry templates
- Validate entries and URLs

### `/seo images <url>` - Image Optimization
- Alt text analysis and recommendations
- Image format and compression
- Lazy loading implementation
- Image sitemap generation

### `/seo local <url>` - Local SEO Analysis
- Google Business Profile optimization
- NAP consistency auditing
- Citation and review analysis
- Local pack ranking factors

### `/seo programmatic <url|plan>` - Programmatic SEO
- Analyze existing programmatic pages
- Plan URL patterns and templates
- Prevent thin content and cannibalization
- Quality gates: WARNING at 100+ pages, HARD STOP at 500+

### `/seo competitor-pages <url>` - Generate Comparison Pages
- Competitor analysis and feature matrix
- Product schema markup with ratings
- SEO-optimized layout with CTAs
- Fairness and accuracy guidelines

### `/seo google [command] [url]` - Google SEO APIs
**4-tier credential system** for varying access levels:

**Tier 0** (API key):
- PageSpeed Insights + CrUX lab/field data
- Core Web Vitals trending

**Tier 1** (OAuth):
- Google Search Console (top queries, URL inspection)
- Indexing API (notify Google of changes)

**Tier 2** (GA4 config):
- Organic traffic analytics
- Top landing pages by impressions
- Device/country breakdown

**Tier 3** (Ads token):
- Keyword Planner access

## Key Features

### Core Web Vitals (Current Metrics)
- **LCP** (Largest Contentful Paint): Target < 2.5s
- **INP** (Interaction to Next Paint): Target < 200ms (replaced FID)
- **CLS** (Cumulative Layout Shift): Target < 0.1

### Schema Markup Types Supported
- **Core**: Article, NewsArticle, BlogPosting
- **E-commerce**: Product, Offer, AggregateRating
- **Video**: VideoObject, BroadcastEvent, Clip
- **Event**: Event, VirtualEvent
- **Local**: LocalBusiness, Organization
- **FAQPage** - Restricted to gov/health sites

### Quality Gates
⚠️ WARNING at 30+ location pages  
🛑 HARD STOP at 50+ location pages  
Auto-detects thin content and doorway pages

## Installation

```bash
# Claude Code plugin (recommended)
/plugin marketplace add AgriciDaniel/claude-seo
/plugin install claude-seo@AgriciDaniel-claude-seo

# Or manual
git clone --depth 1 https://github.com/AgriciDaniel/claude-seo.git
bash claude-seo/install.sh
```

## Quick Start

```bash
# Full site audit
/seo audit https://example.com

# Single page analysis
/seo page https://example.com/blog/post

# Schema markup check
/seo schema https://example.com

# Generate comparison page
/seo competitor-pages https://example.com

# Local SEO analysis
/seo local https://example.com/locations

# Setup Google APIs
/seo google setup
/seo google report cwv-audit
```

## Architecture

```
~/.claude/skills/seo/              # Main orchestrator skill
~/.claude/skills/seo-*/            # 15+ sub-skills
~/.claude/agents/seo-*.md          # 10+ subagents
```

## Extensions

### DataForSEO Integration
Live SERP data, backlinks, keyword research, AI visibility:
```bash
./extensions/dataforseo/install.sh
/seo dataforseo serp "best coffee shops"
/seo dataforseo backlinks example.com
/seo dataforseo ai-mentions "your brand"
```

### Banana AI Image Generation
Generate SEO images (OG previews, hero images, product photos):
```bash
./extensions/banana/install.sh
/seo image-gen og "Professional SaaS dashboard"
/seo image-gen hero "AI-powered content"
```

## Skill Ecosystem Integration

Works seamlessly with complementary skills:

| Skill | Connection |
|-------|------------|
| **Claude Blog** | Write SEO-optimized content |
| **Claude Banana** | Generate images for SEO assets |
| **AI Marketing Claude** | Post-audit marketing actions |

**Workflow Example:**
```
1. /seo audit https://example.com → identify gaps
2. /blog write "target keyword" → create content
3. /seo image-gen hero "topic" → generate images
4. /seo schema generate → add markup
```

## MCP Integrations

Integrates with MCP servers for live data:
- **@ahrefs/mcp** - Backlink data
- **Semrush** - Keyword research
- **Google Search Console** - Query data
- **DataForSEO** - SERP tracking

See [MCP Integration Guide](docs/MCP-INTEGRATION.md) for setup.

## Related Skills

- `marketingskills/seo-audit` - SEO audit framework
- `marketingskills/content-strategy` - Content planning
- `claude-blog` - Blog writing and optimization
- `deep-research-skill` - Audience research

## Requirements

- Python 3.10+
- Claude Code CLI
- Optional: Playwright for screenshots
- Optional: Google API credentials (for Tier 1-3)

## Troubleshooting

**Playwright not found?**
→ `pip install playwright && playwright install`

**Google APIs failing?**
→ Ensure credentials in `~/.claude/seo-google-auth.json`
→ Check tier level matches your configured credentials

**Slow audits?**
→ Reduce parallelism: `--workers=2`
→ Skip image analysis: `--skip-images`

## Resources

- [Installation guide](docs/INSTALLATION.md)
- [Commands reference](docs/COMMANDS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [MCP integration](docs/MCP-INTEGRATION.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## GitHub

https://github.com/AgriciDaniel/claude-seo

Built by [@AgriciDaniel](https://github.com/AgriciDaniel) | MIT License
