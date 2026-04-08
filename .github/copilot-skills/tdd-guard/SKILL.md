---
name: tdd-guard
version: 2.0.0
description: Automated Test-Driven Development (TDD) enforcement for Claude Code. Blocks implementations without failing tests, prevents over-engineering, integrates linting, and validates code quality against custom TDD rules.
author: Nizar Osmani
license: MIT
keywords:
  - tdd
  - test-driven-development
  - testing
  - quality
  - enforcement
  - validation
compatibility:
  - Claude Code
  - Claude Code (all platforms: Windows, macOS, Linux)
allowed-tools:
  - node
  - python
  - shell
  - file-system
  - git
---

# TDD Guard - Test-Driven Development Enforcement

**Automated TDD enforcement system** that:
- **Blocks implementation** without failing tests (RED → GREEN → REFACTOR)
- **Prevents over-engineering** by limiting code beyond test requirements
- **Enforces linting** using your project's lint rules
- **Validates test quality** with customizable rubrics
- **Supports 6+ test frameworks** (Vitest, Jest, pytest, PHPUnit, Go test, RSpec, etc.)
- **Toggles on/off** mid-session
- **Custom rules** for your TDD style

## Use When

The user wants to:
- Enforce strict TDD workflow in Claude Code
- Prevent "vibe coding" and over-engineering
- Ensure all code changes have corresponding tests
- Run automated test validation before implementation
- Enforce minimal implementation matching test requirements
- Apply code quality rules (formatting, linting) automatically
- Create a reliable AI-assisted development workflow
- Debug failing tests using Claude

## Core Concept: RED → GREEN → REFACTOR

**TDD Guard enforces the cycle:**

```
1. RED 🔴
   - Write failing test first
   - Verify it actually fails

2. GREEN 🟢
   - Write minimal code to pass test
   - TDD Guard checks: only implement what tests require

3. REFACTOR 🟠
   - Improve code quality
   - Pass linting rules
   - Maintain all tests passing
```

**TDD Guard blocks**: Implementation without failing test, code beyond test requirements, skipped refactoring

## Installation

```bash
# Claude Code (recommended)
/plugin marketplace add nizos/tdd-guard
/plugin install tdd-guard@tdd-guard
/tdd-guard:setup

# Or manual
git clone https://github.com/nizos/tdd-guard.git
cd tdd-guard
npm install
npm run build
npm run install-hook
```

## Setup

Run setup command:
```bash
/tdd-guard:setup
```

This:
1. Detects your test framework automatically
2. Configures test reporter for your project
3. Validates setup with test run
4. Creates `.tdd-guard.json` configuration

Supported frameworks:
- **JavaScript/TypeScript**: Vitest, Jest, Storybook
- **Python**: pytest, unittest
- **PHP**: PHPUnit
- **Go**: go test, testify
- **Rust**: cargo test, criterion
- **Ruby**: RSpec, minitest

## Configuration

File: `.tdd-guard.json`

```json
{
  "enabled": true,
  "framework": "vitest",
  "testCommand": "npm test",
  "testPattern": "**/*.test.{ts,tsx,js}",
  "validationModel": "claude-3-5-sonnet",
  "enforceLinting": true,
  "linter": "eslint",
  "lintCommand": "npm run lint",
  "allowedToolsOnly": false,
  "customRules": [
    "No implementation without failing test",
    "Minimal implementation only",
    "Must pass linting before commit"
  ],
  "ignorePatterns": [
    "node_modules/**",
    "dist/**",
    "coverage/**"
  ]
}
```

## Key Features

### ✅ Test-First Enforcement
- Prevents implementation without failing test
- Blocks code that doesn't have corresponding test
- Requires tests to run and fail first

### ✅ Minimal Implementation
- Detects over-engineering
- Prevents code beyond what tests require
- Catches unnecessary features or optimizations

### ✅ Linting Integration
- Auto-enforces refactoring via linter rules
- Runs ESLint, Prettier, Black, etc.
- Reports linting violations with fixes

### ✅ Customizable Validation
- Define your TDD style via custom rules
- Model selection (fast vs capable)
- Ignore patterns for config/generated files

### ✅ Flexible Models
- **Fast**: claude-3-5-haiku (quick validation)
- **Capable**: claude-3-5-sonnet (thorough review)
- **Extended**: claude-3-opus (deep analysis)

Choose speed vs accuracy based on your needs.

## Workflow Example

### Scenario: Implementing User Authentication

