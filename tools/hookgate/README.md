# hookgate

The `PreToolUse` deny rules, compiled. Replaces two Python hook processes on the hot path
of every `Bash` tool call.

## Why it exists

### Read the correction first

An earlier version of this file claimed 14.85 ms and a 16.3x improvement. **Both were
wrong**, and the error is worth recording because it is the kind that survives review.

That benchmark fed the binary a payload, timed it, and got a number consistent with pure
process spawn. The measurement was real; the interpretation was not. `main` returns early
on a JSON parse failure, and it returns early *before* `compiled()` is ever called, so the
regexes were never built. The benchmark had been timing the bail-out path and reporting it
as the gate.

What exposed it: a payload of `{"a":1}`, with no command at all, cost 90 ms. A gate that is
fast on a real command cannot be slow on an empty one. That asymmetry only makes sense if
the fast case was not doing the work.

The lesson generalises past this file. **A performance measurement needs to prove the code
under test actually ran.** Timing alone cannot distinguish "fast" from "skipped", and the
faster the number looks, the more likely it is the second one.

### Measured, 2026-07-30, native process creation, warm, valid payload

| | Windows median | Linux median |
|---|---|---|
| empty `main`, spawn floor | 21.72 ms | 1.27 to 1.46 ms |
| compile the 17 patterns, isolated | 101.31 ms | 47.09 ms |
| gate BEFORE the prescan, real payload | 91.87 ms | 49.01 ms |
| **gate AFTER the prescan, ordinary command** | **19.06 ms** | **2.26 ms** |
| `safety_gate.py` | 106.56 ms | not measured |
| `pre_push_gate.py` | 135.92 ms | not measured |
| **both Python hooks, as configured** | **242.5 ms per Bash call** | not measured |

Eager compilation gave ~2.6x on Windows and ~4.9x on Linux, not the 16.3x first claimed. With
the prescan it is **~12.7x on Windows and ~107x on Linux** for an ordinary command. See the
prescan section for the per-payload breakdown and for why that number is the dangerous one to
get wrong.

### The cost that eager compilation exposed

Isolating the terms on Linux: `/bin/true` 1.08 ms, Rust empty `main` 1.46 ms, compile the
17 patterns and exit 47.09 ms, the eager gate 49.01 ms. **Roughly 45 ms of that 49 ms was
building the patterns**, redone on every single invocation.

This reversed the conclusion the crate was first designed around. Process spawn was the whole
problem in the Python configuration, and eliminating it exposed a larger cost underneath.
Linux spawn is 1.46 ms exactly as projected; the projection of a ~2 ms total gate was wrong by
25x because pattern compilation was never measured. The prescan below is what closed the gap,
and it lands the ordinary case at 2.26 ms, which is where the original projection expected the
whole gate to be.

`fancy-regex` is implicated. It builds a backtracking VM for patterns containing lookaround
rather than delegating to the `regex` crate's automata, and six of the seventeen rules need
lookaround. The lookaround requirement is real (see below), so the fix is not to swap the
engine.

### The prescan, built and measured

**Do not compile what cannot match.** Every rule has a precondition expressible as literals:
rule 3 needs both `git` and `reset`; rule 16 needs an interpreter name *and* a
credential-shaped path. `literal_groups` in the generated `rules.rs` encodes that as a
conjunction of disjunctions, and `first_match` skips any rule whose groups are not all
satisfied by a substring test over the lowercased command.

Linux, after (400 runs each, `rust empty main` floor 1.27 ms):

| payload | before prescan | after |
|---|---|---|
| `echo hello` | 49.01 ms | **2.26 ms** |
| `ls -la` | 49.01 ms | **2.50 ms** |
| `python -m pytest -q` | 49.01 ms | **2.01 ms** |
| a `git reset --hard` | 49.01 ms | **2.25 ms** |
| a credential-exposure command | 49.01 ms | 8.34 ms |
| empty command | 49.01 ms | 1.90 ms |

Against the 242.5 ms Python pair that is **~107x for ordinary commands** (242.5 / 2.26), and everything
except an actual credential-exposure command now sits at the process-spawn floor. That last
row still compiles the largest pattern in the set, which is the correct trade: the one class
of command that looks dangerous is the one worth spending 8 ms on.

A flat any-of list was measured first and was not good enough. `python -m pytest` cost
9.09 ms because `python` alone admitted rule 16, and any `git` command admitted all ten git
rules. Those are the two most common command shapes in this repository, which is what
motivated the conjunctive form.

### The prescan is not a new idea, and one search changed the design

The prior-art gate fired on a response that presented this as a design of its own. It is not.
Full record with queries and sources in `docs/prior-art/tools-hookgate.json`; the short version:

**Literal prefiltering is standard and decades old**, and it ships inside the engines this
crate already depends on. `regex-automata` has a whole prefilter module including an
Aho-Corasick prefilter for alternations, and RE2, Hyperscan and GNU grep all do a version of it.

