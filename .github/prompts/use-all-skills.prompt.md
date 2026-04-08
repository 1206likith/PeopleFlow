# Use All Skills Router

Use this prompt to force reliable skill routing across any GitHub Copilot model.

This includes GPT/ChatGPT-family models selected inside Copilot.

If used outside Copilot (standalone ChatGPT), local skill files are not auto-discovered.

## Input

- Task: {{task}}
- Preferred domains (optional): {{domains}}

## Instructions

1. Open `.github/copilot-skills/_manifest.md`.
2. Run the skill selector:
   `powershell -ExecutionPolicy Bypass -File .github/scripts/select-copilot-skills.ps1 -PromptText "{{task}} {{domains}}"`
3. Use `selectedSkills` from the JSON output.
4. Read each selected `SKILL.md` file in `.github/copilot-skills/<skill>/SKILL.md`.
5. Execute the task following the selected skills' workflows and constraints.
6. Return:
   - Selected skills
   - Selector output summary (score + keyword hits)
   - Why each was selected
   - Implementation plan
   - Final output

If the manifest is missing, instruct the user to run:

`powershell -ExecutionPolicy Bypass -File .github/scripts/sync-copilot-skills.ps1`
