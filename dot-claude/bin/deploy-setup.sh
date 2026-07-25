#!/usr/bin/env bash
# Deploy dot-claude/ (canonical, in git) to ~/.claude (live) without clobbering
# another session's edits.
#
# Why this is not `cp -r`: six-plus Claude sessions run in parallel on this box and
# write to ~/.claude while work is in flight. On 2026-07-25 at 00:44:42 one session
# rewrote ~/.claude/CLAUDE.md and settings.json in the same second, under another
# session that was mid-reasoning. A recursive copy would silently destroy that work,
# and the destroyed side is the side that is actually live.
#
# So this does a real three-way compare against a manifest of what was last
# deployed, and refuses to overwrite any live file that changed since:
#
#   repo == live                     SAME      nothing to do
#   live absent                      NEW       safe to create
#   live == manifest, repo differs   UPDATE    live untouched since last deploy, safe
#   live != manifest, repo differs   CONFLICT  someone edited live; refuse, report
#
# A first run has no manifest, so every difference is a CONFLICT by construction.
# That is deliberate: with no recorded ancestor there is no way to tell "repo is
# newer" from "live was edited", and guessing is how you lose work. Run --adopt
# once to record the current live state as the ancestor, resolve by hand, then
# deploy from there.
#
# Live-only files are never deleted. A file in ~/.claude that is not in the repo
# is reported and left alone; deleting it is how you would erase a hook another
# session just installed.
#
# Usage:
#   deploy-setup.sh                     dry run, report what would change
#   deploy-setup.sh --apply             copy NEW + UPDATE, never CONFLICT
#   deploy-setup.sh --adopt             record live state as the ancestor, copy nothing
#   deploy-setup.sh --only 'agents/*'   restrict to matching relative paths
#                                       repeatable, and 'a|b' / 'a,b' also work.
#                                       A filter matching nothing exits 2, never 0.
#   deploy-setup.sh --include-settings  also consider settings.json (excluded by default)
#
# Exit: 0 when live matches the repo and no conflicts remain, 1 otherwise. That
# makes it usable directly as a refutation verifier for "repo and live are in sync".
set -euo pipefail

REPO_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
SRC="$REPO_ROOT/dot-claude"
DEST="${CLAUDE_HOME:-$HOME/.claude}"
MANIFEST="$REPO_ROOT/state/deploy-manifest.tsv"

# settings.json is the highest-blast-radius file here: it registers the hooks that
# fire on every tool call, and a bad one breaks every running session at once. It
# stays opt-in so a routine skills sync can never touch it as a side effect.
DEFAULT_EXCLUDE=("settings.json" "settings.live-2026-07-23.json")

APPLY=0 ADOPT=0 INCLUDE_SETTINGS=0
ONLY_PATS=()

while [ $# -gt 0 ]; do
  case "$1" in
    --apply)            APPLY=1 ;;
    --adopt)            ADOPT=1 ;;
    --include-settings) INCLUDE_SETTINGS=1 ;;
    --only)
      # A `case` pattern cannot take alternation from a variable: the | is a
      # parse-time token, so a single $ONLY holding 'a|b|c' becomes ONE literal
      # pattern containing | characters and matches nothing, which then reads as
      # "in sync". Separators are split into real array elements here instead,
      # and the flag is repeatable.
      only_arg="${2:?--only needs a glob}"; shift
      IFS='|,' read -r -a _only_split <<< "$only_arg"
      for _p in "${_only_split[@]+"${_only_split[@]}"}"; do
        [ -n "$_p" ] && ONLY_PATS+=("$_p")
      done
      ;;
    -h|--help)          sed -n '2,45p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) printf 'unknown argument: %s (try --help)\n' "$1" >&2; exit 2 ;;
  esac
  shift
done

[ -d "$SRC" ] || { printf 'no canonical tree at %s\n' "$SRC" >&2; exit 2; }

hash_of() { sha256sum -- "$1" 2>/dev/null | cut -d' ' -f1; }

