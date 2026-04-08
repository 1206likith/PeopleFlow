---
name: owasp-security
version: 2.0.0
description: OWASP security best practices skill (2025-2026) for Claude Code providing top 10 web vulnerabilities, ASVS verification requirements, agentic AI security, secure code patterns, and language-specific security quirks for 20+ languages.
author: agamm
license: MIT
keywords:
  - security
  - owasp
  - vulnerability
  - secure-coding
  - application-security
  - asvs
compatibility:
  - Claude Code
  - Cursor
  - OpenCode
allowed-tools:
  - shell
  - file-system
  - python
  - node
---

# OWASP Security Skill for Claude Code

**OWASP 2025-2026 security best practices** for Claude Code providing:
- **OWASP Top 10:2025** vulnerabilities quick reference
- **ASVS 5.0.0** security verification requirements by level
- **Agentic AI Security (2026)** - ASI01-ASI10 risks for AI agent systems
- **Security code review checklists** for input handling, auth, access control
- **Secure code patterns** with unsafe/safe examples for all major languages
- **Language-specific security quirks** for 20+ languages

## Use When

The user wants to:
- Review code for security vulnerabilities
- Implement authentication or authorization securely
- Handle user input and external data safely
- Work with cryptography or password storage
- Design API endpoints securely
- Build AI agent systems with security considerations
- Check compliance with ASVS requirements
- Understand language-specific security risks
- Generate secure code patterns

## OWASP Standards Covered

### OWASP Top 10:2025 Vulnerabilities
1. **Broken Access Control** - Invalid authorization enforcement
2. **Cryptographic Failures** - Weak encryption, poor key management
3. **Injection** - SQL, command, LDAP injection attacks
4. **Insecure Design** - Missing security controls
5. **Security Misconfiguration** - Unpatched systems, defaults exposed
6. **Vulnerable & Outdated Components** - Known CVEs
7. **Authentication Failures** - Broken session management, weak credentials
8. **Server-Side Request Forgery (SSRF)** - Requesting unintended URLs
9. **Insecure Deserialization** - Untrusted objects execution
10. **Logging & Monitoring Failures** - Insufficient audit trails

### ASVS 5.0.0 Verification Levels

**Level 1 (Standard)** - Basic security for all web applications  
**Level 2 (Moderate)** - Most business applications  
**Level 3 (Advanced)** - High-value systems requiring maximum security

Covers:
- V1: Architecture, design, threat modeling
- V2: Authentication
- V3: Session management
- V4: Access control
- V5: Validation, sanitization, encoding
- V6: Stored cryptography
- V7: Error handling, logging
- V8: Data protection
- V9: Communications
- V10: Malicious code
- V11: Business logic
- V12: File uploads
- V13: API/web service security
- V14: Configuration
- V15: File system
- V16: Unmanaged code

### OWASP Agentic AI Security (2026)

**ASI01-ASI10** risks for AI agent systems:
- **ASI01**: Insecure output handling
- **ASI02**: Excessive agency
- **ASI03**: Insecure tool integration
- **ASI04**: Lack of monitoring and logging
- **ASI05**: Insecure code practices
- **ASI06**: Insufficient access control
- **ASI07**: Inadequate sandboxing
- **ASI08**: Insecure authentication
- **ASI09**: Improper error handling
- **ASI10**: Ineffective rate limiting

## Code Review Checklists

### Input Handling Checklist
- [ ] All input validated against whitelist/schema
- [ ] Length limits enforced
- [ ] Type checking performed
- [ ] No dynamic SQL construction
- [ ] Encoding applied for output context

### Authentication Checklist
- [ ] Passwords hashed with bcrypt/argon2 (not MD5/SHA1)
- [ ] MFA available and encouraged
- [ ] Session tokens randomly generated (not sequential)
- [ ] Password reset flow secure (time-limited tokens)
- [ ] Brute force protection implemented (rate limiting)

### Access Control Checklist
- [ ] Every action checked for user permissions
- [ ] Authorization logic centralized (not scattered)
- [ ] Default deny policy implemented
- [ ] Privilege escalation impossible
- [ ] No client-side-only authorization

### Data Protection Checklist
- [ ] Sensitive data encrypted at rest (AES-256+)
- [ ] HTTPS only (no HTTP fallback)
- [ ] TLS 1.2+ with strong ciphers
- [ ] API keys never in URLs/logs
- [ ] PII minimized and retention limited

