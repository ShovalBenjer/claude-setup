"""Control tower: a live, spawnable TUI over the harness and project-estate state.

Composes the existing data functions (dashboard.a2a_usage / intent_health,
standards.score_projects, delegation.build_queue) with new pure data functions
(sessions/worktrees, orchestration telemetry, deployed-endpoint surface) into one view.
Renders with rich when it is importable (the launcher's system python3 has it); falls back
to plain text otherwise, the same idiom dashboard.py already uses, so the `uv run` test/lint
environment (no rich dependency declared in pyproject.toml) still runs clean.

Fixes the stale-cache bug in dashboard.py's scorecard panel (a `docs/project-scorecard-*.md`
snapshot showing a 5-dim /14 table): the scorecard panel here always calls
`standards.score_projects()` live, which scores all six dimensions (/17).

Run once (default): `python -m intent_control_plane.tower --once`
Run live:            `python -m intent_control_plane.tower --watch [secs]`  (default 5s, Ctrl-C to exit)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from intent_control_plane import dashboard, delegation, session_guard, standards

PROJECTS_ROOT = Path.home() / "projects"
TELEMETRY_LOG = Path.home() / ".claude" / "cache" / "orchestration" / "telemetry.jsonl"
FOUNDRY_RULE = Path.home() / ".claude" / "rules" / "foundry-deployment-per-project.md"

# Cost-bounded Foundry eval judges (see CLAUDE.md "Active project context").
FOUNDRY_JUDGES = ("grok-4-1-fast-reasoning-2-eval", "DeepSeek-V3.2")

# Documented fallback if FOUNDRY_RULE is missing or has no matching deployment names.
DEFAULT_DEPLOYMENTS = (
    "gpt-5.4-nano-cs-agent",
    "gpt-5.4-mini-qc-api-telephony",
    "gpt-5.4-mini-training",
    "gpt-5.4-nano-call-analysis-agent",
)

_DEPLOYMENT_PATTERN = re.compile(r"`(gpt-[\w.-]+)`")


# --------------------------------------------------------------------------------------------
# Pure data functions
# --------------------------------------------------------------------------------------------


def parse_git_worktree_porcelain(lines: list[str]) -> list[dict[str, Any]]:
    """Pure: parse `git worktree list --porcelain` output into worktree records.

    Each record is `{"worktree", "head", "branch", "repo"}`. `repo` is the basename of the
    worktree's OWN path (the literal checked-out directory), not the repo that was queried:
    a repo family with linked worktrees (e.g. ORM-AGENT plus its `-wt` siblings) reports
    several distinct paths from one invocation, and each is its own working copy for
    session-tracking purposes. `head` is the short (8-char) sha. `branch` is the local
    branch name with the `refs/heads/` prefix stripped, or `"(detached)"` / `"(bare)"`.
    """
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for raw in lines:
        line = raw.rstrip("\n")
        if not line.strip():
            if current:
                entries.append(current)
                current = {}
            continue
        if line.startswith("worktree "):
            if current:
                entries.append(current)
            current = {"worktree": line[len("worktree "):].strip()}
        elif line.startswith("HEAD "):
            current["head"] = line[len("HEAD "):].strip()[:8]
        elif line.startswith("branch "):
            ref = line[len("branch "):].strip()
            current["branch"] = ref[len("refs/heads/"):] if ref.startswith("refs/heads/") else ref
        elif line == "detached":
            current["branch"] = "(detached)"
        elif line == "bare":
            current["branch"] = "(bare)"
    if current:
        entries.append(current)
    for entry in entries:
        entry.setdefault("head", "")
        entry.setdefault("branch", "?")
        entry["repo"] = Path(entry["worktree"]).name if entry.get("worktree") else "?"
    return entries


def telemetry_summary(lines: list[str]) -> dict[str, Any]:
    """Pure: per-strategy aggregation of `orchestration/telemetry.jsonl` lines.

    Each output bucket is `{"count", "avg_subagent_tokens", "avg_duration_ms", "pass_rate"}`.
    `avg_duration_ms` averages only over rows carrying a numeric duration (a `null` duration,
    e.g. a "solo" inline-lead row, is excluded rather than treated as zero). `pass_rate` is
    the fraction of rows with `status == "green"`. Malformed JSON lines and blank lines are
    skipped, not fatal.
    """
    buckets: dict[str, dict[str, Any]] = {}
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue  # valid JSON but wrong shape (list/number/string) is not a telemetry row
        strategy = str(row.get("strategy", "?"))
        bucket = buckets.setdefault(
            strategy, {"count": 0, "tokens_sum": 0.0, "duration_sum": 0.0, "duration_n": 0, "pass": 0}
        )
        bucket["count"] += 1
        tokens = row.get("subagent_tokens")
        if isinstance(tokens, int | float):
            bucket["tokens_sum"] += tokens
        duration = row.get("duration_ms")
        if isinstance(duration, int | float):
            bucket["duration_sum"] += duration
            bucket["duration_n"] += 1
        if str(row.get("status", "")) == "green":
            bucket["pass"] += 1
    out: dict[str, dict[str, Any]] = {}
    for strategy, bucket in buckets.items():
        count = bucket["count"]
        out[strategy] = {
            "count": count,
            "avg_subagent_tokens": round(bucket["tokens_sum"] / count, 1) if count else 0.0,
            "avg_duration_ms": (
                round(bucket["duration_sum"] / bucket["duration_n"], 1) if bucket["duration_n"] else None
            ),
            "pass_rate": round(bucket["pass"] / count, 3) if count else 0.0,
        }
    return out


def parse_deployment_names(text: str) -> list[str]:
    """Pure: pull backtick-quoted `` `gpt-...` `` deployment names out of markdown.

    Order-preserving, deduplicated. Only names starting with `gpt-` match (the rule doc's
    other backtick spans are file paths, flags, and non-gpt model names).
    """
    names: list[str] = []
    seen: set[str] = set()
    for match in _DEPLOYMENT_PATTERN.finditer(text):
        name = match.group(1)
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


# Context-rot thresholds (doc: effectiveness degrades past ~100-120k tokens; hard zone past ~160k).
CONTEXT_ROT_TOKENS = 100_000
CONTEXT_HARD_TOKENS = 160_000


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token. A floor, not exact."""
    return len(text or "") // 4


