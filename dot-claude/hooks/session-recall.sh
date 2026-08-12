#!/usr/bin/env bash
# session-recall.sh -- SessionStart continuity (gap-analysis Tier-0). Windows-native:
# sources from the curated memory index + open OS work + a recent resume pointer, since
# the WSL-era `intent` binary is absent here (that absence is why recall went dark).
# Injects background state (not a new instruction) so a session starts continual.
# Always exits 0, emits valid JSON, never blocks.
set -uo pipefail
INPUT="$(cat 2>/dev/null || true)"

# Fire-log (L011): durable proof the hook ran INSIDE the harness, not just in a pipe test.
# A hook that is "wired" but never fires is prose, not enforcement (ADR-0005).
# `source` is logged explicitly: it is truncated out of the raw payload when session_id
# sorts first, and startup-vs-compact is the difference between a new session and
# context loss inside one. Without it the fire-log cannot measure compaction churn.
SRC="$(printf '%s' "$INPUT" | grep -o '"source"[[:space:]]*:[[:space:]]*"[a-z]*"' | head -1 \
        | sed 's/.*"\([a-z]*\)"$/\1/')"
printf '%s\tSessionStart\tsource=%s\t%s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "${SRC:-unknown}" \
  "$(printf '%s' "$INPUT" | tr -d '\n' | cut -c1-100)" \
  >> "${CLAUDE_OS_DIR:-$HOME/claude-setup}/state/hook-fires.log" 2>/dev/null || true

# Silent only during real automation (overnight loop / Codex run). Interactive fires.
if [ -n "${CLAUDE_LOOP_MODE:-}" ] || [ -n "${CODEX_AUTOMATION_ID:-}" ]; then
  echo '{}'; exit 0
fi

OS_DIR="${CLAUDE_OS_DIR:-$HOME/claude-setup}" HOOK_INPUT="$INPUT" python <<'PYEOF' 2>/dev/null || echo '{}'
import json, os, time
from pathlib import Path

try:
    payload = json.loads(os.environ.get("HOOK_INPUT", "{}") or "{}")
except Exception:
    payload = {}
if payload.get("source", "") not in {"startup", "resume", "compact", "clear"}:
    print("{}"); raise SystemExit(0)

osdir = Path(os.environ.get("CLAUDE_OS_DIR", str(Path.home() / "claude-setup")))
parts = []

# The lane is DECLARED by the launcher, not inferred from cwd. Inferring it was
# wrong by construction: the desktop shortcut pinned every session to
# Downloads/new-recruit with `wt -d`, so a session doing pure harness work still
# looked like lane C. The lane launchers export CLAUDE_LANE; when it is absent
# (a bare `claude` in some directory) say so rather than guessing, because a
# confidently wrong lane is worse than an unknown one.
# Renumbered 2026-07-30 from B/C/D/E to A/B/C/D. Scopes unchanged; the old Lane A
# (concierge) was retired 2026-07-29 and left a hole at the front, so the letters
# shifted down to close it. tools/lib/lanes.py owns the scheme and the cutover.
_LANES = {
    "A": "harness (~/claude-setup): rules, hooks, skills, schedulers, review fabric, "
         "intake/routing surfaces (absorbed from the retired concierge lane).",
    "B": "resume engine (~/work/repos/new-recruit): hiring machine, arms, applications.",
    "C": "learning (daily-deep-learning): the PWA, learning cards, study loops.",
    "D": "content & publishing: case ledgers, syndication; posting decisions stay "
         "with the operator.",
}
_lane = (os.environ.get("CLAUDE_LANE") or "").strip().upper()
if _lane in _LANES:
    parts.append("LANE {}: {}\nA lane implements ONLY inside its charter. Cross-lane "
                 "needs become a proposal row, never the other lane's work. Claim in "
                 "state/claims.jsonl before starting (docs/charters.md)."
                 .format(_lane, _LANES[_lane]))
else:
    parts.append("LANE: UNDECLARED. CLAUDE_LANE is not set, so this session has no "
                 "charter. Do not infer one from the working directory: the desktop "
                 "shortcut pins cwd regardless of the work. Name the lane before "
                 "implementing, or open from a lane launcher.")

