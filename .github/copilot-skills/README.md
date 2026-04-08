# Copilot Skills Mirror

This folder is a workspace-local mirror of your global skills from:

`%APPDATA%\Code\User\prompts`

It exists so **any GitHub Copilot model** can use the same skill set consistently in this repo.

This includes GPT/ChatGPT-family models when selected in GitHub Copilot.

If you are using standalone ChatGPT (outside GitHub Copilot), this local mirror is not read automatically.

## Refresh Skills

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .github/scripts/sync-copilot-skills.ps1
```

## Use in Chat

Use the router prompt from `.github/prompts/use-all-skills.prompt.md` and pass your task.

This works the same way when your active Copilot model is GPT-based.

Automatic selection layer:

```powershell
powershell -ExecutionPolicy Bypass -File .github/scripts/select-copilot-skills.ps1 -PromptText "<your full task prompt>"
```

The selector returns JSON with `selectedSkills` and match details (`score`, `hits`).

Example:

```text
Use All Skills Router
Task: Build a publication-ready research report workflow with security checks.
Domains: research, documents, security
```

## How Routing Works

1. Copilot reads `.github/copilot-skills/_manifest.md`.
2. Copilot runs `.github/scripts/select-copilot-skills.ps1` with the user prompt.
3. It uses `selectedSkills` as candidates.
4. It reads each selected `SKILL.md`.
5. It executes using those skill workflows/checklists.

## Notes

- This mirror is generated. Do not manually edit copied `SKILL.md` files.
- Edit source skills in `%APPDATA%\Code\User\prompts`, then resync.