manifest_hash() {
  [ -f "$MANIFEST" ] || { printf -- '-'; return; }
  # exact tab-delimited match on the relative path, printing its recorded hash
  awk -F'\t' -v want="$1" '$2 == want { print $1; found=1; exit } END { if (!found) print "-" }' "$MANIFEST"
}

excluded() {
  if [ "$INCLUDE_SETTINGS" -eq 0 ]; then
    for e in "${DEFAULT_EXCLUDE[@]}"; do [ "$1" = "$e" ] && return 0; done
  fi
  return 1
}

# True when no --only filter is set, or when the path matches any one pattern.
only_matches() {
  [ "${#ONLY_PATS[@]}" -eq 0 ] && return 0
  local rel="$1" p
  for p in "${ONLY_PATS[@]}"; do
    # shellcheck disable=SC2254
    case "$rel" in $p) return 0 ;; esac
  done
  return 1
}

# Collect relative paths of every canonical file, NUL-safe for paths with spaces.
rels=()
while IFS= read -r -d '' f; do
  rels+=("${f#"$SRC/"}")
done < <(find "$SRC" -type f \
           -not -path '*/__pycache__/*' -not -name '*.pyc' \
           -not -path '*/.git/*' -print0 | sort -z)

[ "${#rels[@]}" -gt 0 ] || { printf 'canonical tree %s holds no files\n' "$SRC" >&2; exit 2; }

if [ "$ADOPT" -eq 1 ]; then
  mkdir -p -- "$(dirname -- "$MANIFEST")"
  tmp="$MANIFEST.tmp.$$"
  : > "$tmp"
  adopted=0
  for rel in "${rels[@]}"; do
    live="$DEST/$rel"
    [ -f "$live" ] || continue
    printf '%s\t%s\n' "$(hash_of "$live")" "$rel" >> "$tmp"
    adopted=$((adopted + 1))
  done
  mv -f -- "$tmp" "$MANIFEST"
  printf 'adopted %d live files as the deploy ancestor: %s\n' "$adopted" "$MANIFEST"
  printf 'nothing was copied. Re-run without --adopt to see what would deploy.\n'
  exit 0
fi

same=0 skipped=0 only_matched=0
new_files=() update_files=() conflict_files=()

for rel in "${rels[@]}"; do
  if excluded "$rel"; then skipped=$((skipped + 1)); continue; fi
  only_matches "$rel" || continue
  only_matched=$((only_matched + 1))

  repo="$SRC/$rel"; live="$DEST/$rel"
  rh=$(hash_of "$repo")

  if [ ! -f "$live" ]; then new_files+=("$rel"); continue; fi

  lh=$(hash_of "$live")
  if [ "$rh" = "$lh" ]; then same=$((same + 1)); continue; fi

  mh=$(manifest_hash "$rel")
  if [ "$lh" = "$mh" ]; then update_files+=("$rel"); else conflict_files+=("$rel"); fi
done

# A filter that matched nothing compared nothing. Reporting that as "in sync"
# would be a false green out of the one instrument meant to detect drift, so it
# exits 2 (usage error) and is never mistaken for a sync result.
if [ "${#ONLY_PATS[@]}" -gt 0 ] && [ "$only_matched" -eq 0 ]; then
  printf 'no canonical path matched --only: %s\n' "${ONLY_PATS[*]}" >&2
  printf 'nothing was compared. This is a filter error, not a sync result.\n' >&2
  exit 2
fi

# Prints a section, capped at 20 lines. The explicit `return 0` is load-bearing:
# the cap test used to be the last command of the loop, so a section holding 1 to
# 19 items left the function returning 1, and `set -e` then killed the script
# mid-report with exit 1. That is indistinguishable from a legitimate dry run, so
# --apply silently died before copying anything and still looked like a dry run.
# A reporting helper must never decide the script's exit status.
report() {
  local label="$1"; shift
  [ "$#" -gt 0 ] || return 0
  printf '%s (%d):\n' "$label" "$#"
  local shown=0
  for r in "$@"; do
    printf '  %s\n' "$r"
    shown=$((shown + 1))
    if [ "$shown" -ge 20 ]; then
      printf '  ... and %d more\n' "$(($# - shown))"
      break
    fi
  done
  return 0
}

