#!/usr/bin/env python3
"""Catch-up digests for Claude Code sessions.

Replaces the paste-the-transcript-into-another-LLM ritual: reads the session
JSONL Claude Code already writes under ~/.claude/projects/, extracts the
structural facts deterministically (prompts, tool calls, files touched,
commands, tokens), and optionally asks a headless `claude -p` for a short
narrative digest on top. The structural pass never depends on the LLM, so
`--no-llm` always works offline.

The transcript schema is Claude Code's own and unversioned; every field
access here is defensive, and unknown row types are counted, not fatal.

Commands:
  list                     sessions found, newest first
  digest [opts]            digest one session (default: newest)
  selftest                 synthetic-fixture check, exit nonzero on failure
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECTS_DIR = Path(os.environ.get("CLAUDE_PROJECTS_DIR", Path.home() / ".claude" / "projects"))
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
NOTICE_MARKERS = ("<task-notification>", "[SYSTEM NOTIFICATION", "<system-reminder>", "<wake ")
TRUNC = 400


def _text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def parse_session(path):
    facts = {
        "path": str(path), "session_id": path.stem, "cwd": None, "branch": None,
        "models": set(), "first_ts": None, "last_ts": None, "turns": 0,
        "prompts": [], "assistant_texts": [], "tools": {}, "files": {},
        "commands": [], "subagents": [], "sidechain_rows": 0, "tokens_out": 0,
        "tokens_in": 0, "unknown_types": {}, "timeline": [],
    }
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                row = json.loads(line)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            rtype = row.get("type")
            ts = row.get("timestamp")
            if ts:
                facts["first_ts"] = facts["first_ts"] or ts
                facts["last_ts"] = ts
            if row.get("isSidechain"):
                facts["sidechain_rows"] += 1
                continue
            facts["cwd"] = row.get("cwd") or facts["cwd"]
            facts["branch"] = row.get("gitBranch") or facts["branch"]
            msg = row.get("message") or {}
            if rtype == "user":
                content = msg.get("content")
                blocks = content if isinstance(content, list) else []
                if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in blocks):
                    continue
                text = _text_of(content).strip()
                if text.startswith(NOTICE_MARKERS):
                    facts["timeline"].append(("notice", text[:TRUNC]))
                elif text:
                    facts["prompts"].append(text)
                    facts["timeline"].append(("user", text[:TRUNC]))
            elif rtype == "assistant":
                facts["turns"] += 1
                if msg.get("model"):
                    facts["models"].add(msg["model"])
                usage = msg.get("usage") or {}
                facts["tokens_out"] += usage.get("output_tokens") or 0
                facts["tokens_in"] += usage.get("input_tokens") or 0
                for b in msg.get("content") or []:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "text" and b.get("text", "").strip():
                        facts["assistant_texts"].append(b["text"].strip())
                        facts["timeline"].append(("assistant", b["text"].strip()[:TRUNC]))
                    elif b.get("type") == "tool_use":
                        name = b.get("name", "?")
                        facts["tools"][name] = facts["tools"].get(name, 0) + 1
                        inp = b.get("input") or {}
                        if name in EDIT_TOOLS and inp.get("file_path"):
                            facts["files"][inp["file_path"]] = facts["files"].get(inp["file_path"], 0) + 1
                        if name == "Bash":
                            facts["commands"].append(inp.get("description") or (inp.get("command") or "")[:80])
                        if name in {"Agent", "Task"}:
                            facts["subagents"].append(inp.get("description") or "unnamed agent")
                        facts["timeline"].append(("tool", f"{name}: " + json.dumps(
                            {k: str(v)[:60] for k, v in list(inp.items())[:3]}, ensure_ascii=False)))
            elif rtype not in {"system", "attachment", "queue-operation", "last-prompt", None}:
                facts["unknown_types"][rtype] = facts["unknown_types"].get(rtype, 0) + 1
    return facts


def structural_digest(facts):
    span = f"{(facts['first_ts'] or '?')[:16]} to {(facts['last_ts'] or '?')[:16]}"
    lines = [
        f"# Catch-up: {Path(facts['cwd'] or '?').name} [{facts['session_id'][:8]}]",
        f"- cwd {facts['cwd']} | branch {facts['branch']} | {span}",
        f"- {len(facts['prompts'])} user prompts, {facts['turns']} assistant turns, "
        f"models {', '.join(sorted(facts['models'])) or '?'}",
        f"- tokens out {facts['tokens_out']:,} | subagent rows skipped {facts['sidechain_rows']}",
    ]
    if facts["tools"]:
        top = sorted(facts["tools"].items(), key=lambda kv: -kv[1])
        lines.append("- tools: " + ", ".join(f"{k} x{v}" for k, v in top))
    if facts["files"]:
        lines.append("## Files touched")
        lines += [f"- {p} ({n} edits)" for p, n in sorted(facts["files"].items(), key=lambda kv: -kv[1])]
    if facts["subagents"]:
        lines.append("## Subagents launched")
        lines += [f"- {d}" for d in facts["subagents"]]
    if facts["commands"]:
        lines.append("## Commands run")
        lines += [f"- {c}" for c in facts["commands"][-15:] if c]
    if facts["prompts"]:
        lines.append("## Your asks")
        lines += [f"- {p[:TRUNC]}" for p in facts["prompts"]]
    if facts["assistant_texts"]:
        lines.append("## Last reported state")
        lines.append(facts["assistant_texts"][-1][:1500])
    if facts["unknown_types"]:
        lines.append(f"- note: unrecognized row types {facts['unknown_types']} (schema drift, non-fatal)")
    return "\n".join(lines)


def condensed_transcript(facts, max_chars):
    parts, total = [], 0
    for role, text in reversed(facts["timeline"]):
        entry = f"[{role}] {text}"
        if total + len(entry) > max_chars:
            break
        parts.append(entry)
        total += len(entry)
    return "\n".join(reversed(parts))


LLM_PROMPT = (
    "You are given the condensed transcript of one Claude Code session, most recent events last, "
    "plus structural facts. Write a catch-up digest for its owner, who runs several sessions in "
    "parallel and has not been watching. Sections, tight bullets: GOAL (what this session is for), "
    "DONE (what actually happened, name files and outcomes), DECISIONS (choices made and why), "
    "OPEN (unfinished threads, risks, unanswered questions), NEEDS YOU (what is blocked on the "
    "owner, or 'nothing'). Trust the structural facts over the prose when they disagree. "
    "Do not praise, do not pad.{lang}\n\nSTRUCTURAL FACTS:\n{facts}\n\nTRANSCRIPT:\n{transcript}"
)


def llm_digest(facts, hebrew, max_chars, llm_cmd):
    prompt = LLM_PROMPT.format(
        lang=" Write the digest in Hebrew." if hebrew else "",
        facts=structural_digest(facts), transcript=condensed_transcript(facts, max_chars))
    try:
        out = subprocess.run(llm_cmd + [prompt], capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, f"llm step failed ({e}); structural digest only"
    if out.returncode != 0:
        return None, f"llm step exited {out.returncode}: {out.stderr.strip()[:200]}"
    return out.stdout.strip(), None


def find_sessions():
    if not PROJECTS_DIR.is_dir():
        return []
    files = [p for p in PROJECTS_DIR.glob("*/*.jsonl") if p.is_file()]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def cmd_list(_args):
    rows = find_sessions()
    if not rows:
        print(f"no sessions under {PROJECTS_DIR}")
        return 1
    now = time.time()
    for p in rows:
        age = int((now - p.stat().st_mtime) / 60)
        print(f"{p.stem[:8]}  {age:>4}m ago  {p.stat().st_size // 1024:>6} KB  {p.parent.name}")
    return 0


def pick_session(args):
    rows = find_sessions()
    if args.session:
        rows = [p for p in rows if p.stem.startswith(args.session)]
    if args.project:
        rows = [p for p in rows if args.project in p.parent.name]
    return rows[0] if rows else None


def cmd_digest(args):
    path = pick_session(args)
    if not path:
        print(f"no matching session under {PROJECTS_DIR}", file=sys.stderr)
        return 1
    facts = parse_session(path)
    if args.no_llm:
        print(structural_digest(facts))
        return 0
    text, err = llm_digest(facts, args.hebrew, args.max_chars, args.llm_cmd.split())
    if err:
        print(f"[{err}]", file=sys.stderr)
        print(structural_digest(facts))
        return 0
    print(text)
    return 0


FIXTURE = [
    {"type": "user", "timestamp": "2026-09-02T10:00:00Z", "cwd": "/tmp/proj", "gitBranch": "main",
     "message": {"role": "user", "content": "fix the flaky test"}},
    {"type": "assistant", "timestamp": "2026-09-02T10:01:00Z", "cwd": "/tmp/proj",
     "message": {"role": "assistant", "model": "claude-fable-5", "usage": {"output_tokens": 50, "input_tokens": 10},
                 "content": [{"type": "text", "text": "Looking at it."},
                             {"type": "tool_use", "name": "Edit", "input": {"file_path": "/tmp/proj/a.py"}},
                             {"type": "tool_use", "name": "Bash", "input": {"description": "run tests"}}]}},
    {"type": "user", "timestamp": "2026-09-02T10:02:00Z",
     "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]}},
    {"type": "assistant", "timestamp": "2026-09-02T10:03:00Z", "isSidechain": True,
     "message": {"role": "assistant", "content": [{"type": "text", "text": "subagent noise"}]}},
    {"type": "user", "timestamp": "2026-09-02T10:03:30Z",
     "message": {"role": "user", "content": "[SYSTEM NOTIFICATION - NOT USER INPUT]\nagent finished"}},
    {"type": "assistant", "timestamp": "2026-09-02T10:04:00Z",
     "message": {"role": "assistant", "model": "claude-fable-5", "usage": {"output_tokens": 30},
                 "content": [{"type": "text", "text": "Fixed and green."}]}},
]


def cmd_selftest(_args):
    failures = []
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "s1.jsonl"
        p.write_text("\n".join(json.dumps(r) for r in FIXTURE) + "\nnot json\n", encoding="utf-8")
        facts = parse_session(p)
        checks = {
            "one prompt": len(facts["prompts"]) == 1,
            "two turns": facts["turns"] == 2,
            "edit counted": facts["tools"].get("Edit") == 1,
            "file tracked": facts["files"].get("/tmp/proj/a.py") == 1,
            "sidechain skipped": facts["sidechain_rows"] == 1 and "subagent noise" not in facts["assistant_texts"],
            "tokens summed": facts["tokens_out"] == 80,
            "last state": facts["assistant_texts"][-1] == "Fixed and green.",
            "branch": facts["branch"] == "main",
            "bad line survived": True,
            "notice filtered": len(facts["prompts"]) == 1 and any(r == "notice" for r, _ in facts["timeline"]),
        }
        digest = structural_digest(facts)
        checks["digest names file"] = "/tmp/proj/a.py" in digest
        checks["digest names ask"] = "fix the flaky test" in digest
        condensed = condensed_transcript(facts, 10_000)
        checks["condensed ordered"] = condensed.index("fix the flaky") < condensed.index("Fixed and green")
        failures = [name for name, ok in checks.items() if not ok]
    for name in failures:
        print(f"FAIL {name}")
    print(f"catchup selftest: {len(failures)} failures / 13 checks")
    return 1 if failures else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    d = sub.add_parser("digest")
    d.add_argument("--session", help="session id prefix")
    d.add_argument("--project", help="substring of the flattened project dir name")
    d.add_argument("--no-llm", action="store_true", help="structural digest only, no claude call")
    d.add_argument("--he", dest="hebrew", action="store_true", help="narrative digest in Hebrew")
    d.add_argument("--max-chars", type=int, default=60_000, help="transcript budget sent to the llm")
    d.add_argument("--llm-cmd", default="claude -p", help="headless command receiving the prompt as one arg")
    sub.add_parser("selftest")
    args = ap.parse_args(argv)
    return {"list": cmd_list, "digest": cmd_digest, "selftest": cmd_selftest}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
