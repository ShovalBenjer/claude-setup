#!/usr/bin/env python3
"""Stop-boundary gate: a done-claim needs a green gate run for THIS tree.

WHY THIS IS NOT completion_gate.py

completion_gate.py, sitting next to this file, decides whether a completion claim
is acceptable by searching the assistant's own sentence for the word "tested".
That is a check on wording. An agent that writes "implemented and tested" passes
it whether or not anything ran, and an agent that ships a broken web app while
saying "tested locally" passes it too. It is worth keeping as a calibration nudge
and it is not evidence of anything.

This hook asks a question the agent cannot answer with prose: does
state/gate-runs.jsonl contain a full PASS recorded against the exact working tree
being claimed done? The fingerprint covers HEAD plus the diff plus untracked
file names, so a pass earned three edits ago does not count, and neither does a
pass on a different branch.

BEHAVIOUR

  no quality-contract.json in the project      pass through, nothing to enforce
  contract, green run for this tree            pass through
  contract, no green run, no completion claim  systemMessage, non-blocking
  contract, no green run, completion claim     block with the red domains named
  gate.py cannot be found or imported          systemMessage saying enforcement
                                               is OFF, never a silent pass

That last row is the whole point of the file's tone. Three hooks in this
directory are 45-byte files containing a Linux path that does not exist on this
machine; they fail open and say nothing, which is why nobody noticed for months.
A guard that cannot run must announce that it cannot run.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT_NAME = "quality-contract.json"


def out(obj: dict) -> int:
    sys.stdout.write(json.dumps(obj))
    return 0


def find_contract(start: str) -> str | None:
    """Walk up looking for the contract. Stops at the git root or 6 levels."""
    cur = os.path.abspath(start)
    for _ in range(6):
        if os.path.exists(os.path.join(cur, CONTRACT_NAME)):
            return cur
        if os.path.isdir(os.path.join(cur, ".git")):
            return None
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent
    return None


def load_gate(project: str | None = None):
    """Import tools/gate/gate.py, wherever this hook happens to be deployed.

    The hook ships to ~/.claude/hooks while gate.py stays in the repo, so the
    path cannot be relative to __file__ once deployed. Each candidate below is a
    real layout on this machine, tried in order of how specific it is.

    `project` (the contract-bearing dir `find_contract` already resolved) is
    tried first. Every real checkout and every real git worktree carries its
    own tools/gate/gate.py, so gate.setup_root() then resolves to the SAME
    tree `project` lives in. Without this, a worktree-isolated session fell
    through to the ~/claude-setup fallback, a symlink to the main checkout:
    the loaded module's setup_root() pointed at the wrong repo, so
    ledger_state() read the main checkout's ledger instead of the worktree's
    own, and a real PASS there stayed invisible to this hook. Found 2026-08-24,
    worktree ecosystem-db-spec: a green run was reported "never gated" every
    turn because the hook was checking a different file.
    """
    candidates = []
    if project:
        candidates.append(os.path.join(project, "tools", "gate", "gate.py"))
    env = os.environ.get("CLAUDE_SETUP_ROOT")
    if env:
        candidates.append(os.path.join(env, "tools", "gate", "gate.py"))
    candidates += [
        os.path.join(HERE, "..", "..", "tools", "gate", "gate.py"),
        os.path.join(os.path.expanduser("~"), "claude-setup", "tools", "gate", "gate.py"),
    ]
    for cand in candidates:
        cand = os.path.abspath(cand)
        if not os.path.exists(cand):
            continue
        try:
            spec = importlib.util.spec_from_file_location("_gate", cand)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod, cand
        except Exception as exc:
            return None, "found {} but could not import it: {}".format(cand, exc)
    return None, "no gate.py at any of: " + ", ".join(os.path.abspath(c) for c in candidates)


def assistant_text(payload: dict) -> str:
    """The last assistant message, from the payload or from the transcript.

    Stop payloads do not reliably carry the message inline, so the transcript is
    the load-bearing path here, not the fallback. completion_gate.py only reads
    the inline keys, which is worth knowing about it.
    """
    for key in ("last_assistant_message", "assistant_message", "response", "message"):
        v = payload.get(key)
        if isinstance(v, str) and v.strip():
            return v
        if isinstance(v, dict):
            for nested in ("text", "content"):
                item = v.get(nested)
                if isinstance(item, str) and item.strip():
                    return item

    path = payload.get("transcript_path")
    if not path or not os.path.exists(path):
        return ""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return ""
    for line in reversed(lines[-400:]):
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if rec.get("type") != "assistant":
            continue
        msg = rec.get("message") or {}
        content = msg.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = [c.get("text", "") for c in content
                     if isinstance(c, dict) and c.get("type") == "text"]
            joined = "\n".join(p for p in parts if p)
            if joined.strip():
                return joined
    return ""


def completion_claim(text: str) -> bool:
    """Reuse completion_gate's own definition so the two cannot drift apart."""
    try:
        spec = importlib.util.spec_from_file_location(
            "_cg", os.path.join(HERE, "completion_gate.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return bool(mod.COMPLETION.search(text))
    except Exception:
        import re
        return bool(re.search(
            r"(?i)\b(all done|done|complete[d]?|fully working|verified|fixed|"
            r"implemented|it works|everything works|ready|shipped)\b", text))


def ledger_state(gate, project: str) -> tuple[bool, str]:
    """Is there a full PASS for this exact tree? Returns (green, explanation)."""
    ledger = os.path.join(gate.setup_root(), gate.LEDGER)
    sha, dirty, fp = gate.tree_fingerprint(project)
    if not os.path.exists(ledger):
        return False, ("no gate run has ever been recorded, so nothing has measured this "
                       "project")
    rows = []
    with open(ledger, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("project_path") == project:
                rows.append(r)
    if not rows:
        return False, "no gate run recorded for {}".format(project)
    mine = [r for r in rows if r.get("fingerprint") == fp and not r.get("partial")]
    if any(r.get("verdict") == "PASS" for r in mine):
        return True, ""
    if mine:
        last = mine[-1]
        return False, "the gate ran on this exact tree and FAILED on: {}".format(
            ", ".join(last.get("blocking") or ["unknown"]) or "unknown")
    partials = [r for r in rows if r.get("fingerprint") == fp and r.get("partial")]
    if partials:
        return False, ("only single domains have been run against this tree ({}), which is "
                       "not a gate pass".format(", ".join(
                           sorted({d for p in partials for d, s in (p.get("domains") or {}).items()
                                   if s in ("PASS", "FAIL")}))[:200]))
    return False, ("the {} recorded run(s) are against other trees. The current tree ({}{}) "
                   "has never been gated.".format(len(rows), fp, ", dirty" if dirty else ""))


#: Path suffixes/prefixes that no gate CODE domain can cover. A tree whose every
#: change is one of these is documentation/payload prose, so a full 12-domain code
#: gate is not-applicable and the block downgrades to a note. This list is
#: deliberately TIGHT: the gate's own docstring warns that an over-broad exclusion
#: "buys a satisfiable gate by going blind". A `.py`/`.ts`/`.sh` anywhere (including
#: dot-claude/hooks and tools/) is code and is NOT here, so it still blocks.
#: `.jsonl`/`.txt` here are the append-only state ledgers and doc-status files under
#: state/ and docs/, which no code domain covers; see tests/test_ship_gate_docs_only.py.
_DOC_ONLY_SUFFIXES = (".md", ".mdx", ".txt", ".rst", ".jsonl")
_DOC_ONLY_DIRS = ("docs/",)


def _changed_paths(gate, project: str) -> list[str]:
    """Paths changed vs HEAD plus untracked names, via the gate's own git().

    Uses name-only / -z forms, never a fixed-column slice of `status --porcelain`:
    gate.py's own comment records that `line[3:]` returns `EADME.md` for a deleted
    README. `-z` splits cleanly on NUL; each record after the first is `XY<space>path`.
    """
    paths = set()
    for line in gate.git("diff --name-only HEAD -- .", project).splitlines():
        if line.strip():
            paths.add(line.strip())
    raw = gate.git("status --porcelain -z -- .", project)
    for rec in raw.split("\0"):
        if not rec or len(rec) < 4:
            continue
        _, _, p = rec.partition(" ")
        p = p.strip()
        if p and " -> " in p:
            p = p.split(" -> ", 1)[1].strip()
        if p:
            paths.add(p)
    return sorted(paths)


def classify_paths(paths: list[str]) -> list[str]:
    """The code paths in `paths`; empty list means all-prose."""
    code = []
    for p in paths:
        low = p.lower()
        if low.endswith(_DOC_ONLY_SUFFIXES):
            continue
        if any(low.startswith(d) or ("/" + d) in low for d in _DOC_ONLY_DIRS):
            continue
        code.append(p)
    return code


def _last_full_run(gate, project: str) -> tuple[str | None, str | None]:
    """(commit, verdict) of the last non-partial gate run for this project."""
    ledger = os.path.join(gate.setup_root(), gate.LEDGER)
    if not os.path.exists(ledger):
        return None, None
    last = None
    with open(ledger, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("project_path") == project and not r.get("partial"):
                last = r
    if not last:
        return None, None
    return last.get("commit"), last.get("verdict")


def is_docs_only(gate, project: str) -> tuple[bool, list[str]]:
    """True iff everything since the last PASSING gate run is prose, not code.

    Returns (docs_only, offending_code_paths). The delta is the UNION of the
    working changes and the commits since the last full run's commit, because
    classifying only the working diff left two holes, both hit on 2026-08-13:
    a clean tree whose only delta since the gate was a committed docs regen still
    hard-blocked (annoyance), and, worse, a dirty docs-only tree sitting on top
    of committed-but-ungated CODE would have downgraded (bypass). The baseline
    must exist and be a PASS: with no run ever there is nothing to be "docs-only
    since", and after a FAIL the red domains are outstanding no matter what kind
    of file changed afterwards.
    """
    commit, verdict = _last_full_run(gate, project)
    if not commit or verdict != "PASS":
        return False, []
    delta = set(_changed_paths(gate, project))
    for line in gate.git("diff --name-only {}..HEAD -- .".format(commit), project).splitlines():
        if line.strip():
            delta.add(line.strip())
    if not delta:
        return False, []
    code = classify_paths(sorted(delta))
    return (not code), code


def howto_command(setup_root: str, project: str) -> str:
    """The one command this hook tells a blocked session to run.

    Resolves both sides before comparing them. `~/claude-setup` is a symlink to
    `~/work/repos/claude-setup` on the WSL host, and os.path.relpath treats the two
    spellings as unrelated strings, so the hook printed

        python ../../../claude-setup/tools/gate/gate.py run --project .

    for a gate sitting at `tools/gate/gate.py` inside the project being blocked.
    Both reach the same file through the link, which is why it survived unnoticed,
    but the instruction is the hook's entire output when it blocks and it should
    name the shortest true path. Measured 2026-07-31; the operator quoted the
    climbing form back as the thing he was being told to run.
    """
    target = os.path.realpath(os.path.join(setup_root, "tools", "gate", "gate.py"))
    rel = os.path.relpath(target, os.path.realpath(project))
    return "python {} run --project .".format(rel.replace("\\", "/"))


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise TypeError
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
        return out({})

    if payload.get("stop_hook_active") is True:
        return out({})

    cwd = payload.get("cwd") or os.getcwd()
    project = find_contract(cwd)
    if not project:
        return out({})

    gate, where = load_gate(project)
    if gate is None:
        return out({"systemMessage": (
            "Ship gate is OFF: {} has a {} but the gate runner is unreachable ({}). "
            "Nothing is checking implementation quality this turn. Fix the path or set "
            "CLAUDE_SETUP_ROOT.".format(project, CONTRACT_NAME, where))})

    try:
        green, why = ledger_state(gate, project)
    except Exception as exc:
        return out({"systemMessage": (
            "Ship gate could not read its own ledger ({}), so it is not enforcing this "
            "turn.".format(exc))})

    if green:
        return out({})

    text = assistant_text(payload)
    howto = howto_command(gate.setup_root(), project)

    if completion_claim(text):
        try:
            docs_only, _code = is_docs_only(gate, project)
        except Exception:
            docs_only = False  # on any doubt, fall through to the hard block
        if docs_only:
            return out({"systemMessage": (
                "Ship gate: the change in this tree is documentation/payload prose only "
                "(no code path touched), so the code domains are not-applicable and no "
                "full gate run is required. Prose is still gated by tools/slop_lint.py. "
                "If you later touch a .py/.ts/.sh or any non-doc file, run `{}`.".format(howto))})
        return out({"decision": "block", "reason": (
            "Ship gate: this project declares a quality contract and {}\n"
            "A done-claim is not available yet. Run:\n  {}\n"
            "Then either make the red domains green, or record a waiver with a reason and "
            "an expiry date and say in the response which domains are waived and why. "
            "Do not restate the claim without doing one of those two things."
        ).format(why, howto)})

    return out({"systemMessage": (
        "Ship gate note: {} Run `{}` before claiming this work is done.".format(why, howto))})


if __name__ == "__main__":
    raise SystemExit(main())
