---
name: marketing-skills
version: 2.0.0
description: Collection of 24+ AI agent skills for marketing tasks including conversion optimization (CRO), copywriting, SEO, paid ads, email automation, analytics, funnel, and revenue operations. Skills reference shared product context document.
author: Corey Haines
license: MIT
keywords:
  - marketing
  - conversion-optimization
  - copywriting
  - email
  - seo
  - paid-advertising
  - analytics
compatibility:
  - Claude Code
  - Cursor
  - Codex
  - Gemini CLI
allowed-tools:
  - node
  - python
  - shell
  - file-system
---

# Marketing Skills for AI Agents

**24+ interconnected marketing skills** with a **shared context pattern** where all skills reference your `product-marketing-context.md` file first—enabling consistent messaging across copywriting, email, landing pages, and strategy.

## Use When

The user wants to:
- Create or optimize landing pages for conversions
- Write marketing copy (homepage, ads, emails)
- Analyze SEO opportunities and implement improvements
- Design customer email sequences and flows
- Plan A/B tests or analyze campaigns
- Design customer journeys and customer research
- Build referral programs or growth strategies
- Create sales collateral or pitch decks
- Set up analytics and funnels
- Plan product launches or feature announcements

## Skills Dependency Tree

All skills reference a **foundation document** first:

```
Product-Marketing-Context (shared by all)
├─ SEO & Content (seo-audit, ai-seo, schema)
├─ Copywriting (copywriting, copy-editing, cold-email)
├─ Conversion (page-cro, form-cro, signup-flow-cro)
├─ Analysis (analytics-tracking, ab-test-setup)
├─ Email (email-sequence)
├─ Growth (referral-program, free-tool-strategy)
├─ Paid (paid-ads, ad-creative)
└─ Sales (revops, sales-enablement, pricing)
```

## Core Skills

### **📝 product-marketing-context**
**Foundation skill**—reads/creates shared `product-marketing-context.md`

Contains:
- Product positioning & value prop
- Target audience personas
- Messaging pillars
- Competitive differentiation
- Brand voice and values

Every other skill checks this first.

### **🎯 Conversion Optimization (6 skills)**
- **page-cro** - Homepage, landing pages, any marketing page
- **signup-flow-cro** - Registration flows, account creation, trial
- **onboarding-cro** - Post-signup activation, first-run experience
- **form-cro** - Lead capture, contact, support forms
- **popup-cro** - Modals, overlays, slide-ins, banners
- **paywall-upgrade-cro** - In-app upsells, feature gates

### **✍️ Content & Copy (5 skills)**
- **copywriting** - Marketing page copy, hero sections, CTAs
- **copy-editing** - Edit/polish existing copy, refresh outdated
- **cold-email** - B2B outreach sequences
- **email-sequence** - Automated drip campaigns, lifecycle flows
- **social-content** - LinkedIn, Twitter/X, Instagram content

### **🔍 SEO & Discovery (5 skills)**
- **seo-audit** - Technical and on-page SEO analysis
- **ai-seo** - AI search optimization (Perplexity, ChatGPT, AEO)
- **programmatic-seo** - Scale page generation with templates
- **site-architecture** - URL structure, navigation, hierarchy
- **schema-markup** - Structured data, rich results

### **📊 Measurement & Strategy (7 skills)**
- **analytics-tracking** - GA4/analytics setup and validation
- **ab-test-setup** - Experiment design and analysis
- **marketing-ideas** - 140+ SaaS marketing idea bank
- **marketing-psychology** - Mental models, persuasion principles
- **launch-strategy** - Product/feature launches and announcements
- **pricing-strategy** - Pricing models, packaging, monetization
- **customer-research** - Research synthesis and analysis

### **💰 Sales & Revenue (4 skills)**
- **revops** - Lead lifecycle, MQL→SQL, revenue operations
- **sales-enablement** - Pitch decks, objection docs, demo scripts
- **competitor-alternatives** - Comparison pages, positioning
- **sales-research** - Competitive analysis, ICP research

### **🚀 Growth & Distribution (3 skills)**
- **free-tool-strategy** - Lead magnets, marketing calculators
- **referral-program** - Referral, affiliate, word-of-mouth
- **paid-ads** - Google Ads, Meta, LinkedIn, Twitter campaigns
- **ad-creative** - Bulk ad generation, iteration, scaling

### **❌ Retention & Churn (1 skill)**
- **churn-prevention** - Cancellation flows, save offers, dunning

## Installation

Choose your method:

### Option 1: CLI Install (Recommended)
```bash
# Install all skills
npx skills add coreyhaines31/marketingskills

# Install specific skills
npx skills add coreyhaines31/marketingskills --skill page-cro copywriting

# List available
npx skills add coreyhaines31/marketingskills --list
```