# Live-only files: reported so drift is visible, never deleted.
live_only=()
if [ -d "$DEST" ]; then
  while IFS= read -r -d '' f; do
    rel="${f#"$DEST/"}"
    case "$rel" in */__pycache__/*|*.pyc|.git/*|projects/*|todos/*|shell-snapshots/*|statsig/*|assets/*|logs/*|state/*|history.jsonl|*.log) continue ;; esac
    [ -f "$SRC/$rel" ] || live_only+=("$rel")
  done < <(find "$DEST" -maxdepth 2 -type f -print0 2>/dev/null | sort -z)
fi

printf '%s -> %s\n' "$SRC" "$DEST"
printf 'in sync: %d' "$same"
[ "$skipped" -gt 0 ] && printf ', skipped as opt-in: %d (settings.json; pass --include-settings)' "$skipped"
printf '\n'

# "would" is a lie once --apply is set, and reading "would UPDATE" after an apply
# is what made a silent no-op look like a dry run. The verb tracks the mode.
if [ "$APPLY" -eq 1 ]; then verb='CREATE'; else verb='would CREATE'; fi
report "$verb" "${new_files[@]+"${new_files[@]}"}"
if [ "$APPLY" -eq 1 ]; then verb='UPDATE (live untouched since last deploy)'
else verb='would UPDATE (live untouched since last deploy)'; fi
report "$verb" "${update_files[@]+"${update_files[@]}"}"
report 'CONFLICT, live changed outside the repo, refusing' "${conflict_files[@]+"${conflict_files[@]}"}"
report 'live-only, not in repo, left alone' "${live_only[@]+"${live_only[@]}"}"

n_new=${#new_files[@]}; n_upd=${#update_files[@]}; n_con=${#conflict_files[@]}

if [ "$APPLY" -eq 0 ]; then
  if [ $((n_new + n_upd + n_con)) -eq 0 ]; then
    printf 'live matches the repo. Nothing to deploy.\n'; exit 0
  fi
  printf 'dry run. Re-run with --apply to write %d file(s); %d conflict(s) will still be refused.\n' \
    "$((n_new + n_upd))" "$n_con"
  exit 1
fi

if [ ! -f "$MANIFEST" ] && [ "$n_con" -gt 0 ]; then
  printf 'no manifest at %s, so every difference reads as a conflict.\n' "$MANIFEST" >&2
  printf 'run --adopt once to record the current live state as the ancestor.\n' >&2
  exit 1
fi

wrote=0
for rel in "${new_files[@]+"${new_files[@]}"}" "${update_files[@]+"${update_files[@]}"}"; do
  [ -n "$rel" ] || continue
  mkdir -p -- "$(dirname -- "$DEST/$rel")"
  cp -p -- "$SRC/$rel" "$DEST/$rel"
  wrote=$((wrote + 1))
done

# Refresh the ancestor for exactly what we just wrote, so the next run can tell a
# repo change from a live edit. Conflicted paths keep their old recorded ancestor.
if [ "$wrote" -gt 0 ]; then
  mkdir -p -- "$(dirname -- "$MANIFEST")"
  tmp="$MANIFEST.tmp.$$"
  : > "$tmp"
  for rel in "${rels[@]}"; do
    live="$DEST/$rel"
    [ -f "$live" ] || continue
    printf '%s\t%s\n' "$(hash_of "$live")" "$rel" >> "$tmp"
  done
  mv -f -- "$tmp" "$MANIFEST"
fi

printf 'wrote %d file(s); manifest refreshed.\n' "$wrote"
if [ "$n_con" -gt 0 ]; then
  printf '%d conflict(s) NOT written. Diff each, then --adopt or fix the repo copy.\n' "$n_con"
  exit 1
fi
exit 0
