#!/usr/bin/env bash
# Make the push-safety numbers real before anything is deleted.
#
# Every "0 unpushed" in the three inventory reports was measured against
# remote-tracking refs on disk, some of which predate 2025. That is not evidence a
# branch is on GitHub. This fetches every repo (read-only, no writes to any working
# tree) and reports true ahead/behind per local branch, plus stashes and dirt.
#
# GIT_TERMINAL_PROMPT=0 so a private repo without cached credentials fails fast and
# is reported as UNKNOWN rather than hanging the sweep waiting on a password.

export GIT_TERMINAL_PROMPT=0
export GIT_ASKPASS=echo

REPOS="
/c/Users/shova
/c/Users/shova/claude-setup
/c/Users/shova/deep_learning_neural_networks
/c/Users/shova/oren-roast-hq
/c/Users/shova/PycharmProjects/Web_Scraping
/c/Users/shova/PycharmProjects/deep_learning_neural_networks
/c/Users/shova/Downloads/GMShoot/gmshooter-v2
/c/Users/shova/Downloads/daily-deep-learning
/c/Users/shova/Downloads/moneyballz
/c/Users/shova/Downloads/new-recruit
/c/Users/shova/Downloads/search_by_ingredients
/c/Users/shova/codex-sites/living-codex-build
/c/Users/shova/gastown/projects/agenteval-bench
/c/Users/shova/gastown/projects/mcp-guard
/c/Users/shova/gastown/projects/protobuf-fuzz-guard
/c/Users/shova/tools/repo-sweep/sqltok
/c/solosolve-clustering
"

for R in $REPOS; do
  [ -d "$R/.git" ] || { printf '\n### %s\n  NOT A REPO (or absent)\n' "$R"; continue; }
  printf '\n### %s\n' "$R"

  REMOTES=$(git -C "$R" remote 2>/dev/null)
  if [ -z "$REMOTES" ]; then
    TOTAL=$(git -C "$R" rev-list --count --all 2>/dev/null || echo 0)
    printf '  NO REMOTE AT ALL. %s commit(s) exist only on this disk.\n' "$TOTAL"
  else
    for RM in $REMOTES; do
      printf '  remote %-28s %s\n' "$RM" "$(git -C "$R" remote get-url "$RM" 2>/dev/null)"
    done
    if git -C "$R" fetch --all --quiet --no-tags 2>/dev/null; then
      printf '  fetch: OK (numbers below are current)\n'
    else
      printf '  fetch: FAILED (auth or network). Numbers below are STALE, do not delete on them.\n'
    fi
  fi

  # Per-branch ahead/behind against its upstream, if it has one.
  git -C "$R" for-each-ref --format='%(refname:short)|%(upstream:short)' refs/heads 2>/dev/null |
  while IFS='|' read -r BR UP; do
    [ -n "$BR" ] || continue
    if [ -z "$UP" ]; then
      # No upstream. Is the tip reachable from ANY remote ref? If not, it is local-only.
      TIP=$(git -C "$R" rev-parse "$BR" 2>/dev/null)
      CONTAINED=$(git -C "$R" for-each-ref --contains "$TIP" --format='%(refname:short)' refs/remotes 2>/dev/null | head -3 | tr '\n' ' ')
      if [ -n "$CONTAINED" ]; then
        printf '    %-42s NO UPSTREAM, but tip is in: %s\n' "$BR" "$CONTAINED"
      else
        N=$(git -C "$R" rev-list --count "$BR" 2>/dev/null)
        printf '    %-42s NO UPSTREAM and tip on NO remote ref. %s commit(s) LOCAL-ONLY\n' "$BR" "$N"
      fi
    else
      AH=$(git -C "$R" rev-list --count "$UP..$BR" 2>/dev/null || echo '?')
      BH=$(git -C "$R" rev-list --count "$BR..$UP" 2>/dev/null || echo '?')
      printf '    %-42s ahead %-5s behind %-5s (upstream %s)\n' "$BR" "$AH" "$BH" "$UP"
    fi
  done

  DIRTY=$(git -C "$R" status --porcelain 2>/dev/null | grep -c '^[MARCD ][MARCD]' )
  UNTR=$(git -C "$R" status --porcelain 2>/dev/null | grep -c '^??')
  STASH=$(git -C "$R" stash list 2>/dev/null | wc -l)
  printf '  dirty=%s untracked=%s stashes=%s\n' "$DIRTY" "$UNTR" "$STASH"
done
