"""Literate CLI snapshot tests: a Python port of the `.trycmd` mechanism.

WHY THIS EXISTS. Five tools in this repo carry a hand-rolled `selftest`
subcommand (gate, panel, codemap, bus, docmap). Every one of them asserts on
INTERNAL FUNCTIONS in-process. Not one of them executes its own command line.
So the argparse contract, the exit codes, the error text a human actually sees,
and the `--help` surface are unverified in a repo whose entire purpose is
verification. That is the gap this fills, and it does not overlap the selftests:
they check derivations, this checks the process boundary.

WHAT WAS TAKEN, AND FROM WHERE. The mechanism is absorbed from `trycmd` v1.2.1
(crates.io, 1.4M recent downloads, MIT/Apache-2.0) and its matching engine from
`snapbox` v0.6.21. Rust source read:

  trycmd-1.2.1/src/schema.rs:186-336   `parse_trycmd`, the fenced-block grammar
  trycmd-1.2.1/src/schema.rs:875-900   `CommandStatus` and its FromStr
  trycmd-1.2.1/src/schema.rs:124       `overwrite`, the update mode
  trycmd-1.2.1/src/runner.rs:460-490   `validate_streams`, newline filter first
  snapbox-0.6.21/src/filter/pattern.rs:520-605  `normalize_to_pattern`,
                                       `is_line_elide`, `line_matches`

No Rust code was vendored and no dependency was added: this is a port of the
grammar and the matcher into stdlib Python, because our CLIs are Python and a
second Rust crate would need a second cargo build in the gate for a test
harness. `tools/hookgate` is Rust because it is a hot-path hook measured in
milliseconds; a snapshot runner has no such argument.

DELIBERATE DIVERGENCES FROM UPSTREAM.
  - Upstream resolves the first token through a `[[bin]]` table. Here it is
    resolved as: `python` -> sys.executable, anything else -> PATH. Repo-relative
    paths in args are made absolute against the project root.
  - Upstream merges stderr into stdout for `.trycmd` blocks and so does this.
    Interleaving is not deterministic, which is why upstream only offers the
    merged stream in the literate format, and splitting them here would invent a
    guarantee the mechanism does not have.
  - `[EXE]` is added, absent upstream in this form: it expands to `.exe` on
    Windows and nothing elsewhere. This tree runs on Windows and CI runs Linux,
    and the reflection of 2026-07-30 records three CRLF-versus-LF false results
    already paid for. Newlines are normalized to LF before comparison for the
    same reason.
  - `CommandStatus::Interrupted` and `Skipped` are not ported. Neither is
    expressible in a `subprocess.run` result on Windows, and a status value that
    can never be produced is a false affordance.

THE FORMAT. Inside a fenced block (```, ```console or ```trycmd):

    $ python tools/docmap/docmap.py bogus
    ? 2
    usage: docmap.py [..]
    ...

  `$ ` starts a command, `> ` continues it, `? <code|success|failed>` declares
  the exit status (default success), every following line is expected output.
  `[..]` matches any run of characters within a line; a bare `...` line elides
  any number of lines. Both come from snapbox and both are load-bearing here,
  because argparse wraps `--help` to the terminal width and that width is not
  ours to fix.

MODES. `check` verifies. `overwrite` rewrites the expected output and status
lines in place from what actually ran, which is upstream's `TRYCMD=overwrite`.
An overwrite is how a snapshot suite stops being a wall of hand-maintained
strings, and it is also how a suite silently stops testing anything, so it is a
separate mode a human has to type and never something `check` does on failure.
"""
from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

FENCE_LANGS = ("", "trycmd", "console")


class ParseError(ValueError):
    """A .trycmd file whose grammar is wrong. Not a test failure, a file bug."""


