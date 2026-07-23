#!/usr/bin/env python3
"""Spawn a Gastown persona as a live Claude Code agent, STREAMING every action so you can watch.

Reads the persona charter from `intent gastown spec <persona>`, spawns it, and emits a compact
live line for every tool call the agent makes (Read/Edit/Bash/...) to stderr AND a per-agent log
at ~/.claude/cache/agents/<slug>.log, so the dogs are visible in action, never headless. No
permission leash is imposed here (pass --permission-mode to choose); this is a window, not a cage.
--deep runs the draft -> self-critique -> revise depth loop.

  gastown-spawn "Product Studio" "task" [--deep] [--cwd DIR] [--permission-mode acceptEdits]
Watch live from any terminal:  tail -f ~/.claude/cache/agents/*.log
"""
from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import TextIO

from claude_agent_sdk import ClaudeAgentOptions, query

INTENT = "/home/shovalbe/.claude/bin/intent"
LOGDIR = Path.home() / ".claude" / "cache" / "agents"


def load_spec(persona: str) -> dict:
    out = subprocess.run([INTENT, "gastown", "spec", persona], capture_output=True, text=True)
    if out.returncode != 0:
        sys.stderr.write((out.stderr or "gastown spec failed") + "\n")
        sys.exit(2)
    return json.loads(out.stdout)


def _text_of(msg: object) -> str:
    parts: list[str] = []
    content = getattr(msg, "content", None)
    if content is not None:
        for block in (content if isinstance(content, list) else [content]):
            text = getattr(block, "text", None)
            if isinstance(text, str):
                parts.append(text)
    result = getattr(msg, "result", None)
    if isinstance(result, str):
        parts.append(result)
    return "\n".join(parts)


def _actions(msg: object) -> list[str]:
    """One compact action line per tool call in a message, for the live feed."""
    lines: list[str] = []
    content = getattr(msg, "content", None)
    if content is None:
        return lines
    home = str(Path.home())
    for block in (content if isinstance(content, list) else [content]):
        name = getattr(block, "name", None)
        if name is None:
            continue
        inp = getattr(block, "input", {}) or {}
        target = (
            inp.get("file_path") or inp.get("path") or inp.get("command")
            or inp.get("pattern") or inp.get("query") or ""
        )
        target = str(target).replace(home, "~").replace("\n", " ")[:80]
        lines.append(f"{name} {target}".strip())
    return lines


def _emit(line: str, log: TextIO) -> None:
    sys.stderr.write(line + "\n")
    sys.stderr.flush()
    log.write(line + "\n")
    log.flush()


async def run_once(sp: str, prompt: str, cwd: str, max_turns: int, perm: str, tag: str, log: TextIO) -> str:
    opts = ClaudeAgentOptions(system_prompt=sp, cwd=cwd, max_turns=max_turns, permission_mode=perm)
    chunks: list[str] = []
    async for msg in query(prompt=prompt, options=opts):
        for act in _actions(msg):
            _emit(f"  {tag} -> {act}", log)  # LIVE: every tool call as it happens
        text = _text_of(msg)
        if text:
            chunks.append(text)
    return "\n".join(chunks).strip()


REPO = "/home/shovalbe/projects/intent-control-plane"


def _grade_spawn(cwd: str, persona: str, task: str, log: TextIO) -> None:
    """Grade this spawn's git diff through the tested package (guardrails + archive), best-effort.

    Closes the transmission gap: every spawn leaves a guardrail-screened variant in the archive so
    company.persona_scorecard grades personas from real spawns. Never raises into the spawn.
    """
    try:
        diff = subprocess.run(["git", "-C", cwd, "diff"], capture_output=True, text=True).stdout
        if not diff.strip():
            return
        out = subprocess.run(
            ["uv", "run", "--project", REPO, "python", "-m", "intent_control_plane.spawn_grade",
             "--subject", task[:80], "--persona", persona, "--model", "gastown-spawn"],
            input=diff, capture_output=True, text=True,
        )
        _emit(f"  {persona} [grade] {(out.stdout or out.stderr).strip()[:160]}", log)
    except Exception as exc:  # noqa: BLE001 - grading must never break a spawn
        _emit(f"  {persona} [grade] skipped ({exc})", log)


async def main(args: argparse.Namespace) -> int:
    spec = load_spec(args.persona)
    sp, name = spec["system_prompt"], spec["name"]
    LOGDIR.mkdir(parents=True, exist_ok=True)
    logpath = LOGDIR / f"{name.lower().replace(' ', '-')}.log"
    with logpath.open("a", encoding="utf-8") as log:
        _emit(f"[spawn] {name} :: {args.task}   (watch: tail -f {logpath})", log)
        result = await run_once(sp, args.task, args.cwd, args.max_turns, args.permission_mode, f"[{name}]", log)
        if args.deep:
            _emit(f"[{name}] [depth] self-critique", log)
            critique = await run_once(
                sp,
                f"Draft:\n\n{result}\n\nCritique it as a senior {name} would: list craft/depth gaps, or reply SHIP.",
                args.cwd, args.max_turns, args.permission_mode, f"[{name}:critique]", log,
            )
            if not critique.strip().upper().startswith("SHIP"):
                _emit(f"[{name}] [depth] revise", log)
                result = await run_once(
                    sp,
                    f"Draft:\n\n{result}\n\nCritique:\n\n{critique}\n\nProduce the revised senior-grade version now.",
                    args.cwd, args.max_turns, args.permission_mode, f"[{name}:revise]", log,
                )
        _grade_spawn(args.cwd, name, args.task, log)
        print(result)
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("persona")
    parser.add_argument("task")
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--deep", action="store_true")
    parser.add_argument("--max-turns", type=int, default=12)
    parser.add_argument("--permission-mode", default="acceptEdits")
    sys.exit(asyncio.run(main(parser.parse_args())))
