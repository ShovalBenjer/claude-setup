"""Generate src/rules.rs from safety_gate.py::RULES, including the prescan literals.

Two jobs, and the second is the one that matters.

CODEGEN. The patterns are copied byte-for-byte rather than retyped, because a safety guard
whose rules were transcribed by hand has no way to prove it still means what it meant.
Inline flags in the pattern strings, `(?i)` and `(?is)`, carry the Python compile flags
across, so nothing about the flags needs restating on the Rust side.

PRESCAN SOUNDNESS. Measured 2026-07-30: compiling the 17 patterns costs ~45 ms of the
gate's ~49 ms on Linux, redone on every invocation. The fix is to skip compiling a pattern
that cannot possibly match, decided by a cheap substring test. Every rule needs some literal
present before it can fire: `rm`, `git`, a downloader name, an interpreter name.

That optimisation is correctness-critical in one direction only, and the asymmetry is the
whole design:

    OVER-approximating is free.   A literal that is present when the rule would not have
                                 matched just means the pattern gets compiled and then
                                 fails. Slower, still correct.

    UNDER-approximating is a       A literal wrongly believed necessary means the rule is
    SILENT SECURITY HOLE.          skipped on a command it should have blocked, and nothing
                                   anywhere reports it.

So the literal sets below are not trusted because they were read carefully. This module
FUZZES them before emitting anything: for every rule, over the corpus plus generated
mutations, it asserts that `pattern.search(s)` implies at least one literal is in
`s.lower()`. A counterexample aborts the generation rather than producing a fast gate with
a hole in it.

Usage:
    python tools/hookgate/regen_rules.py            # verify, then write src/rules.rs
    python tools/hookgate/regen_rules.py --check     # exit 1 if it would change
    python tools/hookgate/regen_rules.py --verify-only
"""

from __future__ import annotations

import importlib.util
import itertools
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "src" / "rules.rs"
CORPUS = HERE / "corpus.txt"

# The live hook is the source of truth, not the committed copy under dot-claude/, because
# the live tree can drift ahead of the repo and it is the live rules that are enforced.
SAFETY_GATE = Path.home() / ".claude" / "hooks" / "safety_gate.py"
FALLBACK = HERE.parents[2] / "payload" / "dot-claude" / "hooks" / "safety_gate.py"

# Rule index -> a CONJUNCTION OF DISJUNCTIONS. Every group must contribute at least one
# member present in the lowercased command, or the rule cannot match and is skipped.
#
# Why groups and not one flat list. A flat any-of list was measured first and left the two
# most common command shapes in this repository paying for nothing: `python -m pytest` cost
# 9.09 ms because "python" alone admitted rule 16, and any `git` command admitted all ten git
# rules. But rule 16 needs an interpreter AND a credential-shaped path; rule 3 needs "git" AND
# "reset". Expressing that conjunction lets `git status` and `python -m pytest` compile nothing.
#
# Soundness requirement, per group: if the group contributes no member, the pattern CANNOT
# match. Over-approximating within a group is free. Adding a group that is not truly necessary
# is an under-approximation of the rule and is a silent security hole, which is what the fuzz
# below exists to catch.
#
# Derivations. Rule 0 opens `\brm\s+`. Rule 1 needs the literal `remove-item`. Rule 2
# alternates `rd|rmdir` and its lookahead requires `/s`; note "rmdir" does NOT contain "rd" as
# a substring, so both spellings are listed. Rules 3 to 12 all open `\bgit\b` and each names
# its own subcommand. Rules 13 to 16 open on an alternation of program names, and 14, 15, 16
# additionally require a credential-shaped path in their tail alternation.
#
# Short members like "gc", "py" and "rd" match inside unrelated words. Deliberate
# over-approximation, and it costs only a wasted compile.
LITERAL_GROUPS: dict[int, tuple[tuple[str, ...], ...]] = {
    0: (("rm",),),
    1: (("remove-item",),),
    2: (("rd", "rmdir"), ("/s",)),
    3: (("git",), ("reset",)),
    4: (("git",), ("clean",)),
    5: (("git",), ("branch",)),
    6: (("git",), ("push",)),
    7: (("git",), ("push",)),
    8: (("git",), ("checkout",)),
    9: (("git",), ("checkout",)),
    10: (("git",), ("switch",)),
    11: (("git",), ("restore",)),
    12: (("git",), ("restore",)),
    13: (("curl", "wget", "iwr", "irm"),),
    14: (("cat", "type", "get-content", "gc", "head", "tail", "sed", "awk",
          "base64", "xxd", "strings", "less", "more", "certutil"),
         (".env", ".ssh", "credential", "service", "id_rsa", "id_ed25519",
          ".pem", ".key")),
    15: (("rg", "grep", "findstr", "select-string", "more"),
         (".env", ".ssh", "credential", "service", "id_rsa", "id_ed25519",
          ".pem", ".key")),
    16: (("python", "py", "powershell", "pwsh", "cmd", "node", "ruby", "perl", "php"),
         (".env", ".ssh", "credential", "service", "id_rsa", "id_ed25519",
          ".pem", ".key")),
    # Rule 17, added 2026-07-31: a long foreground sleep chained into another command.
    # One literal is enough and more would be wrong. The prescan is a NECESSARY-condition
    # filter, so every literal here must appear in EVERY string the regex matches. "sleep"
    # does; the chaining character does not, because the regex accepts `;`, `&` or `|` and
    # a conjunction of disjunctions cannot express "one of these three punctuation marks"
    # without also matching commands that merely contain one.
    17: (("sleep",),),
}