class Step:
    """One `$ command` and everything expected of it."""

    __slots__ = ("bin", "args", "env", "status", "expected", "cmd_line",
                 "status_line", "out_start", "out_end")

    def __init__(self, bin_, args, env, status, expected, cmd_line,
                 status_line, out_start, out_end):
        self.bin = bin_
        self.args = args
        self.env = env
        self.status = status          # int, or None meaning "nonzero"
        self.expected = expected      # str, LF-normalized, no trailing newline
        self.cmd_line = cmd_line      # 1-based line of the `$ ` line
        self.status_line = status_line  # 1-based line of `? `, or None
        self.out_start = out_start    # 1-based, inclusive
        self.out_end = out_end        # 1-based, exclusive

    def render_cmd(self) -> str:
        parts = ["{}={}".format(k, v) for k, v in sorted(self.env.items())]
        parts.append(self.bin)
        parts.extend(self.args)
        return " ".join(parts)


def parse_status(raw: str) -> int | None:
    """Port of CommandStatus::from_str (schema.rs:884), minus the two unportable arms."""
    raw = raw.strip()
    if raw == "success":
        return 0
    if raw == "failed":
        return None
    try:
        return int(raw)
    except ValueError:
        raise ParseError("Expected an exit code, got {}".format(raw))


def render_status(status: int | None) -> str:
    return "failed" if status is None else str(status)


