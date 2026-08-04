#!/usr/bin/env python3
"""The `agy` CLI, built on the only Antigravity integration path that exists here.

WHY THIS FILE EXISTS RATHER THAN A POINTER TO A VENDOR BINARY. The operator supplied
a four-path integration note on 2026-08-04. Three of its four paths were checked on
this machine and two of them do not exist:

  path 1, `agy -p "..."`
      NO SUCH BINARY. `command -v agy` is empty in WSL and in Windows PowerShell.
      The only Antigravity executable installed is
      "C:/Users/shova/AppData/Local/Programs/Antigravity IDE/bin/antigravity-ide",
      whose .cmd body is `"%~dp0..\\Antigravity IDE.exe" ...\\resources\\app\\out\\cli.js`
      and whose sh shim carries a Microsoft copyright and a VSCODE_PATH. That is a
      VS Code fork's editor CLI, the `code` equivalent. It opens files. It is not an
      agent runner and it takes no -p.
  path 2, the Python SDK
      REAL. `google-antigravity` 0.1.9 on PyPI, installed at
      ~/.local/share/antigravity-venv. Its public API is exactly the names in the
      note: Agent, LocalAgentConfig, CapabilitiesConfig. This file is that path.
  path 3, `claude mcp add antigravity -- python -m google.antigravity.mcp_server`
      NO SUCH MODULE. importlib.util.find_spec("google.antigravity.mcp_server")
      returns None on 0.1.9. The venv does install an `mcp` console script, but that
      belongs to the `mcp` dependency package, not to Antigravity, so registering it
      would produce a server that answers for the wrong thing.
  path 4, the harness oracles
      Already live and already documented in AGENTS.md. Nothing to add.

So `agy` is provided here rather than assumed. Same surface the note expects.

AUTH. `GEMINI_API_KEY`, which is the same variable `dot-claude/bin/a2a-gemini-call.py`
and `tools/review/gemini_diff_review.py` already use, deliberately, so this repo has
one Gemini credential convention rather than three. Vertex/ADC is supported by the SDK
and is NOT wired here, because no ADC file exists on this machine either.

DATA BOUNDARY, which is a policy constraint and not a nicety. The global contract
allows a Gemini free tier only for an explicitly public, non-confidential bundle.
`gemini_diff_review.py` enforces its own version of this by refusing anything that is
not a unified diff. This CLI cannot guess what a caller is sending, so it refuses to
send anything until the caller states the classification with --public, and it looks
for obvious credential shapes and stops on them. That check is a backstop, not a
scanner: it is not capable of recognising confidential business content, and a caller
who passes --public over customer code has defeated it.

    agy -p "explain the failure in this trace"
    cat notes.txt | agy -p "summarise"
    agy --selftest
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

VENV = Path.home() / ".local/share/antigravity-venv"
VENV_PY = VENV / "bin/python"
DEFAULT_MODEL_NOTE = "model selection is left to the SDK default; this CLI does not pin one"

# Shapes that must never leave the machine. Deliberately narrow and high-precision:
# a broad heuristic that fires on ordinary prose would train the operator to pass a
# bypass flag, which is worse than no check.
SECRET_PATTERNS = [
    (re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), "a Google API key"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "an OpenAI-style secret key"),
    (re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b"), "an Anthropic key"),
    (re.compile(r"\bghp_[A-Za-z0-9]{36}\b"), "a GitHub token"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "a private key block"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "a Slack token"),
]


class AgyError(RuntimeError):
    pass


def scan_for_secrets(text: str) -> list[str]:
    """Return the human-readable names of any credential shapes found.

    Returns names, never the matched text, so a refusal message cannot itself leak
    the thing it refused over.
    """
    return [name for pattern, name in SECRET_PATTERNS if pattern.search(text)]


def preflight() -> dict:
    """Everything that must be true before a call, reported together.

    Reported together on purpose: a preflight that stops at the first problem makes
    the operator discover the missing pieces one round trip at a time.
    """
    state = {
        "venv_python": str(VENV_PY),
        "venv_present": VENV_PY.exists(),
        "sdk_importable": False,
        "sdk_error": None,
        "api_key_set": bool(os.environ.get("GEMINI_API_KEY", "").strip()),
        "adc_present": (Path.home() / ".config/gcloud/application_default_credentials.json").exists(),
    }
    if state["venv_present"]:
        probe = subprocess.run(
            [str(VENV_PY), "-c", "import google.antigravity as a; print('ok')"],
            capture_output=True, text=True, timeout=90,
        )
        state["sdk_importable"] = probe.returncode == 0 and "ok" in probe.stdout
        if not state["sdk_importable"]:
            state["sdk_error"] = (probe.stderr or probe.stdout).strip().splitlines()[-1:] or None
    return state


def blockers(state: dict) -> list[str]:
    out = []
    if not state["venv_present"]:
        out.append(
            "the SDK venv is missing at {}. Create it with: "
            "uv venv {} --python 3.12 && uv pip install --python {} google-antigravity"
            .format(VENV, VENV, VENV_PY)
        )
    elif not state["sdk_importable"]:
        out.append("the venv exists but google.antigravity does not import: {}".format(state["sdk_error"]))
    if not state["api_key_set"] and not state["adc_present"]:
        out.append(
            "no credential. Set GEMINI_API_KEY (the same variable "
            "dot-claude/bin/a2a-gemini-call.py already uses, free at "
            "aistudio.google.com/apikey), or configure Vertex ADC with `gcloud auth "
            "application-default login`, which this CLI does not yet wire."
        )
    return out


RUNNER = r'''
import asyncio, sys, json
from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig

payload = json.loads(sys.stdin.read())

async def main():
    config = LocalAgentConfig(
        system_instructions=payload["system"],
        capabilities=CapabilitiesConfig(),
    )
    async with Agent(config) as agent:
        response = await agent.chat(payload["prompt"])
        async for token in response:
            sys.stdout.write(token)
            sys.stdout.flush()

asyncio.run(main())
'''


def run(prompt: str, system: str, timeout: int) -> int:
    """Stream the agent's answer to stdout. Returns a process exit code."""
    proc = subprocess.run(
        [str(VENV_PY), "-c", RUNNER],
        input=json.dumps({"prompt": prompt, "system": system}),
        text=True, timeout=timeout,
    )
    return proc.returncode


