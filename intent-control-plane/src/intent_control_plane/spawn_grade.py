"""A5: grade a live spawn's output and record it to the archive (the transmission gap).

Every gastown-spawn run calls grade_spawn: it screens the produced diff through the guardrails
(scoped-diff + reward-hacking), scores it against a rubric when one is supplied, disposes on a
failed deterministic check, and writes the outcome to the population archive as a variant. That is
what connects the engine to the wheels: real spawn outputs become graded, guardrail-screened
variants that company.persona_scorecard grades personas from over time. The logic lives here,
tested; the live spawner (~/.claude/bin/gastown-spawn.py) is a thin caller.

Pure composition over archive/guardrails/rubric; the only I/O is the archive append.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from intent_control_plane.archive import (
    ARCHIVE_LOG,
    append_variant,
    is_novel,
    keep_verdict,
    variant_record,
)
from intent_control_plane.guardrails import is_scoped_diff, reward_hacking_flags
from intent_control_plane.rubric import score_rubric


def grade_spawn(
    subject: str,
    persona: str,
    model: str,
    diff_text: str,
    *,
    criteria: list[dict[str, Any]] | None = None,
    results: dict[str, float] | None = None,
    baseline: float | None = None,
    novelty_texts: list[str] | None = None,
    cost_tokens: int = 0,
    archive_path: Path = ARCHIVE_LOG,
) -> dict[str, Any]:
    """Screen, score, and archive one spawn result. Returns the verdict + score + guardrail flags.

    Guardrails run first and are fatal: a reward-hacking or unscoped diff is rejected before the
    rubric is even consulted (a gamed diff must not buy a score). With criteria + results the outcome
    follows the same keep-if-better-and-novel-and-not-disposed rule as the swarm; criteria supplied
    without results fails closed as 'rejected' with a 'missing-results' tag (a grading intent that
    cannot run must not pass through, audit #12); with no criteria at all the variant is recorded as
    'scored' (screened but un-judged). Every outcome is archived, so even rejected variants survive as
    stepping stones and feed the persona scorecard.
    """
    flags = reward_hacking_flags(diff_text)
    scoped = is_scoped_diff(diff_text)
    failure_tags = list(flags)
    if not scoped:
        failure_tags.append("unscoped-diff")

    overall = 0.0
    dims: dict[str, float] = {}
    if failure_tags:
        verdict = "rejected-guardrail"
    elif criteria and results is None:
        verdict = "rejected"
        failure_tags.append("missing-results")
    elif criteria and results is not None:
        scored = score_rubric(criteria, results)
        overall = float(scored["overall"])
        dims = scored["per_criterion"]
        if scored["disposed"]:
            verdict = "rejected"
            failure_tags += list(scored["disposed_by"])
        elif keep_verdict(overall, baseline) != "kept" or (novelty_texts and not is_novel(diff_text, novelty_texts)):
            verdict = "rejected"
        else:
            verdict = "kept"
    else:
        verdict = "scored"

    row = variant_record(
        subject=subject,
        persona=persona,
        model=model,
        score=overall,
        dims=dims,
        cost_tokens=cost_tokens,
        verdict=verdict,
        failure_tags=failure_tags,
        content=diff_text,
    )
    append_variant(row, archive_path)
    return {"verdict": verdict, "score": overall, "flags": flags, "scoped": scoped, "variant_id": row["variant_id"]}


def _main(argv: list[str] | None = None) -> int:
    """CLI entrypoint the live spawner calls: reads the diff from stdin, grades + archives it."""
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(prog="spawn-grade")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--persona", required=True)
    parser.add_argument("--model", default="spawn")
    parser.add_argument("--cost-tokens", type=int, default=0)
    parser.add_argument("--archive-path", default=str(ARCHIVE_LOG))
    args = parser.parse_args(argv)
    diff_text = sys.stdin.read()
    if not diff_text.strip():
        print(json.dumps({"verdict": "empty", "score": 0.0}))
        return 0
    out = grade_spawn(
        args.subject,
        args.persona,
        args.model,
        diff_text,
        cost_tokens=args.cost_tokens,
        archive_path=Path(args.archive_path),
    )
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
