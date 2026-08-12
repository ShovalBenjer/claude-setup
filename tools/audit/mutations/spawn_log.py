"""Mutations for tools/intent/spawn_log.py.

This file records the one number the persona company is judged on: how many delegations
went to a company persona rather than to `general-purpose`. Measured 2026-08-05 across 66
transcripts, that number is 0 of 19 personas ever spawned.

A measurement instrument that flatters its subject is worse than no instrument, and the
subject here is a system this session is actively building. So the mutations below are
weighted toward the ways this file could make the company look like it is working when it
is not:

  DROPPING THE DEFAULT. An `Agent` call with no `subagent_type` IS `general-purpose`, and
  that is what all 28 measured delegations were. A version that skips those rows would
  record only the deliberate persona spawns and report a perfect ratio while measuring
  almost nothing. This is the single most dangerous regression in the file and it is the
  one a well-meaning "only log real spawns" edit produces.

  AGREEING BY DEFAULT. `agreed` must be false when there was no routing decision. If an
  absent route reads as a followed one, the routing-changes-behaviour question answers
  itself yes without evidence.

  SCORING ITSELF. `outcome` stays None. `skill-usage-log.sh` refuses the same thing by
  name and calls it the self-congratulation failure mode.

The `route_match` provenance field is mutated too, because the join is best-effort by
necessity: CLAUDE_SESSION_ID is not exported into hook env on this host (PERSONA-08), so
same-session matching would silently never fire. A fallback that does not announce itself
is a fallback that gets read as a real join.
"""

TARGET = "tools/intent/spawn_log.py"
ARGV = ["--selftest"]

MUTATIONS = [
    # ---- the flattering failure modes ----
    ("an Agent call with no subagent_type is dropped instead of recorded",
     "the most dangerous edit available here, and it looks like a cleanup. No "
     "subagent_type IS general-purpose, and that is what all 28 measured delegations "
     "were. Dropping them means the ledger holds only deliberate persona spawns and "
     "reports a flawless ratio while measuring almost nothing",
     '    if not subagent:\n        subagent = "general-purpose"',
     "    if not subagent:\n        return None"),

    ("a spawn with no routing decision counts as agreed",
     "the routing-changes-behaviour question would answer itself yes with no evidence. "
     "An absent route must never read as a followed one, because the honest answer to "
     "whether the router changes anything is allowed to be no",
     '        "agreed": bool(routed_slug) and routed_slug == subagent,',
     '        "agreed": (not routed_slug) or routed_slug == subagent,'),

    ("general-purpose stops being classified as a builtin",
     "the persona-versus-builtin split is the entire report. If general-purpose counts "
     "as a company persona, the 0-of-19 number reads as 28-of-28 and the thing being "
     "built appears finished on the day it was started",
     'BUILTINS = {"general-purpose", "Explore", "Plan", "claude", "statusline-setup"}',
     'BUILTINS = {"Plan", "claude", "statusline-setup"}'),

    ("the hook scores its own spawn",
     "skill-usage-log.sh refuses this by name and calls it the self-congratulation "
     "failure mode. An outcome written by the thing being measured is not evidence, and "
     "it would poison the later join against gate-runs and refutations",
     '        "outcome": None,',
     '        "outcome": "ok",'),

    # ---- the join, which is best-effort and must say so ----
    ("a fallback route join claims to be a session match",
     "CLAUDE_SESSION_ID is not exported into hook env here, so the same-session path "
     "rarely fires and nearly every row is a best-effort join against the newest routing "
     "row of any session. A fallback that does not announce itself is read as a real "
     "join, and the agreement rate computed from it would be fiction",
     '    return dict(rows[-1], route_match="latest-any-session")',
     '    return dict(rows[-1], route_match="session")'),

    ("the persona-to-filename mapping stops lowercasing",
     "`QA Lab` must become `qa-lab` to match ~/.claude/agents/. Without it no spawn can "
     "ever equal its routed slug, `agreed` is false on every row forever, and the "
     "conclusion drawn would be that routing never changes behaviour when in fact "
     "nothing was ever compared",
     '    return "-".join(w for w in persona.lower().split() if w not in _DROPPED)',
     '    return "-".join(w for w in persona.split() if w not in _DROPPED)'),

    # ---- scope ----
    ("every tool call is recorded as a spawn",
     "the ledger fills with Bash and Read rows and the denominator of the ratio becomes "
     "meaningless. The report would show a vanishing persona share for a reason that has "
     "nothing to do with delegation",
     '    if tool != "Agent" and not subagent:\n        return None',
     "    if False:\n        return None"),

    # Two rows removed 2026-08-12 during the PR 42 merge: they mutated
    # is_known_agent() and the slug normalizer, which existed only in this
    # branch's spawn_log and were dropped when the resolution adopted main's
    # tested version (main commit 94354e2). The dropped capability is named in
    # the PR 42 thread; if the comparison logic is ever ported, these two rows
    # come back with it (history: this file at 01f7f32^).

]
