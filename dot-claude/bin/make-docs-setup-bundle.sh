#!/usr/bin/env bash
# make-docs-setup-bundle.sh
# Package a sharable/backup bundle of: ~/docs, all project docs subdirs,
# the Claude setup (config only), the Codex setup (config only), and their skill sync.
# EXCLUDES: secrets/keys/.env/auth, caches, sessions, node_modules, .git, model/video
# artifacts, sqlite stores, worktree + build-bundle doc copies.
# Staging happens in /tmp; only the final .zip lands in $HOME. Production data untouched.
set -uo pipefail
export NO_COLOR=1 GIT_PAGER=cat PAGER=cat BAT_STYLE=plain
cd "$HOME"

TS="$(date +%Y%m%d-%H%M%S)"
STAGE="$(mktemp -d /tmp/sb-bundle.XXXXXX)"
NAME="shovalbe-docs-setup-bundle-$TS"
ROOT="$STAGE/$NAME"
ZIP="$HOME/$NAME.zip"
mkdir -p "$ROOT"

# ---------- 1. exclusion rules (apply to every source) ----------
EXC="$STAGE/excludes.txt"
cat >"$EXC" <<'EOF'
.git/
node_modules/
.venv/
venv/
__pycache__/
site-packages/
.mypy_cache/
.pytest_cache/
.ruff_cache/
.next/
dist/
build/
.remotion/
bundle/
worktrees/
public/docs/
.env
.env.*
*.env
auth.json
secrets/
azure-snapshots/
*appsettings*.json
*.PublishSettings
*.publishsettings
AUTH_TECHNICAL_REFERENCE.md
archive/
archived/
*credential*
*Credential*
*CREDENTIAL*
*corp-ai-scan*
retention_module_test_report.md
*.key
*.pem
*.pfx
*.p12
id_rsa*
id_ed25519*
installation_id
daemon-auth-status.json
daemon-auth-cooldown
*.sqlite
*.sqlite-wal
*.sqlite-shm
raw_memories.md
phase2_workspace_diff.md
*.log
EOF

# ---------- 2. fixed allowlist (setup/config, not data) ----------
SRC=(
  docs
  .claude/CLAUDE.md .claude/settings.json .claude/settings.local.json
  .claude/rules .claude/skills .claude/commands .claude/hooks .claude/agents
  .claude/bin .claude/docs .claude/plans .claude/corpus .claude/config
  .claude/jobs .claude/teams .claude/projects/-home-shovalbe/memory
  .codex/AGENTS.md .codex/RTK.md .codex/config.toml .codex/hooks.json .codex/hooks
  .codex/skills .codex/rules .codex/agents .codex/bin
  .codex/automations/prompts .codex/automations/README.md
  .codex/automations/run-codex-automation.sh
  .codex/migrated-from-claude .codex/memories .codex/reports .codex/siu-qa
  .codex/version.json .codex/settings.migrated.from-claude.json
)
EXIST=()
for p in "${SRC[@]}"; do [ -e "$p" ] && EXIST+=("$p"); done

# ---------- 3. every real docs/documentation subdir under projects ----------
mapfile -t PROJ < <(
  find projects \
    \( -name node_modules -o -name .git -o -name .venv -o -name venv \
       -o -name __pycache__ -o -name dist -o -name build -o -name .next \
       -o -name .remotion -o -name out -o -name bundle -o -name site-packages \
       -o -name .pytest_cache -o -name .mypy_cache -o -name worktrees \
       -o -name .build -o -name .kilocode -o -name .archive \) -prune \
    -o -type d \( -iname docs -o -iname documentation \) -print 2>/dev/null \
  | grep -v '/public/docs' | sort -u
)

# ---------- 4. stage (dereference skill symlinks into real content) ----------
echo "[stage] rsync $(( ${#EXIST[@]} + ${#PROJ[@]} )) sources -> $ROOT"
rsync -aR --copy-links --exclude-from="$EXC" "${EXIST[@]}" "${PROJ[@]}" "$ROOT/" 2>"$STAGE/rsync.err"
rc=$?
if [ "$rc" -ne 0 ] && [ "$rc" -ne 23 ] && [ "$rc" -ne 24 ]; then
  echo "[fatal] rsync rc=$rc"; sed -n '1,20p' "$STAGE/rsync.err"; exit "$rc"