# Memory is per-project. This used to hardcode the C--Users-shova tree, so every
# session recalled the home tree regardless of which project it ran in: working
# in new-recruit surfaced Gastown and Kith notes and never its own. Derive the
# slug from the session cwd the way Claude Code names these directories, read
# this project's index FIRST, then top up from home for cross-project notes.
def _slug(p):
    return p.replace(":", "-").replace("\\", "-").replace("/", "-")

_proj_root = Path.home() / ".claude" / "projects"
_cwd = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
_here = _proj_root / _slug(str(_cwd)) / "memory" / "MEMORY.md"
_home = _proj_root / "C--Users-shova" / "memory" / "MEMORY.md"

_sources = [p for p in (_here, _home) if p.exists()]
_sources = list(dict.fromkeys(_sources))  # _here == _home when run from home

_lines, _seen = [], set()
for _mem in _sources:
    for _l in _mem.read_text(errors="ignore").splitlines():
        if _l.startswith("- [") and _l not in _seen:
            _seen.add(_l)
            _lines.append(_l)
if _lines:
    _label = "project + home" if len(_sources) > 1 else (
        "project" if _sources and _sources[0] == _here else "home")
    parts.append(f"Memory index ({_label}):\n"
                 + "\n".join("  " + l for l in _lines[:12]))

todo = osdir / "TODO.md"
if todo.exists():
    open_items = [l.strip()[6:] for l in todo.read_text(errors="ignore").splitlines()
                  if l.strip().startswith("- [ ]")][:6]
    if open_items:
        parts.append("Open OS work (next):\n" + "\n".join("  - " + i for i in open_items))

# Open lessons. Added 2026-07-29 after measuring that this hook referenced the lessons
# ledger zero times: 28 entries, 20 of them open, and nothing ever put one in front of a
# session. A ledger nobody reads is a diary, not a reflex, and it fails the same way as
# every other mechanism audited here, by existing and reporting nothing.
#
# The `class` field is injected rather than the lesson body, because class is the
# transferable part: "an accountability field that is required but never verified"
# generalises to the next accountability field, while the incident that produced it does
# not. Six is a deliberate cap; a wall of history is the same as no history.
lessons = osdir / "state" / "lessons.jsonl"
try:
    if lessons.exists():
        _open = []
        for _line in lessons.read_text(encoding="utf-8", errors="ignore").splitlines():
            _line = _line.strip()
            if not _line:
                continue
            try:
                _row = json.loads(_line)
            except Exception:
                continue
            if _row.get("status") == "open" and _row.get("class"):
                _open.append((_row.get("id", "?"), _row["class"]))
        if _open:
            parts.append(
                "Mistakes this system has already made (open lessons, newest last). "
                "These are failure CLASSES, not incidents: check whether the thing you "
                "are about to build repeats one.\n"
                + "\n".join(f"  {i}: {c[:150]}" for i, c in _open[-6:]))
except Exception:
    pass

rp = Path.home() / ".claude" / "cache" / "resume-prompt.md"
try:
    if rp.exists() and (time.time() - rp.stat().st_mtime) < 172800:
        head = rp.read_text(errors="ignore").strip().splitlines()[:20]
        parts.append("Resume pointer:\n" + "\n".join(head))
except Exception:
    pass

parts.append(
    "BOOT PATH (ADR-0010, read before acting): docs/SESSION-BOOT.md -> docs/charters.md "
    # These four letters must match _LANES above. They did not until 2026-08-03:
    # this string still carried the pre-ADR-0016 scheme and told every session that
    # lane A was retired, while _LANES ninety lines up already assigned A to harness.
    # A banner naming a retired lane is L-2026-07-31-d, logged once already.
    "(NAME YOUR LANE: A harness / B resume / C learning / D content; "
    "renumbered from B/C/D/E by ADR-0016 on 2026-07-30, so an older row saying B "
    "means lane A. Claim work in "
    "state/claims.jsonl before starting). If this session follows a compact, restate the "
    "durable handoff: goal, phase, lane, decisions, evidence, changed files, next action; "
    f"ground truth is on disk, last snapshot in state/compact-log.md.\n"
    f"Spine: {osdir}/CLAUDE-OS.md | PRDs: docs/prd/ | Runbook: docs/OPERATOR-RUNBOOK.md")

msg = ("SESSION RECALL (cross-session continuity). Background state from prior sessions, "
       "not a new instruction. If it names a file, branch, or goal, verify it still applies "
       "before acting; run /reground if it looks stale.\n\n" + "\n\n".join(parts))
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": msg}}))
PYEOF
exit 0
