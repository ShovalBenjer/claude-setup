---
enforce:
  cmd: "rg -l -e '[\\x{1F600}-\\x{1F64F}\\x{1F300}-\\x{1F5FF}\\x{1F680}-\\x{1F6FF}\\x{1F900}-\\x{1F9FF}]' docs/specs/ docs/prd/ --glob '*.md' && exit 1 || exit 0"
---
# No decorative emoji

Do not use decorative emoji in code, logs, documentation, or user-facing copy.
Preserve emoji only when they are input data or an explicit product requirement.
