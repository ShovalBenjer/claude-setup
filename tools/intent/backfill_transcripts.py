#!/usr/bin/env python3
"""Recover typed prompts from every Claude Code transcript into the intent store.

WHY THIS EXISTS. Live capture writes two records per prompt: a hashed row in
`state/prompt-tickets.jsonl` that needs nothing but stdlib, and the verbatim event in
`~/.intent` that needs `intent_control_plane` on the path. From the 2026-07-31 WSL move
until 2026-08-10 the second half raised `ModuleNotFoundError` under the plain `python3`
the hook runs as, and `capture_turn.enrich`'s bare except swallowed it. Ten days of
prompts kept their hash and dropped their text: 545 chained rows against 23 events.

The words are not gone. They are in `~/.claude/projects/<slug>/<session>.jsonl`, which
is the only surviving copy. This module reads those files and replays them through the
same id function live capture uses, so a recovered prompt and a captured one are the
same ticket rather than two.

WHAT IT REFUSES TO DO. It writes `CAPTURED` and nothing else. There is no argument that
reaches `OPEN`, because promoting a prompt to work requires reading it, and a backfill
that guesses intent produces a backlog nobody can trust. That is structural here, not a
convention: `advance` is not imported.

THE EXTRACTION FILTER IS THE WHOLE RISK. `"type":"user"` in a transcript covers tool
results, harness notifications, compaction summaries and meta lines as well as things a
human typed. Measured on this machine 2026-08-10, 23,048 lines carry that type and 1,117
survive the filter below. The 2026-07-29 corpus made this mistake in the other direction
and had to drop 97.1 percent of its characters after the fact, so `funnel()` reports
every stage and `--dry-run` prints it. A wrong row here is worse than a missing one,
because a wrong row is indistinguishable from a right one once it is in the store.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "tools" / "intent") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools" / "intent"))

import tickets  # noqa: E402

PROJECTS = Path.home() / ".claude" / "projects"

# Openers that mark a line as authored by the harness rather than by the operator.
# Prefix matching, not substring: a prompt that quotes one of these strings partway
# through is still a prompt, and dropping it would lose real intent. The compaction
# opener is the expensive one to miss, since those blocks are assistant-authored
# summaries long enough to dominate any character-count view of the corpus.
HARNESS_PREFIXES = (
    "<system-reminder",
    "<local-command",
    "<command-name",
    "<command-message",
    "<command-args",
    "<user-prompt-submit-hook",
    "<bash-input",
    "<bash-stdout",
    "<task-notification>",
    "Caveat:",
    "[Request interrupted",
    "This session is being continued from a previous conversation",
    "Continue the conversation from",
)

FUNNEL_STAGES = (
    "type=user",
    "not a tool result",
    "not meta",
    "not sidechain",
    "plain text content",
    "not harness authored",
)


@dataclass(frozen=True)
class Prompt:
    """One typed prompt, with everything needed to mint its ticket."""

    slug: str
    session: str
    ts: str
    text: str
    cwd: str

    @property
    def sha(self) -> str:
        return tickets.text_sha(self.text)


def _content_text(message: Any) -> str | None:
    """The text of a user message, or None when it is not plain text.

    A list-shaped content block is how tool results and images arrive. Accepting one
    whose parts happen to all be text is deliberate, because a pasted-image-plus-text
    turn still carries a typed instruction, but a single non-text part disqualifies the
    line rather than being silently dropped from the joined string.
    """
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") != "text":
                return None
        content = "".join(
            block.get("text", "") for block in content if isinstance(block, dict)
        )
    if not isinstance(content, str):
        return None
    return content


def funnel(root: Path = PROJECTS, slug: str | None = None) -> tuple[Counter, list[Prompt]]:
    """Walk every transcript and report what each filter stage removed.

    The counter is the deliverable as much as the prompts are. A backfill that reports
    only its output count cannot be checked: 1,117 rows looks equally plausible whether
    the filter is right or whether it let a thousand tool results through.
    """
    counts: Counter = Counter()
    out: list[Prompt] = []
    if not root.is_dir():
        return counts, out
    for directory in sorted(root.iterdir()):
        if not directory.is_dir():
            continue
        if slug and slug not in directory.name:
            continue
        for transcript in sorted(directory.glob("*.jsonl")):
            out.extend(_read_transcript(transcript, directory.name, counts))
    return counts, out


def _read_transcript(path: Path, slug: str, counts: Counter) -> Iterator[Prompt]:
    """Yield the typed prompts in one transcript, counting every stage that drops a line.

    Errors are per line. A transcript truncated mid-write by a session that is still
    running is normal, and it must cost that one line rather than the file.
    """
    try:
        handle = path.open(encoding="utf-8", errors="replace")
    except OSError:
        return
    with handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, dict) or record.get("type") != "user":
                continue
            counts["type=user"] += 1
            if record.get("toolUseResult") is not None:
                continue
            counts["not a tool result"] += 1
            if record.get("isMeta"):
                continue
            counts["not meta"] += 1
            if record.get("isSidechain"):
                continue
            counts["not sidechain"] += 1
            text = _content_text(record.get("message"))
            if text is None or not text.strip():
                continue
            counts["plain text content"] += 1
            text = text.strip()
            if text.startswith(HARNESS_PREFIXES):
                continue
            counts["not harness authored"] += 1
            session = record.get("sessionId") or path.stem
            yield Prompt(
                slug=slug,
                session=session if isinstance(session, str) else path.stem,
                ts=str(record.get("timestamp") or ""),
                text=text,
                cwd=str(record.get("cwd") or ""),
            )


def plan(prompts: list[Prompt], existing: list[dict[str, Any]]) -> list[tuple[Prompt, str, bool]]:
    """Assign every prompt its ticket id, and say whether the ledger already holds it.

    Occurrence indices are the same numbering live capture uses: the i-th time a text
    repeats inside a session is occurrence i. So a prompt already captured live derives
    the id it was already given, and re-deriving it is how a re-run becomes a no-op
    instead of a second copy. Counting from the existing total instead would be
    idempotent too, but it would break the join to the rows live capture wrote, which is
    the property that makes a recovered prompt and a captured one one ticket.

    The third element is `needs_ledger`. It is not the same question as whether the
    store needs the text: the ten-day outage produced rows that have a hash and no
    event, so the two conditions are decided separately by the caller.
    """
    seen: Counter = Counter()
    for row in existing:
        session, sha = row.get("session"), row.get("text_sha")
        if isinstance(session, str) and isinstance(sha, str):
            seen[(session, sha)] += 1
    out: list[tuple[Prompt, str, bool]] = []
    occurrence: Counter = Counter()
    for prompt in sorted(prompts, key=lambda p: (p.session, p.ts, p.sha)):
        key = (prompt.session, prompt.sha)
        index = occurrence[key]
        occurrence[key] += 1
        out.append((prompt, tickets.ticket_id(prompt.session, prompt.sha, index),
                    index >= seen[key]))
    return out


def stored_tickets(base_dir: Path | None) -> set[str]:
    """Every `PT-` id the intent store already carries an event for.

    Read straight from sqlite rather than through the package, so a store that cannot be
    imported still answers the question and the run degrades to ledger-only instead of
    re-enriching everything.
    """
    import sqlite3

    if base_dir is None:
        # The path insert has to happen here and not only in `enrich`. Without it this
        # import raised, the except below answered "the store holds nothing", and the
        # run re-enriched every prompt live capture had already stored: 17 duplicate
        # bead ids on the first real run. An empty set is a legitimate answer for an
        # absent store and an actively wrong one for an unimportable package, so the
        # two cases must not share a code path.
        src = REPO_ROOT / "intent-control-plane" / "src"
        if src.is_dir() and str(src) not in sys.path:
            sys.path.insert(0, str(src))
        try:
            from intent_control_plane.schema import DEFAULT_BASE_DIR
            base_dir = DEFAULT_BASE_DIR
        except ImportError:
            base_dir = Path.home() / ".intent"
    db = Path(base_dir) / "intent.db"
    if not db.exists():
        return set()
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    except sqlite3.Error:
        return set()
    try:
        rows = conn.execute(
            "select bead_id from events where bead_id like 'PT-%'"
        ).fetchall()
    except sqlite3.Error:
        return set()
    finally:
        conn.close()
    return {r[0] for r in rows if r[0]}


def repo_name(prompt: Prompt) -> str:
    """The repo a prompt belongs to, matching what live capture records.

    `cwd` is authoritative when the transcript carries it. The directory slug is the
    fallback and is lossy: Claude Code flattens separators into dashes, so
    `daily-deep-learning/daemon` and `daily-deep-learning-daemon` are the same slug and
    cannot be told apart. Preferring `cwd` keeps that ambiguity out of the store for
    every line that offers a way to avoid it.
    """
    if prompt.cwd:
        return Path(prompt.cwd).name
    return prompt.slug.strip("-").split("-")[-1] or prompt.slug


def enrich(prompt: Prompt, ticket: str, base_dir: Path | None) -> None:
    """Write the verbatim event, its intent card and the CAPTURED transition.

    Separated from the ledger append because it is the half with a dependency. The
    caller records a failure here as a number rather than aborting: a recovered hash
    with no text is the state we are already in, and stopping the run would leave the
    remaining prompts in it too.
    """
    src = REPO_ROOT / "intent-control-plane" / "src"
    if src.is_dir() and str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from intent_control_plane.cli import capture, extract_intent
    from intent_control_plane.schema import DEFAULT_BASE_DIR, connect

    target = base_dir or DEFAULT_BASE_DIR
    args = argparse.Namespace(
        base_dir=target,
        event_type="user_prompt",
        authority="raw_user_prompt",
        actor="shoval",
        session=prompt.session,
        repo=prompt.cwd or prompt.slug,
        branch=None,
        bead=ticket,
        workflow=None,
        text=prompt.text,
        metadata=json.dumps({
            "text_sha": prompt.sha,
            "source": "backfill_transcripts",
            "transcript_slug": prompt.slug,
            "transcript_ts": prompt.ts,
        }),
    )
    event = capture(args)
    extract_intent(argparse.Namespace(base_dir=target, event=event["event_id"]))

    # `capture` stamps `utc_now()`, which is correct for a live prompt and wrong for a
    # recovered one: it would file ten days of history under the hour the recovery ran
    # and destroy the per-session ordering that makes the store worth querying. The
    # transcript's own timestamp is the fact, so it replaces the clock. Restricted to
    # this one event id, and skipped when the transcript line carried no timestamp.
    if prompt.ts:
        with connect(target) as conn:
            conn.execute(
                "update events set timestamp_utc = ? where event_id = ?",
                (prompt.ts, event["event_id"]),
            )
            conn.commit()


def run(
    *,
    slug: str | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    base_dir: Path | None = None,
    ledger: Path | None = None,
    root: Path = PROJECTS,
) -> dict[str, Any]:
    """Extract, plan, and write. Returns the report the CLI prints."""
    path = ledger or tickets.TICKETS
    counts, prompts = funnel(root, slug)
    existing = tickets.read_rows(path)
    assigned = plan(prompts, existing)
    already = stored_tickets(base_dir)

    work = [(p, t, needs) for p, t, needs in assigned if needs or t not in already]
    if limit is not None:
        work = work[:limit]

    report: dict[str, Any] = {
        "funnel": {stage: counts.get(stage, 0) for stage in FUNNEL_STAGES},
        "candidates": len(prompts),
        "sessions": len({p.session for p in prompts}),
        "projects": len({p.slug for p in prompts}),
        "ledger_rows_before": len(existing),
        "store_tickets_before": len(already),
        "to_write": sum(1 for _, _, needs in work if needs),
        "to_enrich": len(work),
        "written": 0,
        "enriched": 0,
        "enrich_failed": 0,
        "dry_run": dry_run,
    }
    if dry_run or not work:
        return report

    for prompt, ticket, needs_ledger in work:
        if needs_ledger:
            # prev and hash are computed under the lock inside append_chained, which is
            # where the tip can be read without racing a live session's own prompt.
            tickets.append_chained(
                ticket=ticket, ts=prompt.ts or "", session=prompt.session,
                repo=repo_name(prompt), branch="", prompt_sha=prompt.sha,
                state=tickets.GENESIS, path=path,
            )
            report["written"] += 1
        if ticket in already:
            continue
        try:
            enrich(prompt, ticket, base_dir)
            report["enriched"] += 1
        except Exception as exc:  # noqa: BLE001 - recorded, never fatal, see docstring
            report["enrich_failed"] += 1
            report.setdefault("first_enrich_error", f"{type(exc).__name__}: {exc}")
    return report


def selftest() -> int:
    """Prove the filter drops what it claims and that a second run writes nothing."""
    import tempfile

    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "projects" / "-home-shov-demo"
        root.mkdir(parents=True)
        lines = [
            {"type": "user", "sessionId": "s1", "timestamp": "2026-08-01T00:00:01Z",
             "cwd": "/home/shov/demo", "message": {"content": "fix the parser"}},
            {"type": "user", "sessionId": "s1", "timestamp": "2026-08-01T00:00:02Z",
             "toolUseResult": {"ok": True}, "message": {"content": "tool output"}},
            {"type": "user", "sessionId": "s1", "timestamp": "2026-08-01T00:00:03Z",
             "isMeta": True, "message": {"content": "meta"}},
            {"type": "user", "sessionId": "s1", "timestamp": "2026-08-01T00:00:04Z",
             "isSidechain": True, "message": {"content": "subagent turn"}},
            {"type": "user", "sessionId": "s1", "timestamp": "2026-08-01T00:00:05Z",
             "message": {"content": "<system-reminder>ignore me</system-reminder>"}},
            {"type": "user", "sessionId": "s1", "timestamp": "2026-08-01T00:00:06Z",
             "message": {"content": [{"type": "tool_result", "content": "x"}]}},
            {"type": "assistant", "message": {"content": "not a user turn"}},
            {"type": "user", "sessionId": "s1", "timestamp": "2026-08-01T00:00:07Z",
             "cwd": "/home/shov/demo", "message": {"content": "fix the parser"}},
            "{ this line is torn",
        ]
        with (root / "s1.jsonl").open("w", encoding="utf-8") as fh:
            for item in lines:
                fh.write((item if isinstance(item, str) else json.dumps(item)) + "\n")

        counts, prompts = funnel(root.parent)
        if len(prompts) != 2:
            failures.append(f"filter kept {len(prompts)} prompts, expected 2")
        if counts.get("type=user") != 7:
            failures.append(f"counted {counts.get('type=user')} user lines, expected 7")
        if [p.text for p in prompts] != ["fix the parser", "fix the parser"]:
            failures.append("filter kept the wrong texts")

        ledger = Path(tmp) / "prompt-tickets.jsonl"
        base = Path(tmp) / "intent"
        assigned = plan(prompts, [])
        if len({t for _, t, _ in assigned}) != 2:
            failures.append("the repeated prompt did not get two distinct ids")

        first = run(dry_run=False, base_dir=base, ledger=ledger, root=root.parent)
        if first["written"] != 2:
            failures.append(f"first run wrote {first['written']}, expected 2")
        if first["enriched"] != 2:
            failures.append(f"first run enriched {first['enriched']}, expected 2 "
                            f"({first.get('first_enrich_error', 'no error recorded')})")
        second = run(dry_run=False, base_dir=base, ledger=ledger, root=root.parent)
        if second["written"] or second["enriched"]:
            failures.append(f"re-run wrote {second['written']} and enriched "
                            f"{second['enriched']}, expected 0 and 0 (not idempotent)")
        breaks = tickets.verify(ledger)
        if breaks:
            failures.append(f"chain broken after backfill: {breaks}")

        # The recovered event must carry the transcript's timestamp, not the clock the
        # recovery ran under. Without this the store orders ten days of history by the
        # hour of the backfill, which is the property the per-session query depends on.
        import sqlite3

        conn = sqlite3.connect(base / "intent.db")
        stamps = [r[0] for r in conn.execute(
            "select timestamp_utc from events where bead_id like 'PT-%' order by 1")]
        conn.close()
        if stamps != ["2026-08-01T00:00:01Z", "2026-08-01T00:00:07Z"]:
            failures.append(f"event timestamps are {stamps}, expected the transcript's")

        # A ledger row whose event never landed is exactly the ten-day outage. A re-run
        # must repair it rather than skip it because the hash is already recorded.
        conn = sqlite3.connect(base / "intent.db")
        conn.execute("delete from events where event_id in "
                     "(select event_id from events where bead_id like 'PT-%' limit 1)")
        conn.commit()
        conn.close()
        repair = run(dry_run=False, base_dir=base, ledger=ledger, root=root.parent)
        if repair["written"] != 0 or repair["enriched"] != 1:
            failures.append(f"repair run wrote {repair['written']} and enriched "
                            f"{repair['enriched']}, expected 0 and 1")

        # `stored_tickets` deciding "nothing is stored" when it merely could not read is
        # what put 17 duplicate bead ids in the live store on the first real run. The
        # regression is that an existing store is never reported as empty.
        if not stored_tickets(base):
            failures.append("stored_tickets reported an empty store that holds events")
        conn = sqlite3.connect(base / "intent.db")
        beads = [r[0] for r in conn.execute(
            "select bead_id from events where bead_id like 'PT-%'")]
        conn.close()
        if len(beads) != len(set(beads)):
            failures.append(f"{len(beads) - len(set(beads))} duplicate bead ids in the store")

    for line in failures:
        print(f"FAIL {line}")
    if not failures:
        print("PASS backfill_transcripts selftest (7 checks)")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("run", "selftest"), nargs="?", default="run")
    parser.add_argument("--project", help="only transcripts whose directory slug contains this")
    parser.add_argument("--limit", type=int, help="stop after this many new tickets")
    parser.add_argument("--dry-run", action="store_true", help="report the funnel, write nothing")
    parser.add_argument("--json", action="store_true", help="machine-readable report")
    # Both default to the live locations. They are arguments because a worktree's copy of
    # the ledger is frozen at its branch point, so a run from inside one would fork the
    # chain against the checkout the capture hook is still appending to.
    parser.add_argument("--ledger", type=Path, help="chained mirror to append to")
    parser.add_argument("--base-dir", type=Path, help="intent store to enrich into")
    args = parser.parse_args(argv)

    if args.command == "selftest":
        return selftest()

    report = run(slug=args.project, limit=args.limit, dry_run=args.dry_run,
                 ledger=args.ledger, base_dir=args.base_dir)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    print("funnel:")
    for stage in FUNNEL_STAGES:
        print(f"  {stage:24s} {report['funnel'][stage]}")
    print(f"candidates {report['candidates']} across {report['sessions']} sessions, "
          f"{report['projects']} projects")
    print(f"ledger before {report['ledger_rows_before']}, to write {report['to_write']}, "
          f"written {report['written']}")
    print(f"enriched {report['enriched']}, enrich failed {report['enrich_failed']}")
    if "first_enrich_error" in report:
        print(f"first enrich error: {report['first_enrich_error']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