def context_budget_band(est_tokens: int) -> str:
    """Degradation band for an estimated context size: green < 100k <= amber < 160k <= red."""
    if est_tokens < CONTEXT_ROT_TOKENS:
        return "green"
    if est_tokens < CONTEXT_HARD_TOKENS:
        return "amber"
    return "red"


def summarize_turns(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Pure: the latest session's turn count + estimated context tokens + degradation band.

    A 'turn' is a `user_prompt` event. `est_tokens` sums estimate_tokens over the session's
    logged event text only (~4 chars/token), so it is a lower bound (it does not see tool
    output) and reads as a floor, not an exact context size. Empty rows give a zeroed green
    meter. The latest session is the session_id of the most recent row by timestamp.
    """
    if not rows:
        return {"session": None, "turns": 0, "est_tokens": 0, "band": "green"}
    latest = max(rows, key=lambda r: str(r.get("timestamp_utc") or ""))
    session = latest.get("session_id")
    session_rows = [r for r in rows if r.get("session_id") == session]
    turns = sum(1 for r in session_rows if str(r.get("event_type")) == "user_prompt")
    est = sum(estimate_tokens(str(r.get("model_text") or "")) for r in session_rows)
    return {"session": session, "turns": turns, "est_tokens": est, "band": context_budget_band(est)}


# --------------------------------------------------------------------------------------------
# Thin impure wrappers (isolated shell/DB calls, kept out of the pure parsers above)
# --------------------------------------------------------------------------------------------


def _git_worktree_list(repo_dir: Path) -> list[str]:
    """Impure: `git worktree list --porcelain` for one repo dir, [] on any failure."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_dir), "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return []
    if result.returncode != 0:
        return []
    return result.stdout.splitlines()


def sessions_panel_data(projects_root: Path = PROJECTS_ROOT) -> dict[str, Any]:
    """Live claude/codex sessions plus worktrees across every repo under `projects_root`.

    `other_sessions` reuses `session_guard._live_other_sessions()` (None if detection could
    not run). Worktree entries are deduped by their own path: a repo family with linked
    worktrees reports the identical set from any one of its checkouts, so scanning each
    top-level dir independently would otherwise duplicate rows.
    """
    other = session_guard._live_other_sessions()
    worktrees: dict[str, dict[str, Any]] = {}
    try:
        repo_dirs = [d for d in sorted(projects_root.iterdir()) if d.is_dir() and (d / ".git").exists()]
    except OSError:
        repo_dirs = []
    for repo_dir in repo_dirs:
        for entry in parse_git_worktree_porcelain(_git_worktree_list(repo_dir)):
            worktrees[entry["worktree"]] = entry
    return {
        "own_pid": os.getpid(),
        "other_sessions": other,
        "worktrees": sorted(worktrees.values(), key=lambda e: e["repo"]),
    }


def endpoints_panel_data(
    rule_path: Path = FOUNDRY_RULE, audit_path: Path = dashboard.A2A_AUDIT
) -> dict[str, Any]:
    """Deployed-endpoint surface: Foundry eval judges, per-project deployments, Codex a2a volume.

    Reads deployment names from `rule_path` (the foundry-deployment-per-project rule doc) when
    present and parseable; falls back to `DEFAULT_DEPLOYMENTS` otherwise. Reuses
    `dashboard.a2a_usage()` for the Codex call count rather than re-parsing the audit ledger.
    """
    deployments: list[str] = []
    try:
        text = rule_path.read_text(errors="ignore")
        deployments = parse_deployment_names(text)
    except OSError:
        deployments = []
    if not deployments:
        deployments = list(DEFAULT_DEPLOYMENTS)
    return {
        "judges": list(FOUNDRY_JUDGES),
        "deployments": deployments,
        "codex_a2a_calls": dashboard.a2a_usage(audit_path)["total"],
    }


def _proof_satisfied_count(db: Path = dashboard.INTENT_DB) -> int:
    """Cheap count of evidence rows whose proof is satisfied (`status == 'pass'`)."""
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    except sqlite3.Error:
        return 0
    try:
        row = conn.execute("select count(*) from evidence where status = 'pass'").fetchone()
        return int(row[0]) if row else 0
    except sqlite3.Error:
        return 0
    finally:
        conn.close()


def context_meter_data(db: Path = dashboard.INTENT_DB) -> dict[str, Any]:
    """Latest session's turns + estimated context tokens + degradation band (read-only)."""
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "select session_id, timestamp_utc, event_type, model_text from events"
        ).fetchall()
        conn.close()
    except sqlite3.Error:
        return summarize_turns([])
    return summarize_turns([dict(r) for r in rows])


