#!/usr/bin/env bash
set -euo pipefail

INPUT_DIR="${1:-$PWD}"
HOME_DIR="/home/shovalbe"
cd "$INPUT_DIR" 2>/dev/null || cd "$HOME_DIR"
START_DIR="$(pwd -P)"

section() {
  printf '\n## %s\n' "$1"
}

redact() {
  sed -E \
    -e 's/(ANTHROPIC_AUTH_TOKEN|JIRA_API_TOKEN|API[_-]?KEY|TOKEN|PASSWORD|SECRET)=([^[:space:]]+)/\1=<redacted>/Ig' \
    -e 's/("ANTHROPIC_AUTH_TOKEN"[[:space:]]*:[[:space:]]*)"[^"]+"/\1"<redacted>"/Ig'
}

mtime_list() {
  local root="$1"
  local pattern="$2"
  local limit="${3:-8}"
  if [[ -d "$root" ]]; then
    find "$root" \
      \( -path '*/.git' -o -path '*/node_modules' -o -path '*/.venv' -o -path '*/venv' \
         -o -path '*/__pycache__' -o -path '*/.cache' -o -path '*/.bun' -o -path '*/.npm' \
         -o -path '*/.local/share' -o -path '*/.claude/cache' -o -path '*/.claude/plugins/cache' \
         -o -path '*/.codex/plugins/cache' -o -path '*/.codex/sessions' -o -path '*/.claude/sessions' \
         -o -path '*/.claude/worktrees' \) -prune \
      -o -type f -iname "$pattern" -printf '%T@ %TY-%Tm-%Td %TH:%TM %p\n' 2>/dev/null \
      | sort -nr \
      | head -n "$limit" \
      | cut -d' ' -f2- \
      || true
  fi
}

top_tree() {
  local root="$1"
  if [[ -d "$root" ]]; then
    find "$root" -maxdepth 1 -mindepth 1 \
      \( -name '.git' -o -name 'node_modules' -o -name '.venv' -o -name 'venv' -o -name '__pycache__' \) -prune \
      -o -printf '%y %p\n' 2>/dev/null \
      | sort \
      | head -n 80 \
      || true
  fi
}

large_loose_files() {
  local root="$1"
  if [[ -d "$root" ]]; then
    find "$root" -maxdepth 1 -type f -size +5M -printf '%s %p\n' 2>/dev/null \
      | sort -nr \
      | head -n 20 \
      | awk '{size=$1; $1=""; printf "%.1f MB%s\n", size/1048576, $0}' \
      || true
  fi
}

count_pattern() {
  local root="$1"
  local pattern="$2"
  if [[ -d "$root" ]]; then
    find "$root" \
      \( -path '*/.git' -o -path '*/node_modules' -o -path '*/.venv' -o -path '*/venv' \
         -o -path '*/__pycache__' -o -path '*/.cache' -o -path '*/.bun' -o -path '*/.npm' \
         -o -path '*/.local/share' -o -path '*/.claude/cache' -o -path '*/.claude/plugins/cache' \
         -o -path '*/.codex/plugins/cache' -o -path '*/.codex/sessions' -o -path '*/.claude/sessions' \
         -o -path '*/.claude/worktrees' \) -prune \
      -o -type f -iname "$pattern" -print 2>/dev/null \
      | wc -l \
      | tr -d ' ' \
      || true
  fi
}

infer_scan_root() {
  local start="$1"
  case "$start" in
    "$HOME_DIR/projects/"*)
      local rest="${start#"$HOME_DIR/projects/"}"
      local project="${rest%%/*}"
      printf '%s/projects/%s\n' "$HOME_DIR" "$project"
      return
      ;;
    "$HOME_DIR/work/"*)
      local rest="${start#"$HOME_DIR/work/"}"
      local project="${rest%%/*}"
      printf '%s/work/%s\n' "$HOME_DIR" "$project"
      return
      ;;
  esac
  printf '%s\n' "$start"
}

