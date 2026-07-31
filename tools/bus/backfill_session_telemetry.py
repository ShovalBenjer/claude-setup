"""Backfill orchestration telemetry from the 2026-07-27 session.

`intent_control_plane.policy` implements a Thompson bandit over
STRATEGIES = ('workflow', 'subagent', 'solo', 'parallel_agents'), with 244 tests,
marked `done` as A16 in the platform-standard PRD. Its TELEMETRY_LOG at
~/.claude/cache/orchestration/telemetry.jsonl DOES NOT EXIST. The bandit has
never received a single row.

This session made six workflow decisions and several solo ones with known
outcomes. Those are exactly the observations the bandit needs, and throwing them
away would repeat the failure the whole estate is made of.

Statuses are graded against what the output was actually worth, not against
whether the run completed. `strategy_stats` counts a win as status == 'green',
so an over-generous grade here poisons the posterior directly. Two runs that
completed cleanly are graded amber because their output was partly wrong.

    python backfill_session_telemetry.py --dry-run
    python backfill_session_telemetry.py --apply
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]
                       / "intent-control-plane" / "src"))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from intent_control_plane import policy  # noqa: E402

SESSION = "9b378a13-5362-4571-930b-a31c4249aec0"

# (strategy, status, task, agents, tokens, ms, task_type, note)
OBSERVATIONS = [
    ("workflow", "amber",
     "distill 691 operator prompts + audit 32 own repos + triage 77 saved repos",
     43, 4_691_758, 3_611_159, "audit",
     "own-repo audit strong. The saved-repo half was README-depth only: 0 line "
     "numbers across 47 repos, and 23 of 41 verdicts were later overturned by a "
     "deeper pass. Also the caller truncated the synthesis input to 120k chars."),

    ("workflow", "amber",
     "five expert personas build competing profile README concepts, adversarially judged",
     24, 1_549_557, 2_720_262, "design",
     "Found real CI truth (a fuzz job that has never once passed, masked by "
     "continue-on-error). But all five concepts scored 5.0 to 5.7 of 10 and every "
     "judge landed the same kill shot, so the primary deliverable was mediocre."),

    ("workflow", "amber",
     "three-way map: operator intents to harness components to saved repos",
     15, 1_578_541, 2_597_356, "research",
     "Only 4 of 6 lanes reached the synthesizer and lane 4 was truncated mid-row. "
     "The wiring-gap finding it did produce was the most valuable of the session."),

    ("workflow", "green",
     "file-level investigation of 81 saved repos, reading source not READMEs",
     22, 2_266_580, 2_873_028, "audit",
     "484 evidence bullets, 81 of 81 rows carrying path:line. Overturned 23 of 41 "
     "prior verdicts, including four about to be adopted on a README."),

    ("workflow", "green",
     "context-engineering literature, prior art in shipped CLIs, local compaction diagnosis",
     17, 1_652_067, 2_520_923, "research",
     "Corrected three of the caller's own claims with better measurement: the "
     "97-percent figure, the every-3-minutes figure, and the env-var theory that "
     "had been carried in session notes for weeks. Highest-value run of the six."),

    ("workflow", "green",
     "skill-lifecycle literature, project routing, stale config, consolidated 113-repo ledger",
     16, 1_482_200, 1_966_566, "research",
     "Named the field's actual vocabulary (skill lifecycle governance, curation), "
     "which the caller had been guessing at, and produced the single consolidated "
     "ledger that six prior runs had left scattered."),

    ("solo", "green",
     "triage and move 1.0 GB of WhatsApp export out of the repo root",
     1, 0, None, "cleanup",
     "Repo root 137 to 43 entries. Dry-run by default, moved not deleted, and the "
     "git-tracked guard correctly refused one file that matched the move pattern."),

    ("solo", "amber",
     "author a full-setup architecture PRD",
     1, 0, None, "design",
     "Violated an active PRD that says in its own text: do not spawn dated notes. "
     "Also re-derived a 4-tier model on top of an existing verified 3-class one, "
     "and a bandit design on top of this very module. Excavation was skipped."),

    ("solo", "green",
     "fix session-recall.sh reading one hardcoded project memory tree",
     1, 0, None, "wiring",
     "Verified across three projects. Every session in every project had been "
     "recalling the home tree regardless of cwd."),

    ("solo", "amber",
     "build and register the PostToolUse skill-usage logger",
     1, 0, None, "wiring",
     "Hook works, verified with positive and negative controls. Graded amber: "
     "three false starts came from a broken test harness (Git Bash echo mangling "
     "JSON escapes), and the caller nearly rewrote correct code twice because of "
     "it. Registration in settings.json is still blocked."),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    rows = [
        policy.telemetry_row(
            strategy=s, status=st, task=task, agent_count=agents,
            subagent_tokens=tok, duration_ms=ms, task_type=tt,
            run_id=SESSION, note=note,
        )
        for s, st, task, agents, tok, ms, tt, note in OBSERVATIONS
    ]

    print(f"telemetry target : {policy.TELEMETRY_LOG}")
    print(f"exists before    : {pathlib.Path(policy.TELEMETRY_LOG).exists()}")
    print(f"rows to append   : {len(rows)}\n")

    for r in rows:
        print(f"  {r['strategy']:<8} {r['status']:<6} {r['task_type']:<8} "
              f"{r['agent_count']:>3} agents  {r['task'][:58]}")

    stats = policy.strategy_stats([json.dumps(r) for r in rows])
    print("\nwhat the bandit would see (this batch alone):")
    for name, s in sorted(stats.items()):
        print(f"  {name:<10} n={s['n']:<4} wins={s['wins']:<4} "
              f"pass_rate={s['pass_rate']:.2f}")

    print("\nNOTE: 10 observations is far too few to act on. This is a seed so the "
          "posterior starts from evidence rather than from a uniform prior.")

    if not args.apply:
        print("\nDRY RUN. Nothing written. Re-run with --apply.")
        return 0

    for r in rows:
        policy.append_telemetry(r)
    print(f"\nappended {len(rows)} rows to {policy.TELEMETRY_LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
