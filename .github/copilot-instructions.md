# Copilot Universal Skill Loading

When a user asks for work that matches a domain skill, you must use the local skill mirror in `.github/copilot-skills/` so behavior is consistent across model choices.

## Model compatibility

This applies to all models available inside GitHub Copilot chat, including GPT/ChatGPT-family models.

If the chat is not running inside GitHub Copilot (for example, standalone ChatGPT web/app), local skill files are not auto-loaded.

## Required workflow

1. Read `.github/copilot-skills/_manifest.md`.
2. Auto-select skills from prompt text using:
   `powershell -ExecutionPolicy Bypass -File .github/scripts/select-copilot-skills.ps1 -PromptText "<user prompt>"`
3. Use returned `selectedSkills` as primary candidates.
4. Read each selected `SKILL.md` before implementation.
5. Apply skill constraints and checklists while solving the task.
6. If two skills conflict, prioritize:
   - Security and correctness
   - Project constraints
   - User intent

## Skill routing hints

- Documents: `pdf-skill`, `docx-skill`, `xlsx-skill`, `pptx-skill`
- Design/UI: `frontend-design-skill`, `canvas-design-skill`, `web-artifacts-skill`
- Research: `deep-research-skill`, `deep-research-enterprise-skill`, `notebooklm-skill`
- Agent workflow: `context-engineering-skill`, `context-engineering-kit`, `task-master-skill`, `planning-with-files-skill`, `superpowers-skill`, `skill-creator-skill`
- Engineering quality: `tdd-guard`, `owasp-security`
- Scientific: `claude-scientific-skills`
- Marketing/content: `marketing-skills`, `claude-seo`, `humanizer`
- Memory: `claude-mem`

## Missing mirror behavior

If `.github/copilot-skills/_manifest.md` is missing or stale, ask to run:

`powershell -ExecutionPolicy Bypass -File .github/scripts/sync-copilot-skills.ps1`

If `.github/copilot-skills/skill-routing-map.json` is missing, fall back to manual skill selection using the routing hints above.
