---
name: slop
description: Lint changed prose (.md) for LLM slop — banned phrases, em/en-dashes, stock patterns. Deep Work Protocol rule 7 (ADR-0005). Blocks nothing; reports hits to fix.
---

# /slop — prose slop gate

Run the slop linter over prose that changed in this repo, and report hits so they can
be regenerated with the constraint named. This is the gate half of the deep-work
protocol's anti-homogenization rule (Antislop banlist, ADR-0005): slop is a defect to
fix, not a style suggestion.

Steps:

1. Find changed markdown (staged + unstaged + untracked):

```bash
{ git diff --name-only --diff-filter=d; git diff --cached --name-only --diff-filter=d; git ls-files --others --exclude-standard; } 2>/dev/null | grep -E '\.md$' | sort -u
```

2. Run the linter on each; it exits 1 and prints `file:line: [kind] 'fragment'` per hit:

```bash
OS="${CLAUDE_OS_DIR:-$HOME/claude-setup}"
files=$({ git diff --name-only --diff-filter=d; git diff --cached --name-only --diff-filter=d; git ls-files --others --exclude-standard; } 2>/dev/null | grep -E '\.md$' | sort -u)
[ -z "$files" ] && echo "no changed .md files" || python "$OS/tools/slop_lint.py" $files
```

3. For each hit, rewrite the flagged span: name the banned pattern, replace with plain
   language (comma/colon/period for dashes; drop stock phrases; break rule-of-three
   symmetry). Re-run until clean. Do not simply delete flagged lines — rewrite them.

Report: the hit count before and after, and which spans were rewritten.
