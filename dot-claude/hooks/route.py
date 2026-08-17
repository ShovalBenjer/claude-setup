#!/usr/bin/env python3
"""Name the persona and the skills a prompt belongs to, on every turn.

WHAT WAS ALREADY HERE AND WHY IT NEVER RAN.

`~/.claude/rules/gastown-company-registry.md` defines 19 personas owning 99 skills and
says, in its own operating flow, "Mayor Opus classifies the user's task ... Mayor selects
company personas and their owned skills." Measured 2026-08-05: across 66 transcripts,
**0 of 19 personas has ever been spawned.** Every delegation went to `general-purpose`
(23) or `Explore` (5). The registry is not even loaded: `~/.claude/CLAUDE.md` is 72 lines
and never mentions it, and imports no rules file, so a model sees it only by going to
look.

The routing half was designed and shipped as dead code. `dot-claude/hooks/prompt-router.sh`
is a 13-line shim onto `intent_control_plane.harness.router`, whose docstring calls itself
"the routing that shapes every turn". It is absent from `~/.claude/hooks/`, absent from
settings.json, and arrived in a single import commit. Its dependency
`~/.claude/corpus/best_practices.sqlite3` does not exist on this machine.

WHY THIS IS A REWRITE AND NOT A REVIVAL.

`tools/intent/capture_turn.py` already proves the ICP path is dead. It runs on every
UserPromptSubmit and its `enrich()` begins `from intent_control_plane.cli import ...`,
inside a bare `except Exception: pass`. `python3 -c "import intent_control_plane"` raises
ModuleNotFoundError here, so that import has failed silently on all 401 recorded turns.
Reviving a path whose failure mode is invisible would add a second silent failure to the
first.

So: stdlib only, no package, no sqlite, no corpus. The ROUTES table is ported verbatim
from router.py because it is curated and good; what is dropped is `corpus_docs()`, the
only I/O it had.

WHY THIS ONE CAN ACTUALLY REFINE A PROMPT.

A UserPromptSubmit hook alters a turn by PRINTING. That is the whole mechanism.
`capture_turn.py` writes nothing to stdout, which is why 401 captured turns changed
nothing about any turn: grep its 198 lines for `print(` and there is one hit, and it is
`json.dumps` into a variable. This file prints `hookSpecificOutput.additionalContext`,
which is the documented way to add context to the turn that is about to run.

WHAT IT DELIBERATELY DOES NOT DO.

It does not spawn anything and it does not rewrite the operator's words. It names what
the registry already says owns this kind of work, and records the naming so "which
persona handled this" becomes a query instead of a guess. Spawning is the model's call
with the Agent tool, and a hook that tried to force it would be making a routing decision
with none of the context the model has.

    echo '{"prompt":"review this before we merge"}' | python3 tools/intent/route.py
    python3 tools/intent/route.py --explain "deploy to prod"
    python3 tools/intent/route.py --selftest
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

REPO = Path(os.environ.get("CLAUDE_OS_DIR") or str(Path.home() / "claude-setup")).expanduser()
REGISTRY = Path.home() / ".claude" / "rules" / "gastown-company-registry.md"
LEDGER = REPO / "state" / "routing.jsonl"

# Ported verbatim from intent_control_plane/harness/router.py. Naming a skill that is not
# installed is harmless: the point is the persona it implies, and skills_sync.py already
# measures the installed estate separately.
ROUTES: list[tuple[str, list[str]]] = [
    (r"\b(deploy|prod|production|go live|redeploy)\b", ["prod-deploy-rules", "deploy-prod"]),
    (r"\b(commit|push|pr|pull request)\b", ["commit-push-pr", "refactor-pre-push"]),
    (r"\b(review|pre-?ship|before merge|is this good)\b", ["review", "heidegger-reflect"]),
    (r"\b(test|tests|coverage|tdd|regression)\b", ["testing-pyramid", "tdd", "coverage-enforcer"]),
    (r"\b(eval|judge|smoke|nightly)\b", ["eval-runner"]),
    (r"\b(lint|format|boilerplate|docstring|scaffold|mechanical|grunt)\b", ["codex-call"]),
    (r"\b(refactor|simplify|over-?engineer|bloat|clean ?up|ponytail)\b",
     ["ponytail", "code-simplifier"]),
    (r"\b(spec|prd|requirement|acceptance|what are we building)\b",
     ["requirement-anchor", "to-prd", "premortem"]),
    (r"\b(azure|foundry|brn-azai|key ?vault|function app|web app)\b",
     ["azure-runtime", "azure-audit"]),
    (r"\b(jira|ticket|dev-\d+)\b", ["jira-read", "jira-task-draft"]),
    (r"\b(branch|pipeline|devops|\bado\b|merge)\b", ["azure-devops", "commit-push-pr"]),
    (r"\b(research|state of the art|sota|compare|deep dive)\b", ["deep-research", "decision-grade"]),
    (r"\b(ui|ux|frontend|dashboard|design|component)\b", ["ui-ux-pro-max", "frontend-design"]),
    (r"\b(pii|secret|redact|credential|compliance)\b", ["pii-scrubber"]),
    (r"\b(data|dataset|sql|query|csv|parquet)\b", ["context-bounded-analyst"]),
    (r"\b(voice|audio|narrat|tts)\b", ["voice-explainer"]),
    (r"\b(video|avatar|explainer)\b", ["visual-explainer"]),
    (r"\b(meeting|talked with|call with|note this)\b", ["meeting-notes"]),
    (r"\b(message|draft|reply|in my voice|blog|post)\b", ["shoval-voice-draft", "blog", "humanize"]),
    (r"\b(plan|design|architecture)\b", ["premortem", "request-refactor-plan", "domain-model"]),
    (r"\b(reground|resume|out of focus|lost|context drift|stale)\b", ["reground", "workspace-brain"]),
    (r"\b(ops status|kill stale|dead code|watchdog)\b", ["ops-status", "kill-stale", "watchdog"]),
    (r"\b(dispatch|second opinion|delegate to)\b", ["dispatch", "codex-call"]),
    (r"\b(mutation|property test|fuzz|red[- ]?team|adversarial)\b",
     ["mutation-runner", "property-test-gen", "red-team-review"]),
    (r"\b(grill|stress-test|interview me|align the plan)\b", ["grill-me"]),
    (r"\b(end session|wrap up|handover)\b", ["end-session"]),
    (r"\b(connector|apify|scrape|browser|activate mcp)\b", ["mcp-activation", "web-inspect"]),
    (r"\b(openai agent|assistant api|agentkit)\b", ["openai-agents"]),
    (r"\b(persona|meme|caveman|super saiyan|kyuubi|jedi|gandalf|thanos|lebowski)\b", ["persona"]),
    (r"\b(advice|advis|not sure|unsure|not confident|is this still true)\b", ["advisor", "deep-research"]),
]

_COMPILED = [(re.compile(p, re.IGNORECASE), skills) for p, skills in ROUTES]


def parse_registry(text: str) -> dict[str, str]:
    """skill name -> persona name, from the registry markdown.

    Parsed rather than hardcoded, because a duplicated ownership table is a second thing
    that can disagree with the first, and the registry is the file the operator edits.

    Shape relied on, and it is the registry's own:  `### Persona Name` opens a section,
    and `- \\`skill-name\\`` lines under it are that persona's. A heading with no skill
    lines contributes nothing and is not an error: several personas legitimately own
    skills that are not installed here.
    """
    owner: dict[str, str] = {}
    persona = ""
    for line in text.splitlines():
        line = line.rstrip()
        if line.startswith("### "):
            persona = line[4:].strip()
            continue
        if persona and line.lstrip().startswith("- `"):
            skill = line.split("`")[1].strip() if "`" in line else ""
            if skill:
                owner.setdefault(skill, persona)
    return owner


def load_owners() -> dict[str, str]:
    try:
        return parse_registry(REGISTRY.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        # No registry means no persona names, not a broken turn. The skills still route.
        return {}


def route(prompt: str, owners: dict[str, str] | None = None) -> dict:
    """Pure. Returns the skills a prompt implies and the personas that own them.

    Ordered by the number of matched skills a persona owns, so a prompt hitting three
    QA-Lab skills names QA Lab ahead of a persona matched once. Ties keep registry order
    rather than being resolved arbitrarily, because an unstable answer to the same prompt
    is worse than a merely imperfect one.
    """
    owners = load_owners() if owners is None else owners
    text = prompt or ""
    skills: list[str] = []
    for rx, names in _COMPILED:
        if rx.search(text):
            for n in names:
                if n not in skills:
                    skills.append(n)

    tally: dict[str, int] = {}
    for s in skills:
        p = owners.get(s)
        if p:
            tally[p] = tally.get(p, 0) + 1
    personas = sorted(tally, key=lambda p: (-tally[p], list(tally).index(p)))
    return {"skills": skills, "personas": personas, "counts": tally,
            "matched": bool(skills)}


def slug(persona: str) -> str:
    """Registry display name -> agent-file slug ("MCP and Tooling Office" ->
    "mcp-tooling-office"). Measured 2026-08-12: router_named matched subagent_type in
    0 of 20 spawn rows, and the display-name/slug mismatch alone made agreement
    structurally unmeasurable. The injected context and the ledger both use slugs so
    the comparison against state/agent-spawns.jsonl is exact."""
    return "-".join(w for w in persona.lower().split() if w != "and")


def render_context(decision: dict) -> str:
    """The additionalContext string, or "" when nothing matched.

    Empty on no match is deliberate. A router that always says something trains the reader
    to stop reading it, which is the same death the agent feed just measured on issue 38.
    """
    if not decision["matched"]:
        return ""
    lines = []
    if decision["personas"]:
        primary = decision["personas"][0]
        lines.append(
            "Routing (deterministic, from ~/.claude/rules/gastown-company-registry.md): "
            "this prompt looks like **{}** work.".format(primary))
        if len(decision["personas"]) > 1:
            lines.append("Secondary: " + ", ".join(
                slug(p) for p in decision["personas"][1:4]) + ".")
        lines.append(
            "If you delegate, use the Agent tool with subagent_type=`{}` rather than "
            "`general-purpose`. Router-vs-spawn agreement was 0 of 20 in the week to "
            "2026-08-12; this line is the exact string to pass.".format(slug(primary)))
    lines.append("Skills the registry associates with this: "
                 + ", ".join("`{}`".format(s) for s in decision["skills"][:8]) + ".")
    lines.append("This is a keyword match, not a judgement. Ignore it when it is wrong.")
    return "\n".join(lines)


def emit(decision: dict) -> str:
    """The exact stdout payload, or "" when nothing should be injected.

    A function rather than an inline dict in main(), so the selftest can assert its shape
    without spawning a subprocess. The harness keys on hookSpecificOutput.hookEventName
    to decide what the output means; a payload missing it is ignored, and the hook would
    then run on every turn, cost time, log, and inject nothing. That is exactly what
    capture_turn.py already is, and it is the failure this file exists to not repeat.
    """
    ctx = render_context(decision)
    if not ctx:
        return ""
    return json.dumps({"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit", "additionalContext": ctx}})


def log(decision: dict, prompt_len: int) -> None:
    """Append one routing row. No prompt text, only its length and the decision.

    Same discipline as tickets.py, which stores a text_sha and never the prompt: the
    ledger is committed to git and a prompt corpus in git is a different consent question
    than a routing corpus.
    """
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "ts": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
                "prompt_chars": prompt_len,
                "personas": [slug(p) for p in decision["personas"][:3]],
                "skills": decision["skills"][:8],
                "matched": decision["matched"],
                "session": os.environ.get("CLAUDE_SESSION_ID", ""),
            }, ensure_ascii=False) + "\n")
    except OSError:
        pass


def selftest() -> int:
    failures = []

    owners = {"review": "Review Board", "heidegger-reflect": "Review Board",
              "tdd": "Engineering Firm", "deploy-prod": "Release Bureau",
              "prod-deploy-rules": "Release Bureau"}

    d = route("please review this before we merge", owners)
    if "review" not in d["skills"]:
        failures.append("an obvious review prompt matched no review skill")
    if d["personas"][:1] != ["Review Board"]:
        failures.append("the persona owning the most matched skills is not named first")

    if route("", owners)["matched"]:
        failures.append("an empty prompt matched something, so every turn gets noise")
    if render_context(route("", owners)) != "":
        failures.append("a non-match still rendered context, which trains the reader to "
                        "stop reading the router")

    # Determinism. An unstable answer to the same prompt is worse than an imperfect one.
    if route("deploy to prod", owners) != route("deploy to prod", owners):
        failures.append("the same prompt routed differently twice")

    # Ordering by weight, not by first hit.
    weighted = route("review this and check the tdd coverage before we merge", owners)
    if weighted["personas"][0] != "Review Board":
        failures.append("ordering ignores how many skills a persona owns: got {}".format(
            weighted["personas"]))

    parsed = parse_registry(
        "## Persona Owners\n\n### Mayor Opus\n\nOwned skills:\n- `dispatch`\n- `premortem`\n\n"
        "### QA Lab\n\nOwned skills:\n- `tdd`\n")
    if parsed.get("dispatch") != "Mayor Opus" or parsed.get("tdd") != "QA Lab":
        failures.append("the registry parser did not attribute skills to their heading")
    if parse_registry("") != {}:
        failures.append("an empty registry produced ownership out of nothing")

    # The live registry must actually parse. A parser that works on a fixture and not on
    # the real file is the reason this check reads the real file.
    live = load_owners()
    if REGISTRY.exists() and len(live) < 20:
        failures.append("the live registry parsed to only {} owned skill(s), so the "
                        "shape assumption is wrong".format(len(live)))

    # The context must actually name a persona, or the hook changes nothing observable.
    ctx = render_context(route("review this before merge", owners))
    if "Review Board" not in ctx or "subagent_type" not in ctx:
        failures.append("the rendered context does not name a persona and the delegation "
                        "mechanism, so it cannot move the 0-of-19 number")

    # ORDERING, with a fixture whose insertion order DISAGREES with weight order. The
    # previous fixture had them agree, so `list(tally)` and the weighted sort returned the
    # same answer and the mutation survived.
    # `deploy` sits at ROUTES[0] so Release Bureau is INSERTED first with 2 skills;
    # Review Board owns 4 of the matched skills and must therefore be NAMED first. The
    # two orderings must disagree or the mutation that replaces the weighted sort with
    # insertion order is a no-op and survives, which is exactly what happened first.
    ord_owners = {"prod-deploy-rules": "Release Bureau", "deploy-prod": "Release Bureau",
                  "review": "Review Board", "heidegger-reflect": "Review Board",
                  "testing-pyramid": "Review Board", "coverage-enforcer": "Review Board",
                  "tdd": "Engineering Firm"}
    ord_d = route("deploy this after you review it and check the tdd coverage", ord_owners)
    counts = ord_d["counts"]
    if list(counts)[:1] == ["Review Board"]:
        failures.append("the ordering fixture no longer disagrees with insertion order, "
                        "so it cannot detect an order-dependent router")
    elif ord_d["personas"][:1] != ["Review Board"]:
        failures.append("the persona named first is not the one owning the most matched "
                        "skills: {} with counts {}".format(ord_d["personas"], counts))

    # SINGLE OWNERSHIP. The registry states it as a rule; setdefault is what enforces it.
    dup = parse_registry("### First\n- `shared`\n\n### Second\n- `shared`\n")
    if dup.get("shared") != "First":
        failures.append("a skill listed under two personas resolved to the LATER one, so "
                        "editing an unrelated section silently changes routing")

    # THE EMITTED PAYLOAD. Without hookEventName the harness ignores it and the hook is
    # a no-op that still costs time on every turn.
    payload = emit(route("review this before merge", owners))
    if "hookEventName" not in payload or "UserPromptSubmit" not in payload:
        failures.append("the emitted payload does not name the hook event, so the "
                        "harness ignores it and the router injects nothing")
    if emit(route("", owners)) != "":
        failures.append("a non-match still emits a payload")

    # THE LEDGER MUST NOT CARRY PROMPT TEXT. state/routing.jsonl is committed.
    import tempfile  # noqa: PLC0415

    global LEDGER  # noqa: PLW0603
    saved_ledger = LEDGER
    try:
        with tempfile.TemporaryDirectory() as td:
            LEDGER = Path(td) / "routing.jsonl"
            log(route("deploy to prod", owners), len("deploy to prod"))
            written = LEDGER.read_text(encoding="utf-8")
    finally:
        LEDGER = saved_ledger
    if "deploy to prod" in written:
        failures.append("the prompt TEXT was written to the routing ledger, which is "
                        "committed to git; tickets.py stores a sha for this reason")
    if '"prompt_chars"' not in written:
        failures.append("the routing ledger does not record the prompt length, so no "
                        "row can be sanity-checked against the turn it came from")

    # THE HOOK EDGE MUST FAIL OPEN. It runs before every prompt.
    import io  # noqa: PLC0415

    saved_stdin = sys.stdin
    try:
        sys.stdin = io.StringIO("this is not json at all")
        rc_bad = main([])
        sys.stdin = io.StringIO('{"prompt": 12345}')
        rc_odd = main([])
    except Exception as exc:  # noqa: BLE001
        rc_bad = rc_odd = -1
        failures.append("the hook edge RAISED on malformed input, so a bad payload "
                        "breaks the turn it was supposed to enrich: {}".format(exc))
    finally:
        sys.stdin = saved_stdin
    if rc_bad != 0 or rc_odd != 0:
        failures.append("the hook edge returned nonzero on malformed input")

    for line in failures:
        print("  FAIL  " + line)
    if failures:
        print("VERDICT: {} check(s) failed".format(len(failures)))
        return 1
    print("  ok    a review prompt routes to the persona that owns review skills")
    print("  ok    an empty prompt matches nothing and renders nothing")
    print("  ok    the same prompt routes identically twice")
    print("  ok    personas are ordered by how many matched skills they own")
    print("  ok    the registry parser attributes skills to their heading, and to nothing "
          "when the registry is empty")
    print("  ok    the LIVE registry parses to {} owned skill(s)".format(len(live)))
    print("  ok    the rendered context names a persona and the Agent tool")
    print("  ok    a skill listed twice keeps its FIRST owner, so ownership stays single")
    print("  ok    the emitted payload names the hook event, and a non-match emits nothing")
    print("  ok    the routing ledger records length, never prompt text")
    print("  ok    the hook edge fails open on malformed and odd-typed input")
    print("VERDICT: routing is deterministic, silent on no match, and names a real owner")
    return 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()

    if "--explain" in argv:
        i = argv.index("--explain")
        prompt = " ".join(argv[i + 1:])
        d = route(prompt)
        print(json.dumps({"skills": d["skills"], "personas": d["personas"]}, indent=2))
        print()
        print(render_context(d) or "(no match, nothing would be injected)")
        return 0

    # Hook edge. Fails OPEN and SILENT: this runs before every prompt, and a router that
    # can break a turn is worse than one that never ran.
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        prompt = str(payload.get("prompt", ""))
        decision = route(prompt)
        log(decision, len(prompt))
        payload = emit(decision)
        if payload:
            print(payload)
    except Exception:  # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
