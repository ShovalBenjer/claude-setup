"""Deterministic UserPromptSubmit router: keyword -> skills/persona + confidence nudge.

Pure decision logic extracted from ~/.claude/hooks/prompt-router.sh so the routing that
shapes every turn is golden-tested instead of embedded, untested python-in-bash. The hook
becomes a thin shim that runs `python -m intent_control_plane.harness.router`.

Split: route() and render_context() are pure (unit-tested); corpus_docs() is the only I/O
(a read-only FTS query against the local best-practices corpus); main() is the hook edge.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

CORPUS_DB = Path.home() / ".claude" / "corpus" / "best_practices.sqlite3"
SESSIONS_DB = Path.home() / ".claude" / "cache" / "sessions.db"

# keyword -> candidate skills (curated gastown routes; naming a skill is harmless even if
# not installed, so this never breaks).
ROUTES: list[tuple[str, list[str]]] = [
    (r"\b(deploy|prod|production|go live|redeploy)\b", ["prod-deploy-rules", "deploy-prod"]),
    (r"\b(commit|push|pr|pull request)\b", ["commit-push-pr", "refactor-pre-push"]),
    (r"\b(review|pre-?ship|before merge|is this good)\b", ["review", "code-review", "heidegger-reflect"]),
    (r"\b(test|tests|coverage|tdd|regression)\b", ["testing-pyramid", "tdd", "coverage-enforcer"]),
    (r"\b(eval|judge|smoke|nightly)\b", ["eval-runner"]),
    (r"\b(lint|format|boilerplate|docstring|scaffold|second opinion|mechanical|grunt)\b", ["codex-call"]),
    (r"\b(refactor|simplify|over-?engineer|bloat|clean ?up|ponytail)\b", ["ponytail", "code-simplifier", "ponytail-audit", "ponytail-review", "ponytail-help"]),
    (r"\b(spec|prd|requirement|acceptance|what are we building)\b", ["requirement-anchor", "to-prd", "premortem"]),
    (r"\b(azure|foundry|brn-azai|key ?vault|function app|web app)\b", ["azure-runtime", "azure-audit", "azure-keyvault-secrets"]),
    (r"\b(agent|seekapa|axiacs|copilot|m365)\b", ["agent-builder", "azure-runtime"]),
    (r"\b(jira|ticket|dev-\d+)\b", ["jira-read", "jira-task-draft"]),
    (r"\b(branch|pipeline|devops|\bado\b|merge)\b", ["azure-devops", "commit-push-pr"]),
    (r"\b(research|state of the art|sota|compare|deep dive)\b", ["deep-research", "decision-grade"]),
    (r"\b(ui|ux|frontend|dashboard|design|component)\b", ["ui-ux-pro-max", "frontend-design"]),
    (r"\b(pii|secret|redact|credential|compliance)\b", ["pii-scrubber"]),
    (r"\b(data|dataset|sql|query|analyze|csv|parquet)\b", ["context-bounded-analyst"]),
    (r"\b(voice|audio|narrat|tts)\b", ["voice-explainer"]),
    (r"\b(video|avatar|explainer)\b", ["visual-explainer"]),
    (r"\b(meeting|talked with|call with|note this)\b", ["meeting-notes"]),
    (r"\b(message|draft|reply|in my voice|blog|post)\b", ["shoval-voice-draft", "blog", "humanize"]),
    (r"\b(plan|design|architecture)\b", ["premortem", "request-refactor-plan", "domain-model"]),
    (r"\b(reground|resume|out of focus|lost|context drift|stale)\b", ["reground", "workspace-brain"]),
    (r"\b(ops status|what.?s running|kill stale|clean ?up|dead code|watchdog)\b", ["ops-status", "kill-stale", "cleanup-crew", "watchdog"]),
    (r"\b(dispatch|ask seekapa|ask axiacs|second opinion|delegate to)\b", ["dispatch"]),
    (r"\b(mutation|property test|fuzz|triage test|red[- ]?team|adversarial)\b", ["mutation-runner", "property-test-gen", "triage-tests", "red-team-review", "red-team"]),
    (r"\b(worth building|invest|feature value|liron lens)\b", ["feature-investor", "LTMD", "decision-grade"]),
    (r"\b(grill|stress-test|interview me|align the plan)\b", ["grill-me"]),
    (r"\b(end session|wrap up|handover)\b", ["end-session"]),
    (r"\b(connector|apify|scrape|browser|activate mcp)\b", ["mcp-activation", "apify-mcp", "web-inspect"]),
    (r"\b(tts|narration|voice over|elevenlabs)\b", ["elevenlabs-mcp"]),
    (r"\b(avatar|talking head|heygen|how-to video|art-direct)\b", ["heygen-mcp", "blonde-designer"]),
    (r"\b(who touched|stopped my|activity log|cert|ai-103)\b", ["azure-activity-watch", "azure-cert-coach"]),
    (r"\b(openai agent|assistant api|agentkit)\b", ["openai-agents"]),
    (r"\b(persona|meme|caveman|super saiyan|rasenshuriken|kyuubi|jedi|gandalf|thanos|lebowski|mossad|eretz)\b", ["persona", "meme-control"]),
    (r"\b(advice|advis|not sure|unsure|not confident|second opinion|latest release|current best practice|is this still true)\b|what.?s the sota", ["advisor", "deep-research"]),
]

# keyword -> owning gastown persona (route work through them; gastown-company-registry.md)
PERSONA_ROUTES: list[tuple[str, str]] = [
    (r"\b(deploy|prod|production|commit|push|pr|branch|pipeline|devops|merge|release)\b", "Release Bureau"),
    (r"\b(azure|foundry|brn-azai|key ?vault|function app|web app|cost)\b", "Azure Ops Utility"),
    (r"\b(seekapa|axiacs|copilot|m365|deployed agent)\b", "Runtime Agents Division"),
    (r"\b(test|tests|coverage|tdd|eval|mutation|regression|red[- ]?team)\b", "QA Lab"),
    (r"\b(review|pre-?ship|refactor|simplify|ponytail|over-?engineer|bloat|dead code)\b", "Review Board"),
    (r"\b(spec|prd|requirement|architecture|design|domain|ubiquitous)\b", "Architecture Office"),
    (r"\b(research|sota|state of the art|compare|decision|evidence|deep dive)\b", "Evidence Clerk"),
    (r"\b(ui|ux|frontend|dashboard|component|design system)\b", "Product Studio"),
    (r"\b(pii|secret|redact|credential|compliance|sensitive)\b", "Security and Compliance Office"),
    (r"\b(data|dataset|sql|query|analyze|csv|parquet|notebook)\b", "Data Bureau"),
    (r"\b(voice|audio|tts|video|avatar|explainer|narrat)\b", "Voice and Media Studio"),
    (r"\b(jira|ticket|message|draft|reply|blog|post|meeting|wiki)\b", "Communications Desk"),
    (r"\b(mcp|connector|apify|browser|web-inspect)\b", "MCP and Tooling Office"),
    (r"\b(reground|resume|context|state|memory|continuity|handoff)\b", "Workflow Clerk"),
    (r"\b(lint|format|boilerplate|docstring|scaffold|mechanical|grunt|implement)\b", "Engineering Firm"),
]

# uncertainty signals (en/he/ar): trigger the confidence-check injection.
LOW_CONF: tuple[str, ...] = (
    "i don't understand", "i dont understand", "don't understand", "dont understand",
    "i'm lost", "im lost", "not sure", "unsure", "not confident", "no idea", " idk",
    "confused", "confusing", "out of focus", "is this right", "am i right",
    "what should i", "help me understand", "i can't tell", "i cant tell", "i'm stuck",
    "im stuck", "which approach", "am i missing", "not clear to me", "no clue",
    "לא מבין", "לא מבינה", "אבוד", "אבודה", "לא בטוח", "לא בטוחה", "תקוע", "תקועה", "לא ברור",
    "مش فاهم", "لا أفهم", "مش متأكد", "لست متأكد", "تائه", "ضايع",
)

DISCIPLINE_LINES = [
    "- if substantive: anchor the spec/PRD as the control plane (requirement-anchor), "
    "state the goal + stop-condition, then TDD in vertical slices.",
    "- before commit: /simplify or /ponytail the changed files; never claim done "
    "without real command output.",
    "- delegate junior/mechanical work (lint-fix, boilerplate tests, docstrings, "
    "diff second-opinion) to Codex via codex-call, read-only for review; verify its output.",
]

CONFIDENCE_LINES = [
    "",
    "CONFIDENCE CHECK (uncertainty detected -- reground before acting, do not guess):",
    "- how we operate: rtk-first Bash; uv (Python) / bun (JS); TDD vertical slices, no "
    "mocks, verify with real output; PRD/spec is the control plane (anchor before "
    "building); ponytail before commit; no em-dash/emoji/slop; Codex executes, Claude "
    "orchestrates; destructive ops need explicit per-action OK.",
    "- local uncertainty (branch/state/spec/artifact unclear): run /reground lite first.",
    "- external uncertainty (SOTA, current facts, a release, unfamiliar tech): run "
    "/advisor -- it web-researches trusted, same-day, peer-reviewed/primary sources and "
    "returns a dated recommendation with confidence.",
]


def routed_skill_names() -> set[str]:
    """Every skill the router can surface: the union of all ROUTES skill lists.

    The authoritative answer to "is this skill reachable", used by the self-improve
    reachability check instead of scraping a source file for quoted tokens.
    """
    return {skill for _, skills in ROUTES for skill in skills}


def get_prompt(payload: dict[str, Any]) -> str:
    for key in ("prompt", "user_prompt", "message", "text"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return ""


def route(prompt_raw: str) -> dict[str, Any] | None:
    """Pure decision. Returns {hits, personas, low_conf} or None when the router stays silent."""
    p = prompt_raw.strip().lower()
    if not p:
        return None
    hits: list[str] = []
    for pat, skills in ROUTES:
        if re.search(pat, p):
            for skill in skills:
                if skill not in hits:
                    hits.append(skill)
    personas: list[str] = []
    for pat, persona in PERSONA_ROUTES:
        if re.search(pat, p) and persona not in personas:
            personas.append(persona)
    if not personas:
        personas = ["Mayor Opus"]
    low_conf = any(t in p for t in LOW_CONF)
    substantive = len(p.split()) >= 12 or "\n" in prompt_raw
    if not hits and not substantive and not low_conf:
        return None
    return {"hits": hits, "personas": personas, "low_conf": low_conf}


def _clean_snippet(text: str, limit: int = 200) -> str:
    """Collapse whitespace and strip em/en dashes from a corpus excerpt.

    The snippet is injected into agent context, so it obeys the no-dash output rule:
    em/en dashes become a comma. Capped so a preview stays a preview.
    """
    collapsed = re.sub(r"\s+", " ", text or "").strip()
    collapsed = collapsed.replace("—", ", ").replace("–", ", ")  # noqa: RUF001 - these ARE what it scrubs
    collapsed = re.sub(r"\s+", " ", collapsed).strip()
    return collapsed[:limit].rstrip()


def corpus_snippets(
    prompt_lower: str, db_path: Path = CORPUS_DB, limit: int = 3
) -> list[dict[str, str]]:
    """I/O: top ~/docs matches as {name, path, snippet} from the read-only FTS index.

    Returns up to `limit` deduped hits, each with the full path and a short content preview
    (FTS5 snippet over the chunk text), so the agent sees what the file says and where it is,
    not only its name. Fails closed to [] if the DB is unreachable or the query errors.
    """
    try:
        words = re.findall(r"[a-zA-Z][a-zA-Z0-9-]{3,}", prompt_lower)[:8]
        if not words:
            return []
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        rows = conn.execute(
            "select c.locator, snippet(corpus_fts, 3, '', '', ' ... ', 15) "
            "from corpus_fts join chunks c on c.id = corpus_fts.chunk_id "
            "where corpus_fts match ? and c.source_id = 'local-shoval-docs' "
            "order by rank limit 24",
            (" OR ".join(words),),
        ).fetchall()
        conn.close()
        hits: list[dict[str, str]] = []
        seen: set[str] = set()
        for locator, snippet in rows:
            name = (locator or "").split("/")[-1]
            if name and name not in seen:
                seen.add(name)
                hits.append(
                    {"name": name, "path": locator or "", "snippet": _clean_snippet(snippet)}
                )
            if len(hits) >= limit:
                break
        return hits
    except Exception:
        return []


def corpus_docs(prompt_lower: str, db_path: Path = CORPUS_DB) -> list[str]:
    """Back-compat: just the matched filenames, derived from corpus_snippets."""
    return [hit["name"] for hit in corpus_snippets(prompt_lower, db_path)]


def skill_usage_counts(db_path: Path = SESSIONS_DB) -> dict[str, int]:
    """I/O: {skill_name: invocation_count} from sessions.db session_events (skill_invoke).

    The `detail` column holds the skill name. Fails closed to {} if the DB or table is
    unreachable, so ranking degrades to the router's own order.
    """
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        rows = conn.execute(
            "select detail, count(*) from session_events "
            "where event_type = 'skill_invoke' and detail is not null "
            "group by detail"
        ).fetchall()
        conn.close()
        return {str(name): int(n) for name, n in rows}
    except Exception:
        return {}


def rank_by_usage(candidates: list[str], usage_counts: dict[str, int]) -> list[str]:
    """Order candidates by measured invocation count (desc), preserving router order on ties.

    Skills with no recorded usage keep their original relative order behind used ones.
    Empty usage_counts is the identity (candidates unchanged), so an unpopulated telemetry
    table degrades to the router's ordering instead of shuffling it.
    """
    return sorted(
        candidates,
        key=lambda skill: (-usage_counts.get(skill, 0), candidates.index(skill)),
    )


def render_context(
    decision: dict[str, Any], docs: list[str], snippets: list[dict[str, str]] | None = None
) -> str:
    """Pure: assemble the additionalContext text from a decision plus retrieved docs.

    docs is the filename list (which file to open); snippets, when present, adds a
    content preview per doc so the ranked corpus text reaches the model, not just a name.
    """
    hits = decision["hits"]
    personas = decision["personas"]
    lines = ["TASK ROUTER (deterministic nudge; use what fits, ignore if trivial):"]
    lines.append(
        "- owning persona(s): " + ", ".join(personas[:3]) + " (route work through them, gastown registry)"
    )
    if hits:
        lines.append("- candidate skills: " + ", ".join(hits[:8]))
    if docs:
        lines.append("- relevant docs (corpus, ~/docs): " + ", ".join(docs))
    if snippets:
        lines.append("- doc previews (open the file for full text):")
        lines.extend(f"    {hit['name']}: {hit['snippet']}" for hit in snippets[:3])
    lines.extend(DISCIPLINE_LINES)
    if decision["low_conf"]:
        lines.extend(CONFIDENCE_LINES)
    return "\n".join(lines)


def build_context(
    prompt_raw: str, db_path: Path = CORPUS_DB, usage_db: Path = SESSIONS_DB
) -> str | None:
    """Full pipeline: decide, rank skills by measured usage, retrieve snippets, render.

    None means stay silent. Candidate skills are reordered by real invocation counts so
    the nudge leads with what actually gets used, not a hand-keyed list order.
    """
    decision = route(prompt_raw)
    if decision is None:
        return None
    decision["hits"] = rank_by_usage(decision["hits"], skill_usage_counts(usage_db))
    snippets = corpus_snippets(prompt_raw.strip().lower(), db_path)
    docs = [hit["name"] for hit in snippets]
    return render_context(decision, docs, snippets)


def main() -> int:
    """Hook edge: read HOOK_INPUT, emit the UserPromptSubmit additionalContext JSON."""
    if os.environ.get("CLAUDE_LOOP_MODE") or os.environ.get("CODEX_AUTOMATION_ID"):
        print("{}")
        return 0
    try:
        payload = json.loads(os.environ.get("HOOK_INPUT", "{}") or "{}")
    except Exception:
        payload = {}
    ctx = build_context(get_prompt(payload))
    if ctx is None:
        print("{}")
        return 0
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ctx}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
