#!/usr/bin/env python3
"""Find the harness (claude-setup) without naming a machine.

WHAT THIS REPLACES

`quality-contract.json` used to carry
`python C:/Users/shova/claude-setup/tools/review/panel.py run --project .`.
docs/specs/2026-07-26-repo-target-architecture.md:56 names that as the decisive
architectural defect: "the interface is currently transported by absolute paths
... Replace with a resolution order: $CLAUDE_HARNESS env var, then a
.harness-ref file at product root pinning a commit SHA, then a vendored
fallback." That section is marked [INFERENCE] because no such mechanism existed.
This is it, written 2026-07-31.

PROMOTED 2026-08-09. This file spent nine days living in new-recruit, a CONSUMER
of the harness, while the harness it resolves documented neither this mechanism
nor the weaker one daily-deep-learning used. A new project inheriting this setup
had to find the resolution order by reading a downstream copy, which is the wrong
direction for an interface to travel. The canonical copy is now here, in the
producer. Consumers vendor or reference it; they no longer own it.

THE RULE THIS FILE IS BUILT AROUND

Resolution either returns a directory that really contains `tools/gate/gate.py`,
or it raises. There is no quiet third answer. That is not a style preference:
two lookup tables in this estate failed the other way on the same day, and both
looked healthy while doing it.

  - `claude-setup/tools/lib/envload.py` had three candidate .env paths, none of
    which resolved after the repos moved. It returned an empty list and every
    caller silently had no API keys.
  - `claude-setup/tools/bus/bus.py` LANE_MAP derived lane "?" for every live
    checkout on this machine, because the only entry that still resolved pointed
    at a directory deleted that morning. Messages were unaddressable while the
    map read as complete.

So a wrongly-set `$CLAUDE_HARNESS` raises here rather than falling through to the
next candidate. Falling through is how an operator's explicit override gets
silently ignored, which is worse than the crash.

WHY THE PIN DOES NOT BLOCK RESOLUTION

`.harness-ref` may pin a SHA. A drift between the pin and the resolved tree's
HEAD fails `check()` but does NOT fail `resolve()`. A product must still be able
to run its gate against a harness that has moved ahead; refusing to resolve
would make a stale pin an outage. `check()` is the thing a gate step calls.

FORMAT

    # comment
    repo = https://github.com/ShovalBenjer/claude-setup.git
    sha  = 539f0a6...
    path = /home/shov/work/repos/claude-setup
    path = /mnt/c/Users/shova/claude-setup

`path` may repeat; order is the search order. Everything is optional, though a
file with no usable `path` and no `$CLAUDE_HARNESS` will raise, by design.

CLI:
  harness.py path     print the resolved harness root
  harness.py check    exit 1 if unresolvable or the pinned SHA has drifted
  harness.py info     path, source, pinned sha, actual sha
  harness.py exec review/panel.py run --project .
                      run a harness tool, resolving its root first. This is the
                      form `quality-contract.json` uses, so a domain command can
                      name a harness tool without naming a machine.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

#: What makes a directory a harness rather than any directory. Deliberately the
#: gate entry point named by the spec's interface list, not a marker file: a
#: marker can be copied somewhere useless, this cannot.
MARKER = Path("tools") / "gate" / "gate.py"

REF_NAME = ".harness-ref"

#: Last resort. A product that vendors the harness puts it here. Nothing does
#: today, and the spec calls this the "vendored fallback" leg.
VENDOR_REL = Path("tools") / "vendor" / "claude-setup"


class HarnessNotFound(RuntimeError):
    """No candidate resolved. The message names every path that was tried."""


def _is_harness(p) -> bool:
    try:
        return (Path(p) / MARKER).is_file()
    except OSError:
        return False


def parse_ref(path):
    """Read a .harness-ref into {'repo': str|None, 'sha': str|None, 'paths': [...]}."""
    out = {"repo": None, "sha": None, "paths": []}
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError:
        return out
    for line in raw.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip().lower(), val.strip()
        if not val:
            continue
        if key == "path":
            out["paths"].append(val)
        elif key in ("repo", "sha"):
            out[key] = val
    return out


def _own_harness():
    """The harness this file is itself inside, if it is inside one.

    Needed only because the canonical copy moved into the producer on
    2026-08-09. A consumer's copy sits at `<product>/tools/harness.py` and its
    ancestors are the product, which contains no gate, so this returns None and
    the env, ref and vendored legs run exactly as before. The copy living in
    claude-setup has the gate two directories up, and without this leg it asked
    a harness to locate a harness and raised.

    Checked by walking up rather than by a fixed depth, so moving this file
    deeper does not silently break it, which is the failure the fixed
    `parent.parent` default produced the first time it ran from its new home.
    """
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if _is_harness(candidate):
            return candidate
    return None


def _default_product_root():
    """Where to look for `.harness-ref` when the caller names no product.

    A consumer copy at `<product>/tools/harness.py` wants its grandparent. This
    copy is one level deeper, so a hardcoded `parent.parent` pointed at
    `claude-setup/tools` and reported every candidate as missing. Resolved from
    the file's position rather than assumed.
    """
    here = Path(__file__).resolve()
    return here.parent.parent if here.parent.name != "harness" else here.parent.parent.parent


def resolve(product_root=None):
    """Return (harness_root, source). Raises HarnessNotFound rather than guessing.

    source is one of "env", "self", "harness-ref", "vendored".
    """
    root = Path(product_root or _default_product_root())
    tried = []

    env = os.environ.get("CLAUDE_HARNESS", "").strip()
    if env:
        # Explicit override. If it is wrong, say so; do not quietly use something
        # else, because the operator set this on purpose.
        if _is_harness(env):
            return str(Path(env)), "env"
        raise HarnessNotFound(
            "CLAUDE_HARNESS is set to {!r} but that directory has no {}. "
            "Refusing to fall through to another candidate: an explicit "
            "override that is silently ignored is the failure this module "
            "exists to prevent.".format(env, MARKER.as_posix()))

    # Self-detection answers "I am the harness and nobody told me otherwise". An
    # explicit product_root is somebody telling it otherwise: the caller is asking
    # where THAT product finds its harness, and that product's .harness-ref is the
    # answer even when this file happens to live inside a harness of its own.
    #
    # Caught by running it rather than by reading it. Asked to resolve for
    # daily-deep-learning, the promoted copy returned its own repository via
    # "self" and never opened the ref file that had just been written for that
    # product. The self leg had swallowed the case the ref leg exists for.
    if product_root is None:
        own = _own_harness()
        if own is not None:
            return str(own), "self"

    ref = parse_ref(root / REF_NAME)
    for p in ref["paths"]:
        tried.append(p)
        if _is_harness(p):
            return str(Path(p)), "harness-ref"

    vendored = root / VENDOR_REL
    tried.append(str(vendored))
    if _is_harness(vendored):
        return str(vendored), "vendored"

    raise HarnessNotFound(
        "no harness found from product root {}. Tried, in order: {}. "
        "Set CLAUDE_HARNESS, add a `path =` line to {}, or vendor the harness "
        "at {}.".format(root, ", ".join(tried) or "(nothing)", REF_NAME,
                        VENDOR_REL.as_posix()))


def head_sha(path):
    """HEAD of a git checkout, or None if it is not one."""
    try:
        r = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def check(product_root=None):
    """(ok, detail). False when unresolvable, or when a pinned SHA has drifted."""
    root = Path(product_root or Path(__file__).resolve().parent.parent)
    try:
        path, source = resolve(product_root=root)
    except HarnessNotFound as e:
        return False, str(e)

    pinned = parse_ref(root / REF_NAME)["sha"]
    if not pinned:
        return True, "resolved {} via {}; no sha pinned".format(path, source)

    actual = head_sha(path)
    if actual is None:
        return True, ("resolved {} via {}; pinned {} but the tree is not a git "
                      "checkout, so the pin cannot be verified"
                      .format(path, source, pinned[:8]))
    if actual.startswith(pinned) or pinned.startswith(actual):
        return True, "resolved {} via {}; sha {} matches".format(
            path, source, actual[:8])
    return False, ("resolved {} via {}, but the pinned sha has drifted: "
                   "{} pinned, {} on disk. Re-pin deliberately after reading "
                   "what changed, or the pin stops meaning anything."
                   .format(path, source, pinned[:8], actual[:8]))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0] if argv else "path"

    if cmd == "path":
        try:
            path, _ = resolve()
        except HarnessNotFound as e:
            print(e, file=sys.stderr)
            return 1
        print(path)
        return 0

    if cmd == "check":
        ok, detail = check()
        print(detail, file=sys.stdout if ok else sys.stderr)
        return 0 if ok else 1

    if cmd == "exec":
        # `harness.py exec review/panel.py run --project .` becomes
        # `<resolved>/tools/review/panel.py run --project .`. The relative form
        # is deliberate: a contract that spelled the tool absolutely would be
        # the defect this module removes, one indirection later.
        if len(argv) < 2:
            print("exec needs a tool path relative to <harness>/tools/, "
                  "e.g. review/panel.py", file=sys.stderr)
            return 2
        try:
            root, _ = resolve()
        except HarnessNotFound as e:
            print(e, file=sys.stderr)
            return 1
        tool = Path(root) / "tools" / argv[1]
        if not tool.is_file():
            print("resolved harness {} has no tools/{}".format(root, argv[1]),
                  file=sys.stderr)
            return 1
        return subprocess.call([sys.executable, str(tool)] + list(argv[2:]))

    if cmd == "info":
        root = Path(__file__).resolve().parent.parent
        ref = parse_ref(root / REF_NAME)
        try:
            path, source = resolve()
        except HarnessNotFound as e:
            print("unresolved: {}".format(e), file=sys.stderr)
            return 1
        print("path   {}".format(path))
        print("source {}".format(source))
        print("repo   {}".format(ref["repo"] or "(none)"))
        print("pinned {}".format(ref["sha"] or "(none)"))
        print("actual {}".format(head_sha(path) or "(not a git checkout)"))
        return 0

    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
