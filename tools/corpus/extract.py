#!/usr/bin/env python
"""Extract the conversational corpus from every session transcript on disk.

Purpose. tools/recall/session_recall.py answers "what did this one session say",
for a human, as markdown. This answers "what is in all of them", for a machine,
as JSONL, so turns can be embedded, clustered, or counted.

Contracts. Conversational text only: attachments are excluded unless asked for,
because on 2026-08-06 they measured 13.6M of the 16.1M characters under
~/.claude/projects and carry file contents, tool output, and cloud scans. Every
project slug is read, since the same repo has a different slug per host. Turns
are keyed by sha256 of their normalised text and repeats collapse into a
`repeats` count rather than vanishing.

Agent-context. Call extract(); the cmd_* functions are CLI shims. Do not call
clean() on raw text without unwrap_command() first, or command markup reaches the
corpus.

Typical usage:
  python tools/corpus/extract.py stats
  python tools/corpus/extract.py dump --out state/corpus/turns.jsonl
  python tools/corpus/extract.py selftest
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path

DEFAULT_ROOT = Path.home() / ".claude" / "projects"

NOISE = re.compile(
    r"^\s*(?:Stop hook feedback|Caveat: The messages below|"
    r"\[Request interrupted|\[SYSTEM NOTIFICATION|<system-reminder>|"
    r"<task-notification>|<local-command|"
    r"This session is being continued|\(Re-invocation of|"
    r"SESSION RECALL|Routing \(deterministic|"
    r"Base directory for this skill)",
    re.I,
)
INLINE = re.compile(
    r"<system-reminder>.*?</system-reminder>|<task-notification>.*?</task-notification>",
    re.S | re.I,
)
COMMAND_ARGS = re.compile(r"<command-args>(.*?)</command-args>", re.S | re.I)
COMMAND_NAME = re.compile(r"<command-name>\s*/?([\w-]+)\s*</command-name>", re.S | re.I)
COMMAND_WRAP = re.compile(r"^\s*<command-(?:message|name|args)\b", re.I)
COUNTERS = ("noise", "empty", "tool_result", "attachment", "command_unwrapped")


def text_of(msg: dict) -> str:
    """Concatenate a message's text blocks, ignoring tool_use and tool_result."""
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content
                         if isinstance(b, dict) and b.get("type") == "text")
    return ""


def is_tool_result(msg: dict) -> bool:
    """Report whether the message carries a tool_result block, which is not conversation."""
    content = msg.get("content")
    return isinstance(content, list) and any(
        isinstance(b, dict) and b.get("type") == "tool_result" for b in content)


def unwrap_command(raw: str) -> str | None:
    """Reduce a slash-command wrapper to '/name args', or None if not a wrapper.

    NOISE is anchored and lists <command-name>, but these turns open with
    <command-message>, so they matched nothing and reached the corpus as raw
    markup with the operator's words buried inside. Pollution rather than loss:
    embedding the tags is worse than embedding neither.
    """
    if not COMMAND_WRAP.match(raw.strip()):
        return None
    name = COMMAND_NAME.search(raw)
    args = COMMAND_ARGS.search(raw)
    parts = ["/" + name.group(1)] if name else []
    if args and args.group(1).strip():
        parts.append(args.group(1).strip())
    return " ".join(parts)


def clean(raw: str) -> str:
    """Strip mid-message injected blocks and collapse whitespace; '' means drop."""
    return " ".join(INLINE.sub(" ", raw).split())


def key_of(text: str) -> str:
    """Stable short digest used to collapse the verbatim-repeated boot block."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def iter_events(path: Path):
    """Yield parsed events, skipping unparseable lines.

    A torn final line is normal: these files are appended to by a live process.
    """
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def admits(event: dict, include_attachments: bool, tally: dict) -> bool:
    """Decide whether an event is in scope, recording why it was not."""
    etype = event.get("type")
    if etype == "attachment":
        tally["attachment"] += 1
        return include_attachments
    if etype not in ("user", "assistant"):
        return False
    if is_tool_result(event.get("message") or {}):
        tally["tool_result"] += 1
        return False
    return True


def turn_text(raw: str, tally: dict) -> str:
    """Normalise one turn's raw text to corpus text, or '' to drop it."""
    unwrapped = unwrap_command(raw)
    if unwrapped is not None:
        raw = unwrapped
        if raw:
            tally["command_unwrapped"] += 1
    if NOISE.match(raw.strip()):
        tally["noise"] += 1
        return ""
    text = clean(raw)
    if not text:
        tally["empty"] += 1
    return text


def record(event: dict, project: str, text: str) -> dict:
    """Build the JSONL row for one accepted turn."""
    return {"id": key_of(text), "role": event.get("type"), "project": project,
            "session": event.get("sessionId", ""),
            "ts": (event.get("timestamp") or "")[:19],
            "chars": len(text), "repeats": 1, "text": text}


def extract(root: Path, include_attachments: bool = False) -> tuple[list[dict], dict]:
    """Walk every project slug and return deduped turn records plus a skip tally."""
    seen: dict[str, dict] = {}
    tally = dict.fromkeys(COUNTERS, 0)
    for path in sorted(root.glob("*/*.jsonl")):
        for event in iter_events(path):
            if not admits(event, include_attachments, tally):
                continue
            text = turn_text(text_of(event.get("message") or {}), tally)
            if not text:
                continue
            row = seen.get(key_of(text))
            if row:
                row["repeats"] += 1
            else:
                seen[key_of(text)] = record(event, path.parent.name, text)
    return list(seen.values()), tally