HEADER = """// GENERATED from ~/.claude/hooks/safety_gate.py::RULES. Do not hand-edit.
//
// `pattern` is a byte-for-byte copy; inline flags (?i)/(?is) carry the Python flags.
//
// `literal_groups` is the PRESCAN, a conjunction of disjunctions: EVERY group must have at
// least one member present in the lowercased command before the pattern is worth compiling. Compiling all 17 patterns measured ~45 ms of the gate's ~49 ms
// on Linux, so skipping the ones that cannot match is where the remaining cost goes.
//
// Over-approximating a literal set is free (a wasted compile). UNDER-approximating silently
// skips a rule on a command it should block. regen_rules.py fuzzes every set before emitting
// this file and refuses to write if `pattern.search(s)` ever holds with no literal present.
//
// Regenerate with tools/hookgate/regen_rules.py after any change to safety_gate.py, then
// re-run tools/hookgate/diff_oracle.py, which is the only thing proving the engines agree.

pub struct Rule {
    pub pattern: &'static str,
    pub reason: &'static str,
    pub literal_groups: &'static [&'static [&'static str]],
}

pub const RULES: &[Rule] = &[
"""


def rust_raw(s: str) -> str:
    """Emit a Rust raw string literal with enough hashes to be unambiguous.

    A pattern containing `"#` would terminate an `r#"..."#` literal early, so the hash count
    is derived from the longest run of `#` actually present rather than fixed.
    """
    longest = max((len(m) for m in re.findall(r"#+", s)), default=0)
    return 'r{h}"{body}"{h}'.format(h="#" * (longest + 1), body=s)