fi
[ -s "$STAGE/rsync.err" ] && echo "[stage] rsync notes: $(wc -l <"$STAGE/rsync.err") line(s) (symlink/vanished, non-fatal)"

STAGE_SZ="$(du -sm "$ROOT" | cut -f1)"
echo "[stage] staged size: ${STAGE_SZ}M"
if [ "$STAGE_SZ" -gt 250 ]; then
  echo "[guard] staged >250M, a dereferenced symlink likely pulled in bulk data. Aborting for review."
  du -sh "$ROOT"/* 2>/dev/null | sort -rh | head -20; rm -rf "$STAGE"; exit 3
fi

# ---------- 5. skill-sync artifact ----------
cp -f .claude/bin/sync-skills.sh "$ROOT/SKILL-SYNC.sync-skills.sh" 2>/dev/null || true
{
  echo "# Claude <-> Codex skill sync"
  echo
  echo "Mechanism: \`sync-skills.sh\` (SessionStart hook). Additive union, symlink-only,"
  echo "never overwrites, never deletes. Each skill has one real dir on its origin side"
  echo "and a symlink on the other. In this bundle both sides are dereferenced to real content."
  echo
  cc=$(find .claude/skills -mindepth 1 -maxdepth 1 2>/dev/null | wc -l)
  xc=$(find .codex/skills  -mindepth 1 -maxdepth 1 2>/dev/null | wc -l)
  echo "- claude skills: $cc"
  echo "- codex skills:  $xc"
  echo
  echo "## claude-origin (real dir in .claude/skills, symlinked into .codex)"
  for d in .claude/skills/*/; do n=$(basename "$d"); [ -L "${d%/}" ] || echo "- $n"; done | sort
  echo
  echo "## codex-origin (real dir in .codex/skills, symlinked into .claude)"
  for d in .codex/skills/*/; do n=$(basename "$d"); [ -L "${d%/}" ] || echo "- $n"; done | sort
} >"$ROOT/SKILL-SYNC.md"

# ---------- 6. secret scan (STRONG = abort, SOFT = warn) ----------
# A line matching a secret keyword is NOT a real secret when it is a placeholder,
# an env/KV reference, or an already-redacted finding. Filter those before deciding.
PLACEHOLDER='os\.environ|getenv|process\.env|REDACTED|MASKED|KeyVault|SecretUri|@Microsoft|\$\{|\$\(|<[A-Za-z0-9._-]+>|x{3,}|example|placeholder|your[_-]|changeme|dummy|sample|test[_-]?secret|whsec_test|sk_xxx|from Azure|password manager|secure channel'
: >"$STAGE/strong.txt"; : >"$STAGE/soft.txt"
addS(){ grep -rnIE "$2" "$ROOT" 2>/dev/null | grep -vEi "$PLACEHOLDER" \
        | sed -E "s|^$ROOT/([^:]+):([0-9]+):.*|  [$1] \1:\2|" >>"$STAGE/strong.txt" || true; }
addW(){ grep -rIlE "$2" "$ROOT" 2>/dev/null | sed "s|^$ROOT/|  [$1] |" >>"$STAGE/soft.txt" || true; }
addS openai    'sk-[A-Za-z0-9]{20,}'
addS aws       'AKIA[0-9A-Z]{16}'
addS privkey   '-----BEGIN [A-Z ]*PRIVATE KEY-----'
addS slack     'xox[bapr]-[A-Za-z0-9-]{10,}'
addS github    'gh[pousr]_[A-Za-z0-9]{30,}'
addS jwt       'eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}'
addS azkey     'AccountKey=[A-Za-z0-9+/]{40,}'
addS pgpass    'PGPASSWORD=.?[A-Za-z0-9]{6,}'
addS urlcred   '://[A-Za-z0-9_.-]+:[A-Za-z0-9!%@._-]{6,}@'
addS pwliteral '(password|passwd|client_secret|secret_key)"?[[:space:]]*[:=][[:space:]]*"[A-Za-z0-9!%@._/+-]{8,}"'
addW password  '(password|passwd|client_secret)[[:space:]]*[:=][[:space:]]*[^[:space:]]{8,}'
addW apikey    '(api[_-]?key|access_key|secret_key)[[:space:]]*[:=][[:space:]]*[A-Za-z0-9_-]{24,}'
sort -u "$STAGE/strong.txt" -o "$STAGE/strong.txt"
sort -u "$STAGE/soft.txt"   -o "$STAGE/soft.txt"

if [ -s "$STAGE/strong.txt" ]; then
  echo "[ABORT] strong secret pattern(s) found in staged content - NOT zipping:"
  cat "$STAGE/strong.txt"
  echo "Staging left at: $STAGE  (inspect, then re-run after removing the offending file)"
  exit 4
fi

# ---------- 7. manifest ----------
{
  echo "# Shoval Benjer - docs + agent-setup bundle"
  echo
  echo "Generated: $TS  |  host: $(hostname)  |  staged size: ${STAGE_SZ}M"
  echo
  echo "## What this is"
  echo "A backup/share bundle of documentation and the Claude+Codex agent setup."
  echo "Code trees, caches, session transcripts, model/video artifacts, sqlite stores,"
  echo "and all secrets/keys/.env/auth files are deliberately EXCLUDED."
  echo
  echo "## Included"
  echo "- \`docs/\` - full personal docs tree"
  echo "- \`projects/**/docs\` - every real docs/documentation subdir of the ACTIVE projects"
  echo "  (${#PROJ[@]} dirs; worktree, build-bundle, node_modules copies pruned)"
  echo "- \`.claude/\` setup: CLAUDE.md, settings, rules, skills, commands, hooks, agents,"
  echo "  bin, docs, plans, corpus, config, jobs, teams, structured memory"
  echo "- \`.codex/\` setup: AGENTS.md, RTK.md, config.toml, hooks, skills, rules, agents,"
  echo "  bin, automation prompts, migrated-from-claude, structured memories, reports"
  echo "- \`SKILL-SYNC.md\` + \`SKILL-SYNC.sync-skills.sh\` - the claude<->codex skill union"
  echo
  echo "## Excluded (and why)"
  echo "- secrets: .codex/secrets/, .codex/auth.json, all .env*, *.key/.pem/.pfx,"
  echo "  daemon-auth-status.json, installation_id (never leave the host)"
  echo "- bulk data: .claude/projects session transcripts, .codex/agent-control,"
  echo "  .codex/sessions, *.sqlite logs, caches, assets, mcp-servers, plugins (node deps)"
  echo "- project code: source, node_modules, .git, venvs, model weights, video renders"
  echo "- projects/.archive/ (inherited/old; Oded docs alone is 4.7G of embedded media)"
  echo "- raw memory dumps: raw_memories.md, phase2_workspace_diff.md"
  echo
  echo "## Provenance"
  echo "Built read-only from \$HOME via rsync allowlist + prune. No production source touched."
  echo
  echo "## Distribution warning"
  echo "Contains internal i-sdd docs and may contain colleague/customer names (meeting notes,"
  echo "Jira drafts, CRM references). NOT cleared for public/external publication as-is."
  if [ -s "$STAGE/soft.txt" ]; then
    echo
    echo "## Soft scan notes (review before sharing - likely example/config text, not live secrets)"
    sed 's/^/- /' "$STAGE/soft.txt"
  fi
  echo
  echo "## Top-level contents"
  ( cd "$ROOT" && find . -maxdepth 2 -type d | sort | sed 's|^\./||;s|^|- |' )
} >"$ROOT/MANIFEST.md"

# ---------- 8. zip ----------
( cd "$STAGE" && zip -r -q "$ZIP" "$NAME" )
ZSZ="$(du -h "$ZIP" | cut -f1)"
FCOUNT="$(find "$ROOT" -type f | wc -l)"

echo
echo "================ BUNDLE READY ================"
echo "zip:    $ZIP"
echo "size:   $ZSZ   files: $FCOUNT   staged: ${STAGE_SZ}M"
echo "project docs dirs: ${#PROJ[@]}"
[ -s "$STAGE/soft.txt" ] && { echo "soft-scan warnings:"; cat "$STAGE/soft.txt"; } || echo "secret scan: clean"
echo "top level:"
( cd "$ROOT" && du -sh */ 2>/dev/null | sort -rh )
echo "=============================================="

rm -rf "$STAGE"   # /tmp only; $HOME untouched