```bash
# Step 1: Claude writes failing test
> Implement user authentication

Claude produces: src/auth.test.ts with failing test
TDD Guard: ✅ Detects failing test, GREEN status

# Step 2: Claude implements minimal code
Claude produces: src/auth.ts (minimal implementation)
TDD Guard: ✅ Tests pass, validates implementation is minimal

# Step 3: Claude refactors
Claude produces: Clean code with variables renamed, logic simplified
TDD Guard: ✅ Tests still pass, linting passes, REFACTOR complete
```

If Claude skips step 1 or over-engineers:
```
TDD Guard: ❌ BLOCKED - Must start with failing test
❌ BLOCKED - Implementation exceeds test requirements
```

## Commands

### `/tdd-guard:setup`
Initialize TDD Guard for your project (auto-detects framework)

### `/tdd-guard:enable`
Turn on TDD validation

### `/tdd-guard:disable`
Turn off validation (toggle within session)

### `/tdd-guard:status`
Show current status and configuration

### `/tdd-guard:validate`
Manually validate last implementation

### `/tdd-guard:fix-tests`
Help debug and fix failing tests

## Custom Instructions

Override defaults in `.tdd-guard.json`:

```json
{
  "customRules": [
    "All exported functions must have @see comments linking to tests",
    "Coverage must stay above 80%",
    "No console.log() in production code",
    "Async functions must have timeout handling"
  ],
  "enforceLinting": true,
  "strictMode": true
}
```

## Configuration Guides

- [Custom instructions](docs/custom-instructions.md) - Define your TDD rules
- [Lint integration](docs/linting.md) - Setup eslint/prettier/black
- [Strengthening enforcement](docs/enforcement.md) - Prevent by-passing
- [Ignore patterns](docs/ignore-patterns.md) - Exclude files
- [Validation model](docs/validation-model.md) - Choose model speed/capability
- [All settings](docs/configuration.md) - Complete reference

## Supported Languages & Frameworks

| Language | Frameworks | Status |
|----------|-----------|--------|
| **JavaScript/TypeScript** | Vitest, Jest, Storybook | ✅ Supported |
| **Python** | pytest, unittest | ✅ Supported |
| **PHP** | PHPUnit | ✅ Supported |
| **Go** | go test, testify | ✅ Supported |
| **Rust** | cargo test, criterion | ✅ Supported |
| **Ruby** | RSpec, minitest | ✅ Supported |

## Security

- Hooks run with your user permissions
- No external code execution
- Active security scanning and dependency audits
- See [Claude Code security docs](https://docs.anthropic.com/en/docs/claude-code/hooks#security-considerations)

## Roadmap

- [ ] Expand language support (Java, C#, Kotlin, Swift)
- [ ] Validate file modifications from MCPs and shell
- [ ] Suggest meaningful refactoring opportunities when tests green
- [ ] Multi-session concurrent support
- [ ] Metrics dashboard (tests/implementation ratio, coverage trends)

## Troubleshooting

**Tests not being detected?**
→ Run `npm test` manually to verify it works
→ Check test file naming matches pattern in `.tdd-guard.json`

**Linting errors but tests pass?**
→ Fix linting issues before refactor
→ Run `npm run lint --fix` to auto-fix

**Model taking too long?**
→ Switch to haiku: `"validationModel": "claude-3-5-haiku"`
→ Disable strict enforcement for non-critical files

**Setup failed?**
→ Check Node.js 22+ installed
→ Verify test framework works (`npm test`)
→ Check test output is readable

## Contributors

- Python/pytest: [@Durafen](https://github.com/Durafen)
- PHP/PHPUnit: [@wazum](https://github.com/wazum)
- Rust: [@104hp6u](https://github.com/104hp6u)
- Go: [@sQVe](https://github.com/sQVe), [@wizzomafizzo](https://github.com/wizzomafizzo)
- Storybook: [@akornmeier](https://github.com/akornmeier)
- Ruby/RSpec: [@Hiro-Chiba](https://github.com/Hiro-Chiba)

## Support

- **Issues**: [GitHub Issues](https://github.com/nizos/tdd-guard/issues)
- **Discussions**: [GitHub Discussions](https://github.com/nizos/tdd-guard/discussions)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)

## License

MIT License

---

**Made with ❤️ for developers who believe in test-driven development**

GitHub: https://github.com/nizos/tdd-guard  
npm: [@nizos/tdd-guard](https://www.npmjs.com/package/tdd-guard)