open_item_scan() {
  python3 - "$@" <<'PY'
import re
import sys
from collections import Counter
from pathlib import Path

roots = []
for arg in sys.argv[1:]:
    path = Path(arg).expanduser()
    if path.exists() and path not in roots:
        roots.append(path)

skip_parts = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".cache",
    ".bun",
    ".npm",
    "sessions",
    "plugins",
    "cache",
    "dist",
    "build",
    "coverage",
}

unchecked_re = re.compile(r"^\s*[-*]\s+\[\s\]\s+(.+)")
marker_re = re.compile(r"\b(TODO|FIXME|BLOCKED)\b[:\s-]*(.*)", re.IGNORECASE)
status_re = re.compile(
    r"\b(remaining|not started|partial|acceptance criteria|acceptance)\b",
    re.IGNORECASE,
)


def is_planish(path: Path) -> bool:
    if path.suffix.lower() not in {".md", ".txt"}:
        return False
    lowered = str(path).lower()
    name = path.name.lower()
    if "/.claude/plans/" in lowered:
        return True
    if "/.codex/" in lowered and (
        name in {"spec.md", "plan.md", "todo.md"}
        or "spec" in name
        or "plan" in name
        or "todo" in name
    ):
        return True
    if "/docs/" in lowered:
        if any(part in path.parts for part in ("specs", "jira-tasks", "pipelines", "core")):
            return True
        return any(
            token in name
            for token in (
                "plan",
                "todo",
                "backlog",
                "queue",
                "status",
                "runbook",
                "readme",
                "prd",
                "spec",
            )
        )
    return any(
        token in name
        for token in (
            "plan",
            "todo",
            "backlog",
            "queue",
            "status",
            "runbook",
            "prd",
            "spec",
            "gaps",
            "health",
        )
    )


def iter_files(root: Path):
    if root.is_file():
        if is_planish(root):
            yield root
        return
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip_parts for part in path.parts):
            continue
        if is_planish(path):
            yield path


items = []
counts = Counter()
seen_files = set()
for root in roots:
    for path in iter_files(root):
        resolved = path.resolve()
        if resolved in seen_files:
            continue
        seen_files.add(resolved)
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for lineno, line in enumerate(lines, start=1):
            kind = None
            text = None
            match = unchecked_re.search(line)
            if match:
                kind = "unchecked"
                text = match.group(1)
            else:
                match = marker_re.search(line)
                if match:
                    kind = match.group(1).upper()
                    text = match.group(2) or line.strip()
                elif status_re.search(line):
                    kind = "status"
                    text = line.strip()
            if not kind or not text:
                continue
            clean = " ".join(text.split())
            if len(clean) > 180:
                clean = clean[:177] + "..."
            items.append((str(path), lineno, kind, clean))
            counts[str(path)] += 1

print("candidate_files:")
if counts:
    for path, count in counts.most_common(12):
        print(f"  {count:>3} {path}")
else:
    print("  none")

print("candidates:")
for path, lineno, kind, text in items[:60]:
    print(f"  {path}:{lineno} [{kind}] {text}")
if len(items) > 60:
    print(f"  ... truncated: showing 60 of {len(items)} candidates")
PY
}

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
scan_root="$(infer_scan_root "$START_DIR")"
if [[ -n "$repo_root" ]]; then
  cd "$repo_root"
  project_root="$scan_root"
else
  project_root="$scan_root"
fi

section "identity"
printf 'cwd: %s\n' "$START_DIR"
printf 'project_root: %s\n' "$project_root"
if [[ -n "$repo_root" ]]; then
  printf 'git_root: %s\n' "$repo_root"
fi
printf 'date_utc: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

section "rules"
for path in \
  "$HOME_DIR/AGENTS.md" \
  "$HOME_DIR/.codex/RTK.md" \
  "$project_root/AGENTS.md" \
  "$project_root/.codex/hive.yaml" \
  "$project_root/.claude/hive.yaml" \
  "$project_root/README.md" \
  "$project_root/CLAUDE.md"; do
  if [[ -f "$path" ]]; then
    printf '%s\n' "$path"
  fi
done | awk '!seen[$0]++'