**The closest analogue is the same problem and the same solution.** Coraza, a
ModSecurity-compatible WAF, loads hundreds of `@rx` rules evaluated per request, and its
PR #1534 adds compile-time pattern analysis to build cheap pre-checks that skip evaluation
when the input clearly cannot match, returning **maybe-match on any uncertainty**. That is
this crate's over-approximate-never-under-approximate invariant, arrived at independently,
which makes it worth strictly less. Nothing in the technique here is original.

**What the search actually changed.** Coraza derives its pre-checks **mechanically from the
pattern AST**, so soundness follows from the analysis. This crate derives them by hand into
`LITERAL_GROUPS` and then fuzzes them, which is a weaker guarantee: a fuzz can only fail on a
case the corpus reaches. Mechanical derivation is the better design and is now filed as
`improvement_owed`.

`regex_syntax::hir::literal::Extractor` was the obvious tool for that and does not fit, for
two reasons that were checked rather than assumed. It extracts **prefix or suffix** sequences
only, so it would reproduce group 0 (`git`, `rm`) but not group 1 (`reset`, a
credential-shaped path), and group 1 is where the measured win came from. And it parses
regex-crate syntax, so it rejects the 6 lookaround rules outright, which are the ones most in
need of help. The remaining path is walking `fancy_regex::Expr` for those 6.

### Why the prescan is the most dangerous code here, and what holds it

The asymmetry is the whole design. Over-approximating a group costs a wasted compile.
**Under-approximating skips a rule on a command it should block, and nothing reports it**:
every test still passes, every benchmark improves, and the guard is quietly weaker. It is the
one optimisation in this crate that can create a security hole while looking like a win.

So the groups are not trusted because they were read carefully:

1. `regen_rules.py` **fuzzes every group before writing `rules.rs`** and refuses to emit if
   any candidate exists where the pattern matches but a group contributes nothing. 3,069
   candidates, built from the corpus plus case, whitespace, quoting, separator and
   command-chaining mutations, with a fixed seed so the check is reproducible.
2. **The verifier is mutation-tested.** Eight controls, all passing: a bogus extra group on
   rules 3, 6 and 16 is caught; a credential group narrowed to only `.env` is caught; an
   empty group and an uppercase member are rejected; and *weakening* a group set is correctly
   NOT reported, since dropping a group only causes extra compiles.
3. `tests/test_hookgate.py` runs both the soundness check and its own mutation test, so this
   is enforced by the suite rather than only by the generator.
4. The **differential oracle** still shows exact agreement with Python on all 123 commands,
   on both the Windows and the Linux build, after the prescan.

Note the deliberate limit: nothing re-checks soundness at runtime, because a runtime check
would mean compiling the pattern, which is the cost being avoided. The guarantee is entirely
build-time and test-time.

### Alternatives measured and rejected

Merging the two Python hooks into one process with `-S -E` reaches 82 ms. Real, and worse
than compiling. A resident daemon reached by a thin client is pointless once the client
spawn is 1.46 ms: the IPC saves nothing worth fighting the spawn-per-call hook protocol for.

## Why `fancy-regex` and not `regex`

Rust's `regex` crate has no lookahead or lookbehind, by design, because that is how it
guarantees linear-time matching. Six of the seventeen ported rules need lookaround. One of
them uses a negative lookahead to permit the staged-only form of a git subcommand while
blocking every other form of it, and hand-rewriting that to avoid lookaround would change
what a safety guard permits. So the patterns are copied verbatim and matched by an engine
that supports them. The cost is a backtracking engine, paid on inputs that are single
shell command lines.

## What is and is not ported

The deny rules are here. `pre_push_gate.py` is **not**: it is git-repository inspection and
evidence binding, and it only ever acts on a command matching its `PUSH` regex. Push
commands are delegated to it unchanged, over stdin, with the original bytes. The hot path
therefore never imports `subprocess`, never shells out to git, and never touches the
filesystem, while the cold path's logic stays Python rather than being reimplemented blind.

## Correctness

`src/rules.rs` is **generated**, never hand-edited, by `regen_rules.py` reading
`safety_gate.py::RULES`. That removes transcription error but proves nothing on its own:
byte-identical patterns are necessary and not sufficient, because Python's `re` and
`fancy-regex` are different engines that can disagree on lookaround, on `$` under DOTALL,
and on Unicode word boundaries.

The differential oracle is what establishes agreement. Both sides answer the same question
for each command, the index of the first matching rule or -1, over `corpus.txt`:

```bash
python tools/hookgate/diff_oracle.py
```

Current result: **exact agreement on 123 commands, 86 blocks per side, zero disagreements**
in either direction. The two directions are counted separately on purpose, because Python
blocking where Rust does not is a security regression while the reverse is only a nuisance.

After any change to `safety_gate.py`, regenerate and re-run the oracle. A regenerated
`rules.rs` with no oracle run is not evidence of anything.

## Status

**Not deployed.** The binary is built and verified but `settings.json` still invokes the
two Python hooks. Wiring it in is a live-config change, and the Linux build is blocked on
`sudo apt install build-essential` in the WSL2 distro (rustc has no linker there yet).

## Build

```bash
cargo build --release              # Windows: target/release/hookgate.exe
cargo build --release --target x86_64-unknown-linux-gnu   # needs a cc in the distro
```