### Option 2: Claude Code Plugin
```bash
# Add marketplace
/plugin marketplace add coreyhaines31/marketingskills

# Install all marketing skills
/plugin install marketing-skills
```

### Option 3: SkillKit (Multi-Agent)
```bash
# Works across Claude Code, Cursor, Copilot, etc.
npx skillkit install coreyhaines31/marketingskills
```

### Option 4: Git Clone
```bash
git clone https://github.com/coreyhaines31/marketingskills.git
cp -r marketingskills/skills/* ~/.claude/skills/
```

## Usage Examples

### Example 1: Create Marketing Page
```bash
> Help me write homepage copy for my SaaS

# Triggers:
# 1. product-marketing-context (reads positioning)
# 2. copywriting (writes hero section)
# 3. page-cro (suggests conversion elements)
# 4. schema-markup (adds structured data)
```

### Example 2: Optimize Landing Page
```bash
> Improve this landing page for conversions

# Triggers:
# 1. page-cro (analyzes current design)
# 2. copywriting (suggests better copy)
# 3. ab-test-setup (recommends tests)
# 4. analytics-tracking (suggest GA4 events)
```

### Example 3: Plan Product Launch
```bash
> Create a GTM strategy for this new feature

# Triggers:
# 1. pricing-strategy (analyze monetization)
# 2. launch-strategy (plan phases)
# 3. sales-enablement (create pitch)
# 4. email-sequence (create announcement flow)
```

### Example 4: Email Campaign
```bash
> Create a 5-email welcome sequence

# Triggers:
# 1. product-marketing-context (messaging)
# 2. email-sequence (flow design)
# 3. copywriting (write each email)
# 4. ab-test-setup (suggest test variants)
```

## Skill Categories by Function

### 🎨 **Conversion**
- page-cro (any page conversions)
- signup-flow-cro (registration)
- onboarding-cro (post-signup)
- form-cro (lead forms)
- popup-cro (modals/overlays)
- paywall-upgrade-cro (upsells)

### 📝 **Content**
- copywriting (core copy)
- copy-editing (polish)
- cold-email (B2B)
- email-sequence (automation)
- social-content (social media)

### 🔍 **SEO & Data**
- seo-audit (technical)
- ai-seo (AI search)
- programmatic-seo (scale)
- site-architecture (URL structure)
- schema-markup (structured data)
- analytics-tracking (setup)

### 🎯 **Strategy**
- pricing-strategy (pricing/packaging)
- launch-strategy (go-to-market)
- marketing-ideas (brainstorm)
- customer-research (insights)
- competitor-alternatives (positioning)

### 💰 **Sales & Ops**
- revops (lead lifecycle)
- sales-enablement (collateral)
- paid-ads (campaigns)
- referral-program (growth)
- churn-prevention (retention)

## Configuration

**Product Marketing Context File** location:

- **Recommended**: `.agents/product-marketing-context.md`
- **Fallback**: `.claude/product-marketing-context.md`

Each skill checks this file first for:
- Product name/tagline
- Target audience
- Value proposition
- Brand voice
- Competitive positioning

## Related Skills & Integration

**Ecosystem:**
- `claude-seo` - Deep SEO analysis integration
- `claude-blog` - Blog writing with SEO optimization
- `deep-research-skill` - Customer research backing

**Workflow Example:** SEO → Content → CRO → Analytics

## Prompting Tips

### ✅ Good Prompts
```
"Optimize this landing page for SaaS founders. Currently at 2% conversion rate."
→ Skills contextualize with product-marketing-context

"Create a 5-email nurture sequence for enterprise prospects"
→ email-sequence + messaging + copywriting

"Compare us to [competitor] for comparison page"
→ competitor-alternatives skill
```

### ❌ Vague Prompts
```
"Write marketing copy" 
→ Need specifics: type of page, audience, goal

"Make this convert better"
→ Better: "What CRO changes would improve [specific page]?"
```

## Troubleshooting

**Skills not triggering?**
→ Ensure `product-marketing-context.md` exists
→ Check file location: `.agents/` or `.claude/`

**Skills referencing old context?**
→ Update `product-marketing-context.md`
→ Restart Claude Code

**Conflicting advice across skills?**
→ Normal—compare perspectives
→ Product-marketing-context provides consistency

## Contributing

PRs welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Adding new skills
- Improving existing skills
- Sharing best practices

Built with Claude Code by [@corey.co](https://corey.co)  
MIT License — Use freely  
Learn more: [Coding for Marketers](https://codingformarketers.com)

## Resources

- [All 24+ skills](https://github.com/coreyhaines31/marketingskills)
- [Skill breakdown](https://github.com/coreyhaines31/marketingskills#available-skills)
- [Setup guide](https://github.com/coreyhaines31/marketingskills#installation)