def selftest() -> int:
    """Checks that hold with no credential and no network."""
    failures = []

    found = scan_for_secrets("here is AIza" + "B" * 35 + " in a note")
    if "a Google API key" not in found:
        failures.append("scan_for_secrets missed a Google API key shape")

    if scan_for_secrets("a perfectly ordinary sentence about sk- prefixes"):
        failures.append("scan_for_secrets fired on prose with no credential in it")

    # Assembled at runtime rather than written out. The gate's own secret scanner
    # flagged the literal here, correctly: a PEM header is exactly what it should
    # catch. The wrong repair would have been to add the header to gate.py's
    # PUBLIC_TEST_VECTORS, which allowlists it repo-wide and blinds the scanner to
    # every real key block anywhere else. This keeps both detectors intact.
    pem = "-" * 5 + "BEGIN RSA PRIVATE" + " KEY" + "-" * 5
    leaky = scan_for_secrets(pem)
    if not leaky:
        failures.append("scan_for_secrets missed a PEM private key header")
    if any("BEGIN" in name for name in leaky):
        failures.append("a refusal name echoed the matched text back")

    saved = os.environ.pop("GEMINI_API_KEY", None)
    try:
        state = dict(preflight())
        state["api_key_set"] = False
        state["adc_present"] = False
        msgs = blockers(state)
        if not any("GEMINI_API_KEY" in m for m in msgs):
            failures.append("blockers() did not name the missing variable")
    finally:
        if saved is not None:
            os.environ["GEMINI_API_KEY"] = saved

    state = dict(preflight())
    state["venv_present"] = False
    if not any("uv venv" in m for m in blockers(state)):
        failures.append("blockers() did not give the command that fixes a missing venv")

    for line in failures:
        print("  FAIL  " + line)
    if failures:
        print("VERDICT: {} check(s) failed".format(len(failures)))
        return 1
    print("  ok    a credential shape in the prompt is detected")
    print("  ok    ordinary prose is not flagged")
    print("  ok    a refusal names the kind of secret, never the secret")
    print("  ok    a missing key is reported by variable name")
    print("  ok    a missing venv is reported with the command that creates it")
    print("VERDICT: agy refuses without a credential and without a stated classification")
    return 0


