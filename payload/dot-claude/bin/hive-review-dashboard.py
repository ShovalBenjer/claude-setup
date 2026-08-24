#!/usr/bin/env python3
from __future__ import annotations

import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path


HOME = Path.home()
DB = HOME / ".hive" / "beads.db"
OUT = HOME / ".claude" / "docs" / "HIVE_REVIEW_PICKUP_STATUS.md"
RIGS = {
    "cs-agent": HOME / "projects" / "axia-seekapa-cs-agents",
    "qc-telephony-api": HOME / "projects" / "qc-telephony-api",
    "video-understanding": HOME / "projects" / "video-understanding",
    "campaign-analysis": HOME / "projects" / "campaign-analysis",
    "seekapa-training-platform": HOME / "projects" / "seekapa-training-platform",
    "ORM-AGENT": HOME / "projects" / "ORM-AGENT",
}


def rows(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def git_log(repo: Path, since: str) -> list[str]:
    if not (repo / ".git").exists():
        return []
    cmd = [
        "git",
        "-C",
        str(repo),
        "log",
        f"--since={since}",
        "--date=short",
        "--pretty=format:%h %ad %s",
        "--max-count=12",
    ]
    proc = subprocess.run(cmd, check=False, text=True, capture_output=True)
    if proc.returncode != 0:
        return [f"git log unavailable: {proc.stderr.strip()}"]
    return [line for line in proc.stdout.splitlines() if line.strip()]


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    status_counts = rows("select status,count(*) as n from beads group by status order by status")
    recent = rows(
        """
        select id,status,priority,rig,title,claimed_by,evidence_url,created_at,updated_at
        from beads
        order by updated_at desc, id desc
        limit 40
        """
    )
    stale_dupes = rows(
        """
        select rig, lower(title) as title_key, count(*) as n, group_concat(id) as ids
        from beads
        where status = 'open'
        group by rig, lower(title)
        having count(*) > 1
        order by n desc, rig
        limit 30
        """
    )
    claimed = rows(
        """
        select id,status,priority,rig,title,claimed_by,evidence_url,updated_at
        from beads
        where status = 'claimed'
        order by updated_at desc, id desc
        """
    )

    lines = [
        "# HIVE_REVIEW_PICKUP_STATUS",
        "",
        f"Generated UTC: `{now}`",
        "",
        "## Summary",
        "",
        "| Status | Count |",
        "|---|---:|",
    ]
    for row in status_counts:
        lines.append(f"| {row['status']} | {row['n']} |")

    lines += [
        "",
        "## Claimed Work",
        "",
        "| Bead | Priority | Rig | Claimed By | Evidence | Title |",
        "|---:|---|---|---|---|---|",
    ]
    if claimed:
        for row in claimed:
            evidence = row["evidence_url"] or ""
            lines.append(
                f"| {row['id']} | {row['priority']} | {row['rig']} | {row['claimed_by'] or ''} | {evidence} | {row['title']} |"
            )
    else:
        lines.append("|  |  |  |  |  | No claimed beads. |")

    lines += [
        "",
        "## Recent Bead Movement",
        "",
        "| Bead | Status | Priority | Rig | Updated | Evidence | Title |",
        "|---:|---|---|---|---|---|---|",
    ]
    for row in recent:
        lines.append(
            f"| {row['id']} | {row['status']} | {row['priority']} | {row['rig']} | {row['updated_at']} | {row['evidence_url'] or ''} | {row['title']} |"
        )

    lines += [
        "",
        "## Duplicate Open-Bead Candidates",
        "",
        "| Rig | Count | Beads | Title |",
        "|---|---:|---|---|",
    ]
    if stale_dupes:
        for row in stale_dupes:
            lines.append(f"| {row['rig']} | {row['n']} | {row['ids']} | {row['title_key']} |")
    else:
        lines.append("|  |  |  | No exact-title duplicate open beads. |")

    lines += [
        "",
        "## Recent Commits Since Latest Review",
        "",
    ]
    for rig, repo in RIGS.items():
        lines.append(f"### {rig}")
        log = git_log(repo, "2026-06-24 13:30 UTC")
        if log:
            lines.extend(f"- `{line}`" for line in log)
        else:
            lines.append("- No commits found or repo missing.")
        lines.append("")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(str(OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
