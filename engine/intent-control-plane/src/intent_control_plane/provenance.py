"""Fix-commit provenance: SZZ linkage, JIT risk, and per-persona survival (Layer 0, AC-F1/F2/F3).

Feeds the company scorecard so a persona is graded on whether its work survives, not on lines
produced (LOC-as-productivity is a known-bad metric). Three established techniques, made pure and
testable: conventional-commit classification (feat/fix/refactor/chore), a Just-In-Time defect-risk
heuristic per diff (churn x spread x touched-file fix-density; Kamei 2013), and SZZ linkage
(Sliwerski-Zimmermann-Zeller 2005: attribute a fix back to the commits whose lines it changed) as a
confidence-weighted edge, not a hard claim. persona_provenance rolls commits up to rework ratio and
net (rework-adjusted) feature throughput. git_log is the one thin real-git reader.
"""
from __future__ import annotations

import math
import re
import subprocess
from pathlib import Path
from typing import Any

_CONVENTIONAL = re.compile(r"[(!:]")


def classify_commit(subject: str) -> str:
    """Classify a commit subject as fix / feat / refactor / chore / other (conventional + keywords)."""
    text = subject.strip().lower()
    head_type = _CONVENTIONAL.split(text, 1)[0].strip()
    if head_type in {"fix", "hotfix", "bugfix", "revert"} or text.startswith("revert"):
        return "fix"
    if head_type in {"feat", "feature"}:
        return "feat"
    if head_type in {"refactor", "perf"}:
        return "refactor"
    if head_type in {"chore", "docs", "test", "tests", "build", "ci", "style"}:
        return "chore"
    if any(keyword in text for keyword in ("hotfix", "correct", "revert", "bugfix")):
        return "fix"
    return "other"


def jit_risk(churn: int, files_touched: int, fix_density: float) -> float:
    """Heuristic defect-risk of a diff in [0, 1]: rises with churn, cross-file spread, and hotspot density.

    A saturating heuristic (not a trained model) because at this repo scale a heuristic beats an
    under-fit JIT classifier; it graduates to a learned model once enough labelled data accrues.
    """
    churn_term = 1.0 - math.exp(-max(0, churn) / 200.0)
    spread_term = 1.0 - math.exp(-max(0, files_touched - 1) / 5.0)
    score = 0.5 * churn_term + 0.3 * spread_term + 0.2 * max(0.0, min(1.0, fix_density))
    return round(max(0.0, min(1.0, score)), 4)


def szz_link(introducer_counts: dict[str, int]) -> list[dict[str, Any]]:
    """SZZ: given how many of a fix's lines each earlier commit owns, return confidence-weighted edges."""
    total = sum(introducer_counts.values())
    if total <= 0:
        return []
    ranked = sorted(introducer_counts.items(), key=lambda item: (-item[1], item[0]))
    return [{"sha": sha, "confidence": round(count / total, 4)} for sha, count in ranked]


def survival_rate(added: int, removed_later: int) -> float:
    """Fraction of added lines still alive: (added - removed_later) / added, clamped to [0, 1]."""
    if added <= 0:
        return 0.0
    return round(max(0.0, added - removed_later) / added, 4)


def persona_provenance(commits: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per-persona rollup: feat/fix counts, rework ratio, and net (rework-adjusted) feature throughput."""
    agg: dict[str, dict[str, int]] = {}
    for commit in commits:
        persona = str(commit.get("persona", "?"))
        kind = str(commit.get("kind", "other"))
        bucket = agg.setdefault(persona, {"n": 0, "feat": 0, "fix": 0, "caused_fix": 0})
        bucket["n"] += 1
        if kind == "feat":
            bucket["feat"] += 1
        if kind == "fix":
            bucket["fix"] += 1
        if commit.get("caused_fix"):
            bucket["caused_fix"] += 1
    out: dict[str, dict[str, Any]] = {}
    for persona, bucket in agg.items():
        n = bucket["n"]
        out[persona] = {
            **bucket,
            "rework_ratio": round(bucket["fix"] / n, 4) if n else 0.0,
            "net_feature_throughput": bucket["feat"] - bucket["caused_fix"],
        }
    return out


def parse_git_log(text: str) -> list[dict[str, Any]]:
    """Parse `git log --format=%H%x09%s` output (sha<TAB>subject per line) into classified commits."""
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 1)
        sha = parts[0].strip()
        subject = parts[1].strip() if len(parts) > 1 else ""
        if not sha:
            continue
        rows.append({"sha": sha, "subject": subject, "kind": classify_commit(subject)})
    return rows


def git_log(repo: Path, max_count: int = 200) -> list[dict[str, Any]]:
    """Thin real-git reader: the last max_count commits of repo as classified rows (empty on error)."""
    result = subprocess.run(
        ["git", "-C", str(repo), "log", f"-n{max_count}", "--format=%H%x09%s"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return parse_git_log(result.stdout)