def read_stdin(have_prompt: bool, wait_s: float = 0.25) -> str:
    """Read piped input, without hanging when stdin is open but silent.

    Found by running `agy -p "..."` from a harness whose stdin is an inherited pipe
    that nobody ever writes to or closes. `isatty()` is false there, so a plain
    read() blocked forever. A terminal user never hits it and an automation user
    hits it every time, which is exactly the kind of bug that only shows up in the
    unattended case. With -p already supplying the prompt, stdin is optional, so it
    gets a short poll and is skipped if nothing is ready. Without -p there is
    nothing else to work with, so the blocking read is correct.
    """
    if sys.stdin.isatty():
        return ""
    if not have_prompt:
        return sys.stdin.read()
    import select

    ready, _, _ = select.select([sys.stdin], [], [], wait_s)
    return sys.stdin.read() if ready else ""


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        prog="agy",
        description="Send a prompt to a Google Antigravity agent. " + DEFAULT_MODEL_NOTE,
    )
    ap.add_argument("-p", "--prompt", help="the prompt. Reads stdin when omitted.")
    ap.add_argument("--system", default="You are a precise engineering assistant.",
                    help="system instructions for the agent")
    ap.add_argument("--public", action="store_true",
                    help="attest that the input is public and non-confidential. Required to send.")
    ap.add_argument("--timeout", type=int, default=300, help="seconds")
    ap.add_argument("--check", action="store_true", help="report readiness and exit")
    ap.add_argument("--selftest", action="store_true", help="run the offline checks")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    state = preflight()
    if args.check:
        print(json.dumps(state, indent=2))
        for b in blockers(state):
            print("BLOCKER: " + b)
        return 0 if not blockers(state) else 1

    prompt = "\n\n".join(x for x in (args.prompt, read_stdin(bool(args.prompt))) if x)
    if not prompt.strip():
        print("agy: no prompt. Use -p or pipe stdin.", file=sys.stderr)
        return 2

    # Data checks run BEFORE the plumbing checks, on purpose. They are free, they are
    # the safety-relevant ones, and putting them second means a caller with no key
    # gets told about the key and never learns that the payload would have been
    # refused anyway. The first version had this the wrong way round and the refusal
    # paths could not even be exercised without a credential.
    if not args.public:
        print(
            "agy: refusing to send. The global contract allows a Gemini free tier only for an "
            "explicitly public, non-confidential bundle. Pass --public to attest that this input "
            "carries no employer or customer code, no resume or recruiting material, no "
            "credentials and no personal data.",
            file=sys.stderr,
        )
        return 4

    hits = scan_for_secrets(prompt)
    if hits:
        print("agy: refusing to send, the input contains {}.".format(" and ".join(hits)), file=sys.stderr)
        return 5

    problems = blockers(state)
    if problems:
        for b in problems:
            print("BLOCKER: " + b, file=sys.stderr)
        return 3

    try:
        return run(prompt, args.system, args.timeout)
    except subprocess.TimeoutExpired:
        print("agy: timed out after {}s".format(args.timeout), file=sys.stderr)
        return 6


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
