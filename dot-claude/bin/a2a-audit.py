#!/usr/bin/env python3
"""a2a-audit.py — append-only JSONL audit log for A2A calls.

Single source of truth at ~/.claude/cache/a2a/audit.jsonl. No sqlite tables
in v1 (per refined plan). Add tables only if querying becomes painful.

Usage as a module:
    from a2a_audit import log_call
    log_call(from_addr, to_addr, prompt_hash, duration_ms, state, conversation_id, **extra)

Usage as CLI (for shell bridges):
    a2a-audit.py log <from> <to> <prompt_hash> <duration_ms> <state> [<conversation_id>]
    a2a-audit.py tail [N]
    a2a-audit.py stats
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

AUDIT_DIR = Path.home() / ".claude" / "cache" / "a2a"
AUDIT_LOG = AUDIT_DIR / "audit.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def hash_prompt(prompt: str, length: int = 12) -> str:
    return hashlib.sha1(prompt.encode("utf-8", errors="replace")).hexdigest()[:length]


def log_call(
    from_addr: str,
    to_addr: str,
    prompt_hash: str,
    duration_ms: int,
    state: str,
    conversation_id: str | None = None,
    **extra,
) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": now_iso(),
        "from": from_addr,
        "to": to_addr,
        "prompt_hash": prompt_hash,
        "duration_ms": int(duration_ms),
        "state": state,
        "conversation_id": conversation_id,
        **extra,
    }
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def tail(n: int = 20) -> None:
    if not AUDIT_LOG.exists():
        print("(no audit log yet)")
        return
    lines = AUDIT_LOG.read_text().splitlines()[-n:]
    for line in lines:
        try:
            r = json.loads(line)
            print(f"{r['ts']}  {r['from']:30s} -> {r['to']:30s}  {r['state']:10s}  {r['duration_ms']:>6}ms  {r.get('prompt_hash','-')}")
        except Exception:
            print(line)


def stats() -> None:
    if not AUDIT_LOG.exists():
        print("(no audit log yet)")
        return
    by_pair: dict[tuple[str, str], dict] = {}
    by_state: dict[str, int] = {}
    for line in AUDIT_LOG.read_text().splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        key = (r["from"], r["to"])
        agg = by_pair.setdefault(key, {"count": 0, "total_ms": 0, "ok": 0, "fail": 0})
        agg["count"] += 1
        agg["total_ms"] += r.get("duration_ms", 0)
        if r.get("state") == "completed":
            agg["ok"] += 1
        else:
            agg["fail"] += 1
        by_state[r.get("state", "?")] = by_state.get(r.get("state", "?"), 0) + 1

    print(f"Total calls: {sum(a['count'] for a in by_pair.values())}\n")
    print("By state:")
    for s, n in sorted(by_state.items(), key=lambda x: -x[1]):
        print(f"  {s:15s} {n}")
    print("\nBy pair (count, ok/fail, avg_ms):")
    for (f, t), a in sorted(by_pair.items(), key=lambda x: -x[1]["count"]):
        avg = a["total_ms"] // a["count"] if a["count"] else 0
        print(f"  {f:30s} -> {t:30s}  count={a['count']:3d}  ok/fail={a['ok']}/{a['fail']}  avg={avg}ms")


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: a2a-audit.py {log|tail|stats} ...", file=sys.stderr)
        sys.exit(2)
    cmd = sys.argv[1]
    if cmd == "log":
        if len(sys.argv) < 7:
            print("usage: a2a-audit.py log <from> <to> <prompt_hash> <duration_ms> <state> [<conversation_id>]", file=sys.stderr)
            sys.exit(2)
        log_call(
            from_addr=sys.argv[2],
            to_addr=sys.argv[3],
            prompt_hash=sys.argv[4],
            duration_ms=int(sys.argv[5]),
            state=sys.argv[6],
            conversation_id=sys.argv[7] if len(sys.argv) > 7 else None,
        )
    elif cmd == "tail":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        tail(n)
    elif cmd == "stats":
        stats()
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