section "global_docs"
for path in \
  "$HOME_DIR/docs/README.md" \
  "$HOME_DIR/docs/core/README.md" \
  "$HOME_DIR/docs/specs/2026-06-25-local-intent-control-plane.md" \
  "$HOME_DIR/docs/specs/2026-06-28-work-general-mojuco-artifixer-foundry-plan.md" \
  "$HOME_DIR/docs/2026-06-28-work-general-setup_4614.md" \
  "$HOME_DIR/docs/SOTA-TESTING-CRITERIA-2026.md" \
  "$HOME_DIR/docs/testing_practices.txt" \
  "$HOME_DIR/docs/pipelines/README.md" \
  "$HOME_DIR/docs/research/README.md"; do
  if [[ -f "$path" ]]; then
    printf '%s\n' "$path"
  fi
done

section "skills"
for root in "$HOME_DIR/.agents/skills" "$HOME_DIR/.codex/skills"; do
  if [[ -d "$root" ]]; then
    count="$(find "$root" -maxdepth 2 -name SKILL.md -type f 2>/dev/null | wc -l | tr -d ' ')"
    printf '%s: %s SKILL.md files\n' "$root" "$count"
  fi
done

section "git"
if [[ -n "$repo_root" ]]; then
  printf 'repo: %s\n' "$repo_root"
  printf 'branch: %s\n' "$(git branch --show-current 2>/dev/null || true)"
  printf 'upstream: %s\n' "$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
  printf 'remote:\n'
  git remote -v 2>/dev/null | sed 's/^/  /' | redact || true
  printf 'status:\n'
  git status --short 2>/dev/null | head -n 40 | sed 's/^/  /' || true
  printf 'status_counts:\n'
  printf '  changed: %s\n' "$(git status --short 2>/dev/null | wc -l | tr -d ' ')"
  printf '  untracked: %s\n' "$(git status --short 2>/dev/null | awk '$1 ~ /^\?\?/ {c++} END {print c+0}')"
  if [[ "$repo_root" == "$HOME_DIR" ]]; then
    printf 'warning: HOME_AS_REPO\n'
  fi
  if [[ -z "$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)" ]]; then
    printf 'warning: NO_UPSTREAM\n'
  fi
  printf 'local_commits:\n'
  git log --oneline --decorate -8 2>/dev/null | sed 's/^/  /' || true
  if git rev-parse --verify '@{u}' >/dev/null 2>&1; then
    printf 'ahead_behind: '
    git rev-list --left-right --count HEAD...@{u} 2>/dev/null || true
    printf 'upstream_commits:\n'
    git log --oneline --decorate -5 '@{u}' 2>/dev/null | sed 's/^/  /' || true
  fi
else
  printf 'not a git repo\n'
fi

section "tree_hygiene"
printf 'top_level:\n'
top_tree "$project_root" | sed 's/^/  /'
printf 'large_loose_files:\n'
large_loose_files "$project_root" | sed 's/^/  /'
printf 'artifact_dirs:\n'
find "$project_root" -maxdepth 3 -type d \
  \( -iname 'artifacts' -o -iname 'outputs' -o -iname 'dist' -o -iname 'build' -o -iname 'coverage' \
     -o -iname 'reports' -o -iname 'logs' -o -iname 'tmp' -o -iname 'scratch' -o -iname 'archive' \) \
  -print 2>/dev/null | head -n 30 | sed 's/^/  /' || true

section "file_counts"
for pattern in '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' '*.md' '*.png' '*.xlsx' '*.csv' '*.parquet' '*.json' '*.html'; do
  printf '%s: %s\n' "$pattern" "$(count_pattern "$project_root" "$pattern")"
done

section "jira"
jira_cache="$HOME_DIR/.claude/jira/reminders.json"
if [[ -f "$jira_cache" ]]; then
  python3 - "$jira_cache" <<'PY'
import json, sys, datetime
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text())
updated = data.get("updated_at") or data.get("refreshed_at")
print(f"cache: {path}")
if updated:
    print(f"updated_at: {updated}")
