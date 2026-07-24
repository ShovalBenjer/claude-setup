# Spec — PST Extraction v1, First Real Run

**Date:** 2026-05-04
**Owner:** shoval
**Branch:** `feat/v109-yasha-multilingual` (run from $HOME, but writes only to `~/.claude/cache/pst/` — not a code change)
**Forge-loop status target:** Hit SPEC + PREMORTEM + RED + GREEN + COVERAGE + REFLECT this run (6/8 axes; REFACTOR + CI-BIND don't apply to a data-extraction run)

## What it does

Run the existing `~/.claude/cache/layer7/extract-pst.sh` pipeline against `/home/shovalbe/shoval.be@i-sdd.com.pst`, producing:
- mbox tree at `~/.claude/cache/pst/mbox/`
- privacy-aware JSONL at `~/.claude/cache/pst/latest.jsonl`
- full bodies at `~/.claude/cache/pst/.bodies/<sha1>.txt` (mode 0600)
- pst_messages rows in `~/.claude/cache/sessions.db`

## Why now

- `pst_messages` table schema v2 has been applied since 2026-05-03 → ready to receive rows.
- `a05-pst-email-action-mining` cron (Mon 02:00 IL) consumes `latest.jsonl` → currently empty → cron has been a no-op since the schema landed.
- Codex weekly quota exhausted until 2026-05-05 09:10 IL → /review-able tasks are blocked anyway → this is a no-codex task that closes a real gap.
- Path A discipline has not been runtime-tested. This is the first concrete task that exercises the loop end-to-end.

## Acceptance criteria (mapped to tests)

| AC | Test |
|---|---|
| AC1: readpst exits 0 | `bash extract-pst.sh; echo $?` returns 0 |
| AC2: At least 1 mbox file produced | `find ~/.claude/cache/pst/mbox -name 'mbox' -o -name '*.mbox' \| wc -l` ≥ 1 |
| AC3: JSONL has ≥ 100 records (sanity for an 166MB inbox) | `wc -l ~/.claude/cache/pst/latest.jsonl` ≥ 100 |
| AC4: Each JSONL record validates as JSON | `python3 -c "import json; [json.loads(l) for l in open(p)]"` exits 0 |
| AC5: pst_messages row count = unique Message-ID count from JSONL (intentional dedup across folder copies — same email in Inbox + Azure_Devops folder = 2 JSONL rows, 1 DB row) | `sqlite3 sessions.db "SELECT count(*) FROM pst_messages"` equals `unique msg_id_hash` count from JSONL |
| AC6: All `.bodies/<hash>.txt` files are mode 0600 | `find .bodies -type f ! -perm 0600 \| wc -l` == 0 |
| AC7: No body content leaked to JSONL (privacy guard) | `grep -c body_path ~/.claude/cache/pst/latest.jsonl` == JSONL line count, AND no `body_text` field in JSONL |
| AC8: Sample query returns recent action-relevant messages | `sqlite3 ... "SELECT subject, from_addr FROM pst_messages WHERE date_utc > '2026-04-01' AND from_addr LIKE '%i-sdd%' LIMIT 3"` returns ≥ 1 row |

## Premortem — 5 failure modes

1. **Outlook is actively writing to the .pst during readpst.** The .pst was last touched 2026-05-04 14:46 (Outlook sync). Concurrent write could corrupt readpst output mid-stream.
   *Mitigation:* `cp /home/shovalbe/shoval.be@i-sdd.com.pst /tmp/pst-snapshot-<stamp>.pst` first. Run readpst on the snapshot. Original .pst stays untouched. Worst case: snapshot is also mid-write, but at least readpst doesn't fight Outlook.

2. **Disk space exhaustion.** 166MB .pst could expand to ~500MB-1GB of mbox + bodies. Currently 860GB free → fine, but verify.
   *Mitigation:* `df -h ~/.claude/cache/pst` pre-flight check. Abort if < 5GB free.

3. **Hebrew/Arabic encoding garble.** Mixed-charset email bodies (UTF-8 / Windows-1255 / ISO-8859-8 for Hebrew) → `parse-mbox.py` uses `errors='replace'` which produces � for unknown chars but doesn't crash.
   *Mitigation:* Accept some garble in v1. Log charset distribution post-run. Future: try `chardet` for unknown-encoding detection.

4. **Privacy leak — `body_text` field accidentally included in JSONL.** The script writes bodies to `.bodies/<hash>.txt` separately, but a regression in `parse-mbox.py` could include the body inline in the JSONL record.
   *Mitigation:* AC7 explicitly tests for `body_text` field absence. The current script (just-written) doesn't include it but the test catches future regressions.

5. **`pst_messages` INSERT contention.** sessions.db is concurrently accessed by Layer 7 SessionStart/Stop hooks (just wired this turn). 50K row INSERTs in a tight loop could lock the DB.
   *Mitigation:* sqlite WAL mode is default for sessions.db (set during init). INSERT in batches of 1000 with explicit transactions. Run extraction when no Claude session is mid-restart.

## What this run does NOT do

- No semantic search yet (embeddings) — that's a separate task.
- No action-item mining — that's a05 cron's job, not this run.
- No ADO work-item creation — same, a05 owns that.
- No update to the .pst itself — read-only on the snapshot copy.

## Test plan (RED before, GREEN after)

```bash
# RED: write all 8 acceptance criteria as a single shell test script
~/.claude/cache/layer7/test-pst-acceptance.sh
# expected before extraction: ALL ACs FAIL (no JSONL, no rows, no bodies)

# RUN
~/.claude/cache/layer7/extract-pst.sh

# GREEN: re-run the same test script
~/.claude/cache/layer7/test-pst-acceptance.sh
# expected after extraction: ALL ACs PASS
```

If RED → GREEN does not transition cleanly across all 8 ACs, the run is a failure regardless of how many bytes ended up on disk.

## Forge-axis self-score (predicted)

| Axis | Predicted result |
|---|---|
| SPEC | ✓ this file |
| PREMORTEM | ✓ 5 modes above |
| RED | ✓ test-pst-acceptance.sh runs and FAILS pre-extraction |
| GREEN | ✓ same test PASSES post-extraction |
| REFACTOR | N/A (data run, no code to refactor) |
| COVERAGE | ✓ 8 ACs each map to a discrete test command |
| REFLECT | ✓ /heidegger-reflect at end |
| CI BIND | N/A (no commit-push-pr — config-adjacent run, no PR) |

Predicted: 6/8 axes hit. (REFACTOR + CI-BIND inapplicable for this task type — but if the audit is strict, they count as missed.)