# --------------------------------------------------------------------------------------------
# Data collection (one fresh snapshot per render, so --watch shows live state)
# --------------------------------------------------------------------------------------------


def _collect() -> dict[str, Any]:
    try:
        records = standards.score_projects(PROJECTS_ROOT)
    except OSError:
        records = []  # missing/unreadable ~/projects degrades to empty, like the other collectors
    try:
        telemetry_lines = TELEMETRY_LOG.read_text(errors="ignore").splitlines()
    except OSError:
        telemetry_lines = []
    return {
        "sessions": sessions_panel_data(PROJECTS_ROOT),
        "a2a": dashboard.a2a_usage(),
        "health": dashboard.intent_health(),
        "proof_satisfied": _proof_satisfied_count(),
        "records": records,
        "telemetry": telemetry_summary(telemetry_lines),
        "queue": delegation.build_queue(records)[:5],
        "endpoints": endpoints_panel_data(),
        "context_meter": context_meter_data(),
    }


# --------------------------------------------------------------------------------------------
# Rendering: rich if importable, plain text otherwise (same idiom as dashboard.py)
# --------------------------------------------------------------------------------------------


def _rich_components() -> dict[str, Any] | None:
    try:
        from rich import box
        from rich.console import Console, Group
        from rich.panel import Panel
        from rich.table import Table
    except ImportError:
        return None
    return {"box": box, "Console": Console, "Group": Group, "Panel": Panel, "Table": Table}