print(f"open_total: {data.get('open_total')}")
pointer = data.get("time_pointer") or data.get("pointer")
if pointer:
    print(f"time_pointer: {pointer}")
for item in (data.get("flagged") or [])[:8]:
    key = item.get("key")
    status = item.get("status") or item.get("status_name")
    summary = item.get("summary")
    reason = item.get("reason") or item.get("why") or item.get("age")
    print(f"- {key} [{status}] {summary} -- {reason}")
PY
else
  printf 'cache missing: %s\n' "$jira_cache"
fi

section "docs_and_plans"
for dir in \
  "$project_root/docs" \
  "$project_root/.codex" \
  "$project_root/.claude/plans" \
  "$HOME_DIR/.claude/plans" \
  "$HOME_DIR/docs"; do
  [[ -d "$dir" ]] && printf '### %s\n' "$dir" && mtime_list "$dir" '*.md' 8
done

section "open_plan_spec_items"
if [[ "$project_root" != "$HOME_DIR" ]]; then
  open_item_scan \
    "$project_root" \
    "$project_root/docs" \
    "$project_root/.codex" \
    "$project_root/.claude/plans" \
    "$HOME_DIR/.claude/plans" \
    "$HOME_DIR/docs"
else
  open_item_scan \
    "$project_root/docs" \
    "$project_root/.codex" \
    "$project_root/.claude/plans" \
    "$HOME_DIR/.claude/plans" \
    "$HOME_DIR/docs"
fi
printf 'note: candidates require reconciliation against code, tests, runtime state, or newer superseding specs before being marked closed.\n'

section "recent_artifacts"
for ext in png xlsx csv parquet json html txt md; do
  printf '### .%s\n' "$ext"
  mtime_list "$project_root" "*.${ext}" 10
done

section "ai_coding_risk_scan"
printf 'large_source_files:\n'
find "$project_root" \
  \( -path '*/.git' -o -path '*/node_modules' -o -path '*/.venv' -o -path '*/venv' \
     -o -path '*/__pycache__' -o -path '*/.cache' -o -path '*/.bun' -o -path '*/.npm' \
     -o -path '*/.local/share' -o -path '*/.antigravity-server' -o -path '*/.vscode-server' \
     -o -path '*/.claude-resource-archive' -o -path '*/.codex/plugins/cache' \
     -o -path '*/.claude/plugins/cache' -o -path '*/dist' -o -path '*/build' \
     -o -path '*/.next' -o -path '*/coverage' \) -prune \
  -o -type f \( -iname '*.py' -o -iname '*.ts' -o -iname '*.tsx' -o -iname '*.js' -o -iname '*.jsx' \) \
  -size +80k -printf '%s %p\n' 2>/dev/null \
  | sort -nr \
  | head -n 20 \
  | awk '{size=$1; $1=""; printf "  %.1f KB%s\n", size/1024, $0}' \
  || true
printf 'duplicate_builder_names:\n'
find "$project_root" \
  \( -path '*/.git' -o -path '*/node_modules' -o -path '*/.venv' -o -path '*/venv' \
     -o -path '*/__pycache__' -o -path '*/.cache' -o -path '*/.bun' -o -path '*/.npm' \
     -o -path '*/.local/share' -o -path '*/.antigravity-server' -o -path '*/.vscode-server' \
     -o -path '*/.claude-resource-archive' -o -path '*/.codex/plugins/cache' \
     -o -path '*/.claude/plugins/cache' -o -path '*/.next' \) -prune \
  -o -type f \( -iname '*build*' -o -iname '*builder*' -o -iname '*generate*' -o -iname '*generator*' \) \
  -printf '%f %p\n' 2>/dev/null \
  | sort \
  | head -n 40 \
  | sed 's/^/  /' \
  || true
printf 'mock_test_mentions:\n'
grep -RIn --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=venv --exclude-dir=__pycache__ \
  -E '\b(mock|mocker|monkeypatch|jest\.mock|vi\.mock|sinon)\b' "$project_root"/tests "$project_root"/test 2>/dev/null \
  | head -n 30 \
  | sed 's/^/  /' \
  || true