def parse(text: str) -> list[Step]:
    """Port of TryCmd::parse_trycmd (schema.rs:186).

    Same state machine: find a fence, read `$`/`>`/`?`, then consume lines as
    expected output until the next `$` or the closing fence.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    steps: list[Step] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        i += 1
        if not line.startswith("```"):
            continue
        tick_end = len(line) - len(line.lstrip("`"))
        fence = line[:tick_end]
        info = line[tick_end:].strip()
        lang = info.split(",")[0]
        attrs = info.split(",")[1:]
        if lang not in FENCE_LANGS or "ignore" in attrs:
            while i < n and not lines[i].startswith(fence):
                i += 1
            i += 1
            continue

        while i < n:
            if lines[i].startswith(fence):
                i += 1
                break
            cmd_line = i + 1
            raw = lines[i]
            if not raw.startswith("$ "):
                raise ParseError("Expected `$` on line {}, got `{}`".format(cmd_line, raw))
            words = shlex.split(raw[2:].strip(), posix=True)
            i += 1
            while i < n and lines[i].startswith("> "):
                words.extend(shlex.split(lines[i][2:].strip(), posix=True))
                i += 1

            status: int | None = 0
            status_line = None
            if i < n and lines[i].startswith("? "):
                status_line = i + 1
                status = parse_status(lines[i][2:])
                i += 1

            out_start = i + 1
            body: list[str] = []
            while i < n and not lines[i].startswith("$ ") and not lines[i].startswith(fence):
                body.append(lines[i])
                i += 1
            out_end = i + 1

            env: dict[str, str] = {}
            while words and "=" in words[0] and not words[0].startswith("="):
                key, _, value = words[0].partition("=")
                if "/" in key or "\\" in key:
                    break
                env[key] = value
                words.pop(0)
            if not words:
                raise ParseError("No bin specified on line {}".format(cmd_line))

            steps.append(Step(words[0], words[1:], env, status, "\n".join(body),
                              cmd_line, status_line, out_start, out_end))
    return steps


def line_matches(actual: str, expected: str) -> bool:
    """Port of snapbox pattern.rs:582 `line_matches`. `[..]` is the wildcard."""
    if actual == expected:
        return True
    sections = expected.split("[..]")
    for idx, section in enumerate(sections):
        if not actual.startswith(section):
            return False
        remainder = actual[len(section):]
        if idx + 1 == len(sections):
            return not remainder
        nxt = sections[idx + 1]
        if not nxt:
            actual = ""
        else:
            found = remainder.find(nxt)
            actual = remainder[found:] if found >= 0 else remainder
    return False


def normalize(actual: str, expected: str) -> str:
    """Port of snapbox pattern.rs:520 `normalize_to_pattern`.

    Rewrites `actual` toward `expected` wherever the pattern legitimately
    matches, so that an equality check afterwards is exact and any diff shown to
    a human is the real difference and not a wildcard.
    """
    if "[..]" not in expected and "..." not in expected:
        return actual
    actual_lines = actual.split("\n")
    expected_lines = expected.split("\n")
    out: list[str] = []
    ai = 0
    for ei, exp in enumerate(expected_lines):
        if exp.strip() == "..." :
            nxt = expected_lines[ei + 1] if ei + 1 < len(expected_lines) else None
            if nxt is None:
                out.append(exp)
                ai = len(actual_lines)
                break
            offset = None
            for probe in range(ai, len(actual_lines)):
                if line_matches(actual_lines[probe], nxt):
                    offset = probe
                    break
            if offset is None:
                break
            out.append(exp)
            ai = offset
        else:
            if ai >= len(actual_lines):
                break
            if line_matches(actual_lines[ai], exp):
                out.append(exp)
            else:
                out.append(actual_lines[ai])
            ai += 1
    out.extend(actual_lines[ai:])
    return "\n".join(out)


def redactions(project: Path) -> dict[str, str]:
    return {
        "[ROOT]": str(project),
        "[CWD]": str(Path.cwd()),
        "[EXE]": ".exe" if os.name == "nt" else "",
    }


def apply_redactions(text: str, subs: dict[str, str]) -> str:
    for token, value in subs.items():
        if value:
            text = text.replace(value, token)
    return text


def resolve_bin(name: str, project: Path) -> str | None:
    if name == "python":
        return sys.executable
    found = shutil.which(name)
    if found:
        return found
    candidate = project / name
    return str(candidate) if candidate.exists() else None


def run_step(step: Step, project: Path) -> tuple[int, str]:
    exe = resolve_bin(step.bin, project)
    if exe is None:
        return 127, "trycmd: binary not found: {}".format(step.bin)
    subs = redactions(project)
    args = []
    for arg in step.args:
        for token, value in subs.items():
            arg = arg.replace(token, value)
        args.append(arg)
    env = dict(os.environ)
    env.update(step.env)
    env["COLUMNS"] = env.get("TRYCMD_COLUMNS", "80")
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run([exe] + args, cwd=str(project), env=env,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    merged = (proc.stdout or "") + (proc.stderr or "")
    merged = merged.replace("\r\n", "\n").rstrip("\n")
    return proc.returncode, apply_redactions(merged, subs)


def check_step(step: Step, project: Path) -> list[str]:
    code, got = run_step(step, project)
    fails = []
    if step.status is None:
        if code == 0:
            fails.append("line {}: expected failure, got exit 0".format(step.cmd_line))
    elif code != step.status:
        fails.append("line {}: expected exit {}, got {}".format(
            step.cmd_line, step.status, code))
    normalized = normalize(got, step.expected)
    if normalized != step.expected:
        fails.append("line {}: output mismatch\n--- expected\n{}\n--- actual\n{}".format(
            step.out_start, step.expected, got))
    return fails


def rewrite(text: str, path: Path, project: Path) -> str:
    """Port of TryCmd::overwrite (schema.rs:124): splice real output back in.

    Walked back-to-front so earlier line spans stay valid as later ones resize.
    """
    steps = parse(text)
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.replace("\r\n", "\n").split("\n")
    for step in reversed(steps):
        code, got = run_step(step, project)
        body = normalize(got, step.expected)
        if body != step.expected:
            body = got
        lines[step.out_start - 1:step.out_end - 1] = body.split("\n") if body else []
        if step.status_line is not None:
            if code == 0:
                del lines[step.status_line - 1]
            else:
                lines[step.status_line - 1] = "? " + render_status(code)
        elif code != 0:
            lines.insert(step.cmd_line, "? " + render_status(code))
    return newline.join(lines)


def cases(project: Path, paths: list[str]) -> list[Path]:
    if paths:
        return [Path(p) if Path(p).is_absolute() else project / p for p in paths]
    # Two shapes are real: this repo's own cases live at engine/tests/cmd (moved
    # 2026-08-24), but trycmd.py also runs against synthetic fixture projects built
    # from scratch with a plain tests/cmd, so both are tried rather than picked.
    for rel in (("engine", "tests", "cmd"), ("tests", "cmd")):
        found = sorted((project.joinpath(*rel)).glob("*.trycmd"))
        if found:
            return found
    return []


def run_check(project: Path, paths: list[str], verbose: bool) -> int:
    files = cases(project, paths)
    if not files:
        print("trycmd: no cases found")
        return 1
    total = 0
    failed = 0
    for path in files:
        try:
            steps = parse(path.read_text(encoding="utf-8"))
        except (ParseError, OSError) as exc:
            # A harness that skips files it cannot read reports green on an empty
            # suite, so an unreadable case is a failure and not a warning.
            total += 1
            failed += 1
            print("FAIL {}: {}".format(path.name, exc))
            continue
        for step in steps:
            total += 1
            fails = check_step(step, project)
            if fails:
                failed += 1
                print("FAIL {}:{}  $ {}".format(path.name, step.cmd_line, step.render_cmd()))
                for f in fails:
                    print("  " + f.replace("\n", "\n  "))
            elif verbose:
                print("ok   {}:{}  $ {}".format(path.name, step.cmd_line, step.render_cmd()))
    print("trycmd: {} step(s), {} failed".format(total, failed))
    return 1 if failed else 0


def run_overwrite(project: Path, paths: list[str]) -> int:
    files = cases(project, paths)
    for path in files:
        path.write_text(rewrite(path.read_text(encoding="utf-8"), path, project),
                        encoding="utf-8")
        print("overwrote {}".format(path))
    return 0


def selftest(project: Path) -> int:
    """Prove the grammar and the matcher. Exit code is the failure count."""
    fails: list[str] = []

    def check(label, got, want):
        if got != want:
            fails.append("{}: got {!r} want {!r}".format(label, got, want))

    # Grammar. Each of these is a case upstream carries a #[test] for.
    check("empty", parse(""), [])
    check("empty fence", parse("```\n```\n"), [])
    steps = parse("```\n$ echo hello\n```\n")
    check("one step", (steps[0].bin, steps[0].args, steps[0].status), ("echo", ["hello"], 0))
    steps = parse("```\n$ cmd a\n> b c\n```\n")
    check("continuation joins args", steps[0].args, ["a", "b", "c"])
    steps = parse("```\n$ cmd\n? 2\nboom\n```\n")
    check("status code", (steps[0].status, steps[0].expected), (2, "boom"))
    check("status failed is any-nonzero", parse("```\n$ c\n? failed\n```\n")[0].status, None)
    steps = parse("```\n$ KEY=value cmd\n```\n")
    check("env prefix", (steps[0].env, steps[0].bin), ({"KEY": "value"}, "cmd"))
    check("non-trycmd lang ignored", parse("```python\n$ cmd\n```\n"), [])
    check("ignore attr honored", parse("```console,ignore\n$ cmd\n```\n"), [])
    check("prose outside fences ignored", parse("hello\n\n```\n$ c\n```\nbye\n")[0].bin, "c")
    check("two blocks", len(parse("```\n$ a\n```\ntext\n```\n$ b\n```\n")), 2)
    try:
        parse("```\nnot a command\n```\n")
        fails.append("a fenced non-command line must be a ParseError")
    except ParseError:
        pass

    # Matcher. The [..] cases are lifted from snapbox pattern.rs:610-640.
    check("exact", line_matches("hello", "hello"), True)
    check("wildcard whole line", line_matches("hello", "[..]"), True)
    check("wildcard empty", line_matches("", "[..]"), True)
    check("wildcard prefix", line_matches("hello world", "hello [..]"), True)
    check("wildcard middle", line_matches("hello world", "[..] world"), True)
    check("wildcard both", line_matches("abcde", "a[..]e"), True)
    check("mismatch", line_matches("hello", "goodbye"), False)
    check("prefix mismatch", line_matches("hello", "hell[..]x"), False)

    # normalize collapses only what legitimately matched; a real diff survives.
    check("normalize rewrites a match", normalize("exit code 37", "exit code [..]"),
          "exit code [..]")
    check("normalize keeps a mismatch", normalize("boom", "exit code [..]"), "boom")
    check("elide swallows lines",
          normalize("a\njunk\njunk\nz", "a\n...\nz"), "a\n...\nz")
    check("elide to end", normalize("a\nb\nc", "a\n..."), "a\n...")
    check("no pattern is identity", normalize("a\nb", "x\ny"), "a\nb")

    # Round trip: what parse reads, render_cmd writes back.
    check("render_cmd round trip", parse("```\n$ K=v cmd a b\n```\n")[0].render_cmd(),
          "K=v cmd a b")

    # The runner reaches a real process and reports its real code.
    code, out = run_step(parse('```\n$ python -c "print(1)"\n```\n')[0], project)
    check("real process exit", code, 0)
    check("real process stdout", out, "1")
    code, _ = run_step(parse('```\n$ python -c "raise SystemExit(3)"\n```\n')[0], project)
    check("real process nonzero", code, 3)
    _, out = run_step(parse('```\n$ python -c "import sys; sys.stderr.write(\'e\')"\n```\n')[0],
                      project)
    check("stderr merges into stdout", out, "e")
    check("missing binary is 127",
          run_step(parse("```\n$ definitely-not-a-real-binary\n```\n")[0], project)[0], 127)

    # check_step: THE comparison. Added 2026-07-31 after tools/audit/mutations/
    # trycmd.py found that removing the output comparison and removing the exit
    # code comparison both left this selftest green. Every check above proves a
    # part in isolation; nothing proved the part that puts them together, which
    # is the vacuous-pass failure this file's own docstring names as the strongest
    # objection to snapshot testing. A suite that stops comparing prints 0 failed.
    def one_step(src):
        return check_step(parse(src)[0], project)

    check("check_step passes a step whose output and status both match",
          one_step('```\n$ python -c "print(1)"\n1\n```\n'), [])
    mismatch = one_step('```\n$ python -c "print(1)"\n2\n```\n')
    check("check_step reports an output mismatch", len(mismatch), 1)
    check("check_step names the mismatch as one",
          bool(mismatch) and "output mismatch" in mismatch[0], True)
    wrong_code = one_step('```\n$ python -c "print(1)"\n? 3\n1\n```\n')
    check("check_step reports a wrong exit code", len(wrong_code), 1)
    check("check_step names the exit code as the reason",
          bool(wrong_code) and "expected exit 3" in wrong_code[0], True)
    check("check_step reports a command that was required to fail and did not",
          len(one_step('```\n$ python -c "print(1)"\n? failed\n1\n```\n')), 1)
    check("check_step accepts a wildcard that legitimately matched",
          one_step('```\n$ python -c "print(1)"\n[..]\n```\n'), [])

    for f in fails:
        print("[FAIL] " + f)
    print("trycmd selftest: {} checks failed".format(len(fails)))
    return len(fails)


def main() -> int:
    ap = argparse.ArgumentParser(description="Literate CLI snapshot tests (.trycmd).")
    ap.add_argument("mode", choices=("check", "overwrite", "selftest"))
    ap.add_argument("paths", nargs="*", help="case files; default tests/cmd/*.trycmd")
    ap.add_argument("--project", type=Path, default=Path.cwd())
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    project = a.project.resolve()
    if a.mode == "selftest":
        return 1 if selftest(project) else 0
    if a.mode == "overwrite":
        return run_overwrite(project, a.paths)
    return run_check(project, a.paths, a.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