def cmd_dump(args) -> int:
    """Write turn JSONL to --out, or to stdout when --out is absent."""
    rows, _ = extract(Path(args.root), args.include_attachments)
    if args.include_attachments:
        print("WARNING: attachments included; this is the high-PII majority of "
              "the corpus. Do not send it to a third party undecided.",
              file=sys.stderr)
    lines = [json.dumps(r, ensure_ascii=False) for r in rows]
    if not args.out:
        print("\n".join(lines))
        return 0
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote {} ({} turns, {:,} chars)".format(
        out, len(rows), sum(r["chars"] for r in rows)), file=sys.stderr)
    return 0


def tally_by(rows: list[dict], field: str) -> dict[str, int]:
    """Count rows per distinct value of one field."""
    counts: dict[str, int] = {}
    for row in rows:
        counts[row[field]] = counts.get(row[field], 0) + 1
    return counts


def cmd_stats(args) -> int:
    """Print corpus size, role split, per-slug counts, and why turns were skipped."""
    root = Path(args.root)
    if not root.is_dir():
        print("no project root at {}".format(root), file=sys.stderr)
        return 1
    rows, tally = extract(root, args.include_attachments)
    chars = sum(r["chars"] for r in rows)
    print("root          {}".format(root))
    print("unique turns  {}".format(len(rows)))
    print("collapsed     {} repeat(s)".format(sum(r["repeats"] - 1 for r in rows)))
    print("chars         {:,}   (~{:,} tokens at 4 chars/token)".format(chars, chars // 4))
    for role, n in sorted(tally_by(rows, "role").items()):
        print("  {:10s}  {}".format(role, n))
    print("skipped       " + ", ".join("{} {}".format(v, k) for k, v in sorted(tally.items())))
    print("")
    slugs = tally_by(rows, "project")
    for slug in sorted(slugs, key=lambda s: -slugs[s]):
        print("  {:6d}  {}".format(slugs[slug], slug))
    return 0


def filter_checks() -> list[tuple[str, bool]]:
    """Regex and normalisation checks needing no fixture on disk."""
    wrapped = ("<command-message>d</command-message><command-name>/deep-research"
               "</command-name><command-args>find DORA</command-args>")
    return [
        ("noise matches a stop-hook turn", bool(NOISE.match("Stop hook feedback: x"))),
        ("noise matches a skill body",
         bool(NOISE.match("Base directory for this skill: /home/x"))),
        ("noise spares prose mentioning a reminder",
         not NOISE.match("the <system-reminder> block is what I mean")),
        ("inline strip keeps surrounding words",
         clean("before <system-reminder>j</system-reminder> after") == "before after"),
        ("clean collapses whitespace", clean("a\n\n  b\t c") == "a b c"),
        ("clean of pure injection is empty",
         clean("<system-reminder>only</system-reminder>") == ""),
        ("wrapper yields name plus operator args",
         unwrap_command(wrapped) == "/deep-research find DORA"),
        ("wrapper with no args keeps the name",
         unwrap_command("<command-name>/reground</command-name>") == "/reground"),
        ("plain prose is not a wrapper", unwrap_command("a normal sentence") is None),
    ]


def write_fixture(root: Path) -> None:
    """Lay down a two-slug corpus exercising every skip path and a torn line."""
    events = [
        {"type": "user", "sessionId": "s1", "message": {"content": "hello world"}},
        {"type": "assistant", "sessionId": "s1",
         "message": {"content": [{"type": "text", "text": "an answer"}]}},
        {"type": "user", "sessionId": "s1",
         "message": {"content": "Stop hook feedback: ignore me"}},
        {"type": "user", "sessionId": "s1",
         "message": {"content": [{"type": "tool_result", "content": "x"}]}},
        {"type": "attachment", "sessionId": "s1", "message": {"content": "blob"}},
    ]
    (root / "proj-one").mkdir(parents=True)
    (root / "proj-two").mkdir(parents=True)
    (root / "proj-one" / "a.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events) + "\n{ torn", encoding="utf-8")
    (root / "proj-two" / "b.jsonl").write_text(
        json.dumps({"type": "user", "sessionId": "s2",
                    "message": {"content": "hello world"}}) + "\n", encoding="utf-8")


def corpus_checks(root: Path) -> list[tuple[str, bool]]:
    """Run extraction checks against the synthetic corpus written by write_fixture."""
    rows, tally = extract(root)
    texts = [r["text"] for r in rows]
    return [
        ("both slugs are read", len(rows) == 2),
        ("kept the operator turn", "hello world" in texts),
        ("kept the assistant turn", "an answer" in texts),
        ("dropped the stop-hook turn", not any("ignore me" in t for t in texts)),
        ("dropped the tool_result", tally["tool_result"] == 1),
        ("attachments excluded by default", tally["attachment"] == 1),
        ("duplicate across slugs collapsed",
         next(r["repeats"] for r in rows if r["text"] == "hello world") == 2),
        ("torn last line did not abort the walk", True),
        ("--include-attachments admits the blob",
         len(extract(root, include_attachments=True)[0]) == 3),
    ]


def cmd_selftest(_args) -> int:
    """Run every offline check and report the failures. No network, no real corpus."""
    with tempfile.TemporaryDirectory() as tmp:
        write_fixture(Path(tmp))
        checks = filter_checks() + corpus_checks(Path(tmp))
    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print("{:8s} {}".format("ok" if ok else "FAIL", name))
    print("selftest: {} checks, {} failed".format(len(checks), len(failed)))
    return 1 if failed else 0


def main(argv=None) -> int:
    """Parse arguments and dispatch to the requested subcommand."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--include-attachments", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("stats").set_defaults(fn=cmd_stats)
    dump = sub.add_parser("dump")
    dump.add_argument("--out")
    dump.set_defaults(fn=cmd_dump)
    sub.add_parser("selftest").set_defaults(fn=cmd_selftest)
    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