def load_rules():
    path = SAFETY_GATE if SAFETY_GATE.exists() else FALLBACK
    if not path.exists():
        raise SystemExit("no safety_gate.py at {} or {}".format(SAFETY_GATE, FALLBACK))
    spec = importlib.util.spec_from_file_location("_safety_gate_for_codegen", path)
    if spec is None or spec.loader is None:
        raise SystemExit("could not import {}".format(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return path, mod.RULES


def fuzz_candidates(rules) -> list[str]:
    """Strings likely to match the rules, so the soundness check is not vacuous.

    A fuzz over random noise would almost never match a rule and would therefore prove
    nothing. These are built to HIT: real corpus lines, then mutations that keep the
    dangerous shape while perturbing spacing, case, quoting and separators.
    """
    rng = random.Random(20260730)  # fixed seed: a soundness check must be reproducible
    base: list[str] = []
    if CORPUS.exists():
        base = [c for c in CORPUS.read_text(encoding="utf-8").splitlines() if c.strip()]

    out = list(base)

    # Case perturbation: every pattern is case-insensitive, and the prescan lowercases, so a
    # mismatch here would mean the prescan and the pattern disagree about case.
    for s in base:
        out.append(s.upper())
        out.append(s.title())
        out.append("".join(c.upper() if rng.random() < 0.5 else c for c in s))

    # Whitespace and quoting perturbation around the same tokens.
    for s in base:
        out.append(s.replace(" ", "  "))
        out.append(s.replace(" ", "\t"))
        out.append("  " + s)
        out.append(s + " ")
        out.append(s.replace("/", "\\"))

    # Chained commands, which is how a dangerous token most often hides.
    for a, b in itertools.islice(itertools.product(base, base), 0, 4000, 7):
        out.append("{} && {}".format(a, b))
        out.append("{} ; {}".format(a, b))
        out.append("echo ok | {}".format(b))

    # Prefix/suffix noise, to catch a literal that only appears by accident of position.
    for s in base:
        out.append("cd /tmp && " + s)
        out.append(s + " # trailing comment")

    return out


def verify_literals(rules) -> list[str]:
    """Return counterexamples proving a group set is unsound. Empty means sound."""
    failures: list[str] = []

    for i in sorted(set(range(len(rules))) - set(LITERAL_GROUPS)):
        failures.append(
            "rule {} has no literal groups; add groups or an empty tuple to opt out".format(i)
        )

    for i in sorted(set(LITERAL_GROUPS) - set(range(len(rules)))):
        failures.append(
            "LITERAL_GROUPS has entry {} but there are only {} rules".format(i, len(rules))
        )

    candidates = fuzz_candidates(rules)
    for i, (pattern, _reason) in enumerate(rules):
        groups = LITERAL_GROUPS.get(i)
        if not groups:
            continue  # no groups means "always compile", sound by construction
        counterexample = None
        for s in candidates:
            if not pattern.search(s):
                continue
            low = s.lower()
            # EVERY group must contribute. One group with nothing present proves the prescan
            # would skip a rule that does in fact match, which is the silent hole.
            for gi, group in enumerate(groups):
                if not any(l in low for l in group):
                    counterexample = (gi, group, s)
                    break
            if counterexample:
                break
        if counterexample:
            gi, group, s = counterexample
            failures.append(
                "rule {} UNSOUND: pattern matches but group {} {} contributes nothing\n"
                "    command: {!r}".format(i, gi, group, s[:160])
            )

    # A member that is empty or uppercase would never match a lowercased haystack.
    for i, groups in LITERAL_GROUPS.items():
        for gi, group in enumerate(groups or ()):
            if not group:
                failures.append(
                    "rule {} group {} is empty, which can never match".format(i, gi)
                )
            for member in group:
                if not member:
                    failures.append("rule {} group {} has an empty member".format(i, gi))
                elif member != member.lower():
                    failures.append(
                        "rule {} group {} member {!r} is not lowercase".format(i, gi, member)
                    )

    return failures


def render(rules) -> str:
    body = [HEADER]
    for i, (pattern, reason) in enumerate(rules):
        groups = LITERAL_GROUPS.get(i, ())
        group_src = ", ".join(
            "&[{}]".format(", ".join(rust_raw(m) for m in group)) for group in groups
        )
        body.append(
            "    Rule {{\n"
            "        pattern: {},\n"
            "        reason: {},\n"
            "        literal_groups: &[{}],\n"
            "    }},\n".format(rust_raw(pattern.pattern), rust_raw(reason), group_src)
        )
    body.append("];\n")
    return "".join(body)


def main() -> int:
    path, rules = load_rules()
    args = sys.argv[1:]

    failures = verify_literals(rules)
    if failures:
        print("PRESCAN SOUNDNESS FAILED. Not writing rules.rs.")
        print("A skipped rule is a silent security hole, so this is fatal, not a warning.\n")
        for f in failures:
            print("  " + f)
        return 1
    print("prescan soundness: {} rules, all groups verified against {} fuzz candidates".format(
        len(rules), len(fuzz_candidates(rules))))

    if "--verify-only" in args:
        return 0

    text = render(rules)
    if "--check" in args:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current == text:
            print("rules.rs is current ({} rules from {})".format(len(rules), path))
            return 0
        print("STALE: src/rules.rs does not match {}".format(path))
        print("Run: python tools/hookgate/regen_rules.py, then the differential oracle.")
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print("wrote {} with {} rules from {}".format(OUT, len(rules), path))
    print("NOW RUN: python tools/hookgate/diff_oracle.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
