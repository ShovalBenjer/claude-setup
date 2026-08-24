#!/usr/bin/env bash
# Clean, labeled, Widgora-palette HUD for the Claude Code statusline (two rows).
#
# Reads the Claude Code statusline JSON on stdin + ~/.claude/cache/hud.json (brain fields,
# refreshed in the background by `intent hud`). Every value is LABELED (Context, Estate, Gaps,
# Strategy, 5h), never a cryptic glyph. No emoji (house hard rule). Truecolor Widgora tokens.
#
# Reversible: to restore the old status line, point settings.json statusLine.command back at
# ~/.claude/bin/statusline.sh.
INPUT="$(cat)"

# --- Widgora OKLCH palette, approximated to sRGB truecolor ---
c() { printf '\033[38;2;%s;%s;%sm' "$1" "$2" "$3"; }
R='\033[0m'
ACCENT="$(c 61 125 255)"   # calm azure #3d7dff
TEXT="$(c 237 237 242)"
MUTED="$(c 139 145 163)"
GREEN="$(c 46 189 133)"    # #2ebd85 health
AMBER="$(c 224 162 58)"    # #e0a23a warning
RED="$(c 240 82 106)"      # #f0526a danger

j() { printf '%s' "$INPUT" | jq -r "$1" 2>/dev/null; }
CTX=$(j '(.context_window.used_percentage // 0) | floor'); [[ "$CTX" =~ ^[0-9]+$ ]] || CTX=0
MODEL=$(j '.model.display_name // .model.id // "Claude"')
COST=$(j '.cost.total_cost_usd // 0'); [[ "$COST" =~ ^[0-9.]+$ ]] || COST=0
CWD=$(j '.workspace.current_dir // .cwd // empty'); [ -d "$CWD" ] || CWD="$PWD"
FIVEH=$(j '.rate_limits.five_hour.used_percentage // empty | floor'); [[ "$FIVEH" =~ ^[0-9]+$ ]] || FIVEH=""
REPO=$(basename "$CWD")
BRANCH=$(git -C "$CWD" branch --show-current 2>/dev/null || echo '-')
[ -n "$BRANCH" ] || BRANCH='-'

# --- brain cache: estate score, open gaps (quests), strategy recommendation ---
HUD="$HOME/.claude/cache/hud.json"
ESTATE='-'; GAPS='-'; STRAT='-'; SPASS=''
if [ -f "$HUD" ]; then
  ESTATE=$(jq -r '.estate // "-"' "$HUD" 2>/dev/null)
  GAPS=$(jq -r '.gaps // "-"' "$HUD" 2>/dev/null)
  STRAT=$(jq -r '.strategy // "-"' "$HUD" 2>/dev/null)
  SPASS=$(jq -r 'if (.strategy_pass // 0) > 0 then ((.strategy_pass*100)|floor|tostring) else "" end' "$HUD" 2>/dev/null)
fi
# Refresh the cache in the background if stale (>120s) or for a different repo. Non-blocking.
NEED=1
if [ -f "$HUD" ]; then
  AGE=$(( $(date +%s) - $(stat -c %Y "$HUD" 2>/dev/null || echo 0) ))
  CREPO=$(jq -r '.repo // ""' "$HUD" 2>/dev/null)
  [ "$AGE" -le 120 ] && [ "$CREPO" = "$REPO" ] && NEED=0
fi
[ "$NEED" = 1 ] && ( "$HOME/.claude/bin/intent" hud --cwd "$CWD" >/dev/null 2>&1 & )

# --- context bar (8 cells), colored green -> amber -> red ---
W=14; F=$(( CTX * W / 100 )); [ "$F" -gt "$W" ] && F=$W; E=$(( W - F ))
if   [ "$CTX" -ge 80 ]; then BC="$RED"
elif [ "$CTX" -ge 50 ]; then BC="$AMBER"
else BC="$GREEN"; fi
FILL=""; i=0; while [ "$i" -lt "$F" ]; do FILL="${FILL}█"; i=$((i+1)); done
GAPB=""; i=0; while [ "$i" -lt "$E" ]; do GAPB="${GAPB}░"; i=$((i+1)); done
BAR="${BC}${FILL}${MUTED}${GAPB}${R}"

# --- row 1: identity ---
printf "${ACCENT}●${R}  ${TEXT}%s${R}     ${MUTED}%s   ·   %s   ·   \$%.2f${R}\n" "$REPO" "$BRANCH" "$MODEL" "$COST"

# --- row 2: vitals, all labeled ---
LINE="${MUTED}Context${R} ${BAR} ${TEXT}${CTX}%${R}"
LINE="${LINE}     ${MUTED}Estate${R} ${TEXT}${ESTATE}${R}"
LINE="${LINE}     ${MUTED}Gaps${R} ${TEXT}${GAPS}${R}"
LINE="${LINE}     ${MUTED}Strategy${R} ${TEXT}${STRAT}${R}${SPASS:+ ${MUTED}${SPASS}%${R}}"
[ -n "$FIVEH" ] && LINE="${LINE}     ${MUTED}5h${R} ${TEXT}${FIVEH}%${R}"
printf "%b\n" "$LINE"