def _build_group(data: dict[str, Any]) -> Any:
    """Build one rich `Group` of all eight panels, or None if rich is not importable."""
    c = _rich_components()
    if c is None:
        return None
    box, Group, Panel, Table = c["box"], c["Group"], c["Panel"], c["Table"]
    panels = []

    # (a) Sessions & worktrees + guard state
    sessions = data["sessions"]
    sess_table = Table(box=box.SIMPLE)
    for col in ("Repo", "Branch", "HEAD", "Path"):
        sess_table.add_column(col)
    for wt in sessions["worktrees"]:
        sess_table.add_row(wt["repo"], wt["branch"], wt["head"], wt["worktree"])
    guard_note = f"own pid {sessions['own_pid']} | other live claude/codex sessions: {sessions['other_sessions']}"
    panels.append(Panel(Group(guard_note, sess_table), title="Sessions & Worktrees", border_style="blue"))

    # (b) Codex / a2a usage (reuses dashboard.a2a_usage)
    a2a = data["a2a"]
    usage = Table(box=box.SIMPLE, show_header=False)
    usage.add_row("Codex calls (total)", str(a2a["total"]))
    usage.add_row("completed", str(a2a["completed"]))
    usage.add_row("failed", f"{a2a['failed']} ({int(a2a['fail_rate'] * 100)}%)")
    usage.add_row("by state", ", ".join(f"{k}:{v}" for k, v in a2a["by_state"].items()) or "-")
    usage.add_row("recent days", ", ".join(f"{k[5:]}:{v}" for k, v in list(a2a["by_day"].items())[-6:]) or "-")
    panels.append(Panel(usage, title="Codex / a2a usage", border_style="cyan"))

    # (c) Intent plane health + proof-satisfied (reuses dashboard.intent_health)
    hp = Table(box=box.SIMPLE, show_header=False)
    for key, val in data["health"].items():
        hp.add_row(key, str(val))
    hp.add_row("proof_satisfied (evidence pass)", str(data["proof_satisfied"]))
    panels.append(Panel(hp, title="Intent plane health", border_style="green"))

    # (d) LIVE estate scorecard (reuses standards.score_projects; six dims, /17)
    score_table = Table(box=box.SIMPLE)
    for col in ("Project", "Class", *standards.DIMENSIONS, "Score"):
        score_table.add_column(col)
    for r in data["records"]:
        cells = [f"{r['dimensions'][d]['passed']}/{r['dimensions'][d]['total']}" for d in standards.DIMENSIONS]
        score_table.add_row(r["name"], r["class"], *cells, r["score"])
    panels.append(Panel(score_table, title="Estate standards scorecard (live)", border_style="magenta"))

    # (e) Orchestration telemetry
    telem_table = Table(box=box.SIMPLE)
    for col in ("Strategy", "Count", "Avg subagent tokens", "Avg duration ms", "Pass rate"):
        telem_table.add_column(col)
    for strategy, stats in sorted(data["telemetry"].items()):
        telem_table.add_row(
            strategy,
            str(stats["count"]),
            str(stats["avg_subagent_tokens"]),
            str(stats["avg_duration_ms"]),
            f"{int(stats['pass_rate'] * 100)}%",
        )
    panels.append(Panel(telem_table, title="Orchestration telemetry", border_style="yellow"))

    # (f) Delegation queue, top 5 (reuses delegation.build_queue)
    queue_table = Table(box=box.SIMPLE)
    for col in ("Repo", "Dimension", "Priority", "Failing checks"):
        queue_table.add_column(col)
    for item in data["queue"]:
        queue_table.add_row(item["repo"], item["dimension"], str(item["priority"]), ", ".join(item["failing_checks"]))
    panels.append(Panel(queue_table, title="Delegation queue (top 5)", border_style="red"))

    # (g) Deployed endpoints
    endpoints = data["endpoints"]
    ep_table = Table(box=box.SIMPLE, show_header=False)
    ep_table.add_row("Eval judges", ", ".join(endpoints["judges"]))
    ep_table.add_row("Deployments", ", ".join(endpoints["deployments"]))
    ep_table.add_row("Codex a2a calls", str(endpoints["codex_a2a_calls"]))
    panels.append(Panel(ep_table, title="Deployed endpoints", border_style="white"))

    # (h) Context-degradation meter (turns + estimated tokens vs the context-rot threshold)
    meter = data["context_meter"]
    band_style = {"green": "green", "amber": "yellow", "red": "red"}[meter["band"]]
    m_table = Table(box=box.SIMPLE, show_header=False)
    m_table.add_row("session", str(meter["session"] or "-"))
    m_table.add_row("turns (user prompts)", str(meter["turns"]))
    m_table.add_row("est context tokens (floor)", f"{meter['est_tokens'] // 1000}k")
    m_table.add_row("band", meter["band"].upper() + " (rot >100k, hard >160k)")
    panels.append(Panel(m_table, title="Context-degradation meter", border_style=band_style))

    return Group(*panels)