### Error Handling Checklist
- [ ] Generic error messages to users
- [ ] Detailed errors logged (never exposed)
- [ ] Stack traces hidden from production
- [ ] Exception handling doesn't mask security issues

## Language-Specific Security Quirks

### JavaScript/TypeScript
- **Risk**: prototype pollution, NoSQL injection, unsafe template literals
- **Safe**: `Object.freeze()`, parameter validation, template escaping

### Python
- **Risk**: pickle deserialization, SQL injection via string formatting
- **Safe**: `json` over `pickle`, parameterized queries

### PHP
- **Risk**: register_globals, SQL injection, weak type juggling
- **Safe**: `input validation`, prepared statements, strict comparison (`===`)

### Java
- **Risk**: XXE in XML parsing, serialization gadgets
- **Safe**: Disable DTD parsing, use safe serialization libs

### C/C++
- **Risk**: Buffer overflow, use-after-free, format string
- **Safe**: bounds checking, smart pointers, format security flags

### Go
- **Risk**: crypto/rand not used, unhardened defaults
- **Safe**: `crypto/rand`, explicit TLS config

### Rust
- **Risk**: unsafe blocks bypassing memory safety
- **Safe**: minimize unsafe, use safety audits

*(20+ languages covered)*

## Installation

```bash
# One-liner
curl -sL https://raw.githubusercontent.com/agamm/claude-code-owasp/main/.claude/skills/owasp-security/SKILL.md -o \
  ~/.claude/skills/owasp-security/SKILL.md --create-dirs

# Or clone full repo
git clone https://github.com/agamm/claude-code-owasp.git
cp -r claude-code-owasp/.claude/skills/owasp-security ~/.claude/skills/
```

## Example Prompts

```
"Review this code for security issues"
→ Checks for OWASP Top 10, language-specific risks

"Is this authentication implementation secure?"
→ Runs auth checklist, flags weak patterns

"What are the security risks in this Python code?"
→ Language-specific quirks + OWASP context

"Help me implement secure session management"
→ ASVS V3 requirements + code patterns

"Check this AI agent for OWASP agentic risks"
→ ASI01-ASI10 analysis for agent safety
```

## Secure Code Patterns

### ❌ Unsafe: SQL Injection
```python
query = f"SELECT * FROM users WHERE id = {user_id}"
db.execute(query)  # VULNERABLE
```

### ✅ Safe: Parameterized Query
```python
query = "SELECT * FROM users WHERE id = %s"
db.execute(query, (user_id,))  # SAFE
```

### ❌ Unsafe: MD5 Password Hash
```python
import hashlib
password_hash = hashlib.md5(password.encode()).hexdigest()  # WEAK
```

### ✅ Safe: Bcrypt Password Hash
```python
import bcrypt
password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(12))  # STRONG
```

### ❌ Unsafe: Hardcoded Secrets
```javascript
const API_KEY = "sk-1234567890abcdef";  // EXPOSED
```

### ✅ Safe: Environment Variables
```javascript
const API_KEY = process.env.API_KEY;  // USE .env
```

## Configuration

Skills auto-triggers when Claude detects:
- Keywords: "security", "vulnerability", "authentication", "encryption"
- Context: code review, auth implementation, API design
- Agents: security-auditor subagent

## Related Skills

- `deep-research-skill` - Security research and advisories
- `claude-code-owasp` - Repository with full documentation

## Audits & Frameworks

- **OWASP Testing Guide** - Comprehensive testing methodology
- **OWASP Top 10 API** - REST API-specific risks
- **OWASP Secure Coding Practices** - Development best practices
- **CWE** (Common Weakness Enumeration) - Root causes

## Compliance

Works with:
- **PCI DSS** - Payment card security
- **HIPAA** - Healthcare data security
- **SOC 2** - Service organization controls
- **GDPR** - Data protection requirements
- **ISO 27001** - Information security management

## Resources

- [OWASP Top 10:2025](https://owasp.org/Top10/)
- [ASVS 5.0](https://owasp.org/www-project-application-security-verification-standard/)
- [Agentic AI Security 2026](https://genai.owasp.org/)
- [Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [Repository](https://github.com/agamm/claude-code-owasp)

## Keywords for Auto-Triggering

Mention any to auto-enable this skill:
- security, vulnerability, attack, exploit
- authentication, authorization, access control
- encryption, cryptography, hashing
- OWASP, ASVS, compliance, audit
- SQL injection, XSS, CSRF, XXE
- API security, secure coding

License: MIT  
Built by [@agamm](https://github.com/agamm)
