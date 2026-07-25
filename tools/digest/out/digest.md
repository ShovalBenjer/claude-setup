# Claude OS Daily Digest

- TODO: 22 done, 33 open; next: COMPACTION CHURN (new, from that same log): 11 PreCompact fires in ~100 min, and 5 SessionStart fires sharing only 2 session ids = repeated post-compact re-entry, roughly one compaction every 3 min. Suspects: `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=70` (compacts 30% early) stacked with `CLAUDE_CODE_DISABLE_1M_CONTEXT=1` (200k not 1M), leaving ~140k usable. Hooks now log `trigger=auto|manual` and `source=`, so the next session measures the auto/manual split directly
- claude-setup repo: main, dirty (91)
- Branch health: 20 merged-deletable, 2 default-branch drift

- OPEN LESSONS (8) — unenforced until closed:
  - L006: parallel sessions need structural separation (queues+charters), not intent -> ADR-0013 + docs/charters.md + work-claims (db pending AUTO-06)
  - L007: phone must reach a stateless-by-design intake, not a stateful stranger -> ADR-0013 concierge lane; RC pattern test pending (AUTO-05)
  - L008: green must mean green; cosmetic failures train alarm-blindness -> review workflow green-means-green fix — tracked in TODO P2
  - L009: calibration of claims IS the product of an autonomy system; a wrong DONE costs more than a -> rules/calibrated-claims.md + kernel-anchor v2 injection (every prompt)
  - L012: BLOCKED(operator) is a claim about the world and needs the same evidence bar as DONE. Befo -> AUTO-10/AUTO-18 unblocked and re-scored with command evidence (gh secr
  - L013: A verifier is the last place a false green is tolerable, and all three defects were false  -> All three fixed on disk at dot-claude/bin/deploy-setup.sh: --only spli
  - L014: Each error came from reasoning over a remembered artifact instead of re-reading it, and th -> Verification pattern adopted and used to close the meme removal: three
  - L015: An artifact's existence on disk is not evidence of which process produced it, and never ev -> Retraction stated to the operator in-line rather than quietly dropped:

Pending operator decisions: model default, key rotation, PR repo list, WhatsApp cadence, OAuth token.