def _render_plain(data: dict[str, Any]) -> None:
    """Plain-text fallback for all eight sections (no rich importable)."""
    print("== Sessions & Worktrees ==")
    print(json.dumps(data["sessions"], indent=2))
    print("== Codex / a2a usage ==")
    print(json.dumps(data["a2a"], indent=2))
    print("== Intent plane health ==")
    health = dict(data["health"])
    health["proof_satisfied"] = data["proof_satisfied"]
    print(json.dumps(health, indent=2))
    print("== Estate standards scorecard (live) ==")
    print(standards.render_markdown(data["records"]))
    print("== Orchestration telemetry ==")
    print(json.dumps(data["telemetry"], indent=2))
    print("== Delegation queue (top 5) ==")
    print(delegation.render_queue(data["queue"]))
    print("== Deployed endpoints ==")
    print(json.dumps(data["endpoints"], indent=2))
    print("== Context-degradation meter ==")
    print(json.dumps(data["context_meter"], indent=2))


def render_once(console: Any = None) -> None:
    """Render all eight panels once: rich Panels/Tables if importable, plain text otherwise."""
    data = _collect()
    c = _rich_components()
    if c is None:
        _render_plain(data)
        return
    con = console if console is not None else c["Console"]()
    con.print(_build_group(data))


# --------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(prog="tower")
    parser.add_argument("--once", action="store_true", help="render once and exit (default)")
    parser.add_argument(
        "--watch",
        nargs="?",
        const=5,
        type=int,
        default=None,
        metavar="SECS",
        help="live refresh loop every N seconds (default 5), Ctrl-C to exit",
    )
    args = parser.parse_args(argv)

    if args.watch is not None and args.watch <= 0:
        parser.error("--watch interval must be a positive integer (seconds)")

    if args.watch is None:
        render_once()
        return 0

    c = _rich_components()
    if c is None:
        # No live refresh without rich; fall back to one plain render.
        _render_plain(_collect())
        return 0

    from rich.live import Live

    con = c["Console"]()
    interval = args.watch
    try:
        with Live(_build_group(_collect()), console=con, refresh_per_second=1) as live:
            while True:
                time.sleep(interval)
                live.update(_build_group(_collect()))
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
