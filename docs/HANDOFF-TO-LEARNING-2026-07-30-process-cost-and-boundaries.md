# Handoff to Lane C (learning): process cost, boundaries, and how to measure them

- From: Lane A (harness, ~/claude-setup)
- To: Lane C (learning, daily-deep-learning)
- Date: 2026-07-30
- Trigger: the operator, at the end of a Lane A session, asked for this material as
  learning content, stating "I need to learn this hands down, I don't know OS at all."

Lane A does not author learning content (docs/charters.md). This is the raw material and
the dependency ordering. Shaping it into pages, cards, or a research ladder is Lane C's
call, and the rubric is Lane C's.

## Read this framing first, because it changes what the material is worth

The operator said he does not know OS. What this session actually produced is **systems
performance measurement**, which is one slice of operating systems and not the subject.
Presenting it as "OS" would misrepresent the coverage.

What the session genuinely covers: process creation, program loading and linking, the cost
of crossing a filesystem boundary, why a blocking gate cannot be parallelised, and the
methodology for measuring any of it.

What it does **not** touch, and what a real OS foundation needs: virtual memory and paging,
the scheduler beyond noticing it adds variance, filesystems as on-disk data structures,
interrupts and system-call mechanics from the kernel side, concurrency primitives, and
memory hierarchy. If Lane C builds a curriculum from this alone, it should be labelled
"systems performance", with the gaps above named as the sequel rather than left implicit.

The strong pedagogical asset here is that **every number below was measured on his own
machine, by him, in one session.** That is a better anchor than any textbook figure, and it
is reproducible on demand. The scripts are named at the end.

## The one result the whole session turns on

Two Python hook processes ran before every shell command the agent issued. They performed
about 11 ms of regular-expression work and cost **242 ms**. Replacing them with one compiled
binary brought that to **91.87 ms on Windows and 49.01 ms on Linux**: a real improvement of
roughly 2.6x and 4.9x, and far less than the session first believed.

Then the interesting part. Removing the process-startup cost **exposed a larger cost hiding
underneath it.** Of the 49 ms on Linux, only 1.46 ms is starting the program. About 45 ms is
**compiling the regular expressions**, rebuilt from scratch on every single invocation.

So the honest arc of the session is not "compiled code is faster". It is: a bottleneck was
measured, removed, and the removal revealed that the original diagnosis was incomplete. That
is the more useful thing to learn, and it is why item 7 below (measure the instrument, and
prove the code under test actually ran) is the rung that matters most.

RETRACTION, recorded rather than edited away. An earlier version of this document claimed
14.85 ms for the compiled gate and projected 1.7 ms under WSL2. The 14.85 ms measurement was
real but was **timing an early-return path**: the benchmark's payload failed JSON parsing, so
the program exited before compiling any patterns, and the number reported was bare process
spawn. The 1.7 ms projection was wrong by 25x because pattern compilation was never measured
at all. Both figures are corrected above. See item 7 for what caught it.

## Concepts in dependency order

Each item lists the measurement that motivates it, so nothing is taught as an assertion.

### 1. What actually happens when a program starts

The teachable unit: a process is not free. Creating one means the kernel allocating a
process structure, building an address space, loading an executable image, resolving
dynamic libraries, initialising a language runtime, and only then running `main`.

Measured, empty `main()` in three compiled languages on Windows:

| language | median | binary |
|---|---|---|
| Zig | 16.82 ms | 4.6 KB |
| Rust | 22.12 ms | 114 KB |
| Go | 24.56 ms | 1,171 KB |

The ordering is not about language speed. It is about **how much runtime each language
initialises before your code runs**. Go starts a goroutine scheduler and a garbage
collector. Rust initialises much less. Zig initialises almost nothing.

Then the interpreter comparison, same machine, same method:

| candidate | median |
|---|---|
| `python -S -E -c pass` | 44.09 ms |
| `python -c pass` | 146.74 ms |

**`-S` skips importing the `site` module**, which is what scans for installed packages and
`.pth` files. That single flag is worth 100 ms here. The lesson is that an interpreter's
startup is dominated by work that has nothing to do with your program.

### 2. Not all process creation is equal, and the gap is an OS design decision

Same compiled binary class, two operating systems:

| platform | compiled binary spawn |
|---|---|
| Windows (`CreateProcess`) | 16.8 to 24.6 ms |
| WSL2 Linux (`fork` + `exec`) | **1.67 ms** (min 1.03) |

Roughly **10x**, and it is architectural. Unix `fork` was designed to duplicate an existing
process cheaply using copy-on-write, then `exec` replaces the image. Windows `CreateProcess`
builds a new process from scratch every time and does considerably more setup work.

This is the single most transferable fact in the session: **the same program, doing the same
work, costs ten times more to start depending on the OS.**

A worthwhile exercise for Lane C: have the learner predict the direction of this gap before
seeing it, then measure. Most people guess wrong, or guess right for the wrong reason.

### 3. Crossing a filesystem boundary is not like using a filesystem

The same git repository, 5,763 files, three ways:

| operation | Windows native | WSL2 via `/mnt/c` | WSL2 ext4 |
|---|---|---|---|
| `git status` (warm) | 109 ms | **12,018 ms** | 69 ms |
| count all files | 291 ms | 3,549 ms | 23 ms |

**110x.** WSL2 does not mount the Windows drive natively. It reaches it over **9P (the Plan 9
Filesystem Protocol)**, the same mechanism behind the `\\wsl$` shares. Each Linux VFS request
is serialised into a 9P request, sent over a virtual network, and deserialised on the other
side, so every `stat()` becomes a round trip between two operating systems. `git status` does
thousands of `stat()` calls, which is why a tree walk is where this shows up worst.

The mechanism has no single agreed name. Practitioner sources describe it as the cost of
crossing the Windows/Linux boundary or simply "9P is slow"; Microsoft's own WSL issue tracker
carries it as a long-running known design tradeoff. The general principle is that an
operation whose cost is invisible at 10 microseconds becomes dominant at 3 milliseconds, and
the program doing it cannot tell anything changed. Nothing about git differed between those
columns.

RETRACTION, recorded rather than quietly edited. An earlier draft of this document named the
mechanism "syscall amplification" and presented that as an established concept. It is not.
Three searches found no such term in the literature. The real established term nearby is
**IO amplification** (read and write amplification), from Mohan et al., "Analyzing IO
Amplification in Linux File Systems" (APSys 2017, arXiv:1707.08514), and it measures
something different: how many more BYTES a filesystem reads or writes than the caller asked
for. What is described above is per-operation round-trip LATENCY, not byte volume. Teaching
the invented term would have taught a learner a word that no one else uses, attached to a
definition that collides with a real one. Lane C should teach "IO amplification" as its own
correct concept and keep it distinct from this.

**The boundary is directional, and this corrects the rule an earlier draft gave.** Windows
reading Linux files over `\\wsl$` is fast; Linux reading Windows files over `/mnt/c` is the
slow path. So the practical rule is not the symmetric "do not straddle" that was written
first. It is: **keep the working tree on ext4 under the Linux home, and reach it from Windows
if you must, never the reverse.** Direction matters, and the earlier phrasing was wrong.

### 4. A blocking gate cannot be made concurrent, and this is a definition not a limitation

The operator asked whether threading or load balancing would help. It cannot, and the
reasoning is worth teaching because it generalises far beyond this case.

The hook must return a decision **before** the command it guards may run. That is what a gate
is. Its latency is therefore unconditionally on the critical path, and there is nothing to
overlap it with.

The decisive arithmetic: running the two hooks in perfect parallel gives `max(211, 224) = 224
ms`. Merging them into one process gives 117 ms. **The best possible case for parallelism was
1.9x worse than removing one process.** When the cost is per-process overhead rather than
work, the fix is fewer processes, not more workers.

Related, and the same shape: a resident daemon reached by a thin client was considered and
rejected. Once the client costs 1.67 ms, the inter-process round trip saves nothing worth
having, because **the client's own startup is the cost, not the communication.**

### 5. Compilers need linkers, and a program is assembled not just translated

The WSL2 build failed with `linker cc not found`. `rustc` compiles source to object files
and then hands off to a **linker** to combine them with libraries into one executable. No
linker means no executable, no matter how correct the source is.

This is a small, concrete hook for teaching the compile pipeline: source, object files,
linking, loading, execution. The failure made a normally invisible stage visible.

### 6. Regex engines make a real computer-science trade, with a real consequence

This one is worth a whole page on its own, because it is theory that produced an engineering
decision under measurement.

Rust's `regex` crate does not support lookaround. That is not an omission, it is the price of
a guarantee: it compiles patterns to automata and matches in time linear in the pattern and
the input, so it cannot suffer catastrophic backtracking. Python's `re` and `fancy-regex` are
backtracking engines: they support lookaround and can, on adversarial input, blow up
exponentially. Go's RE2 makes the identical trade, which is worth mentioning because it shows
this is a family of designs rather than one crate's quirk.

Two accuracy corrections to how an earlier draft put this. The crate supports a **limited**
form of lookaround already, namely `^`, `$` and `\b`, so "cannot express lookaround at all"
was too strong. And the position is not frozen: there is active work on **unbounded
captureless lookbehind** that preserves the linear-time guarantee, so this should be taught
as a documented current trade rather than a permanent impossibility. The crate's maintainers
state that arbitrary lookaround is not planned because no efficient general implementation is
known, and they name `fancy-regex` as the intended escape hatch, which is exactly the choice
this session made independently.

This is well-trodden ground, not a finding. It is documented in the crate's own issue #618
and discussion #910 and has been debated publicly for years. Presenting the reasoning as an
insight of this session would be a novelty claim with extensive prior art against it.

Concretely, 6 of 17 security rules needed lookaround, including a negative lookahead that
permits one narrow form of a command while blocking every other form. Choosing the faster
engine would have required rewriting those patterns by hand, which would have silently
changed what a safety guard permits.

The transferable lesson: **the fast option is sometimes fast because it refuses to do
something you need.** Read what a tool cannot do before choosing it for speed.

### 7. Measure the instrument before trusting the measurement

The most important methodological item, and the operator is the one who caught it.

An earlier measurement put Python startup at 106 ms. Re-measured through a different path it
was **44 ms**. The first number was taken through Git Bash, which emulates Unix `fork` on
Windows through a compatibility layer, and that layer was adding **2.4x** to every result.
The tool being measured had not changed at all.

Teach alongside it:

- **Warm up before timing.** First runs pay cache and page-in costs that steady state does not.
- **Report median and minimum, not mean.** Spawn timings have a long right tail from
  antivirus scans and scheduler preemption, so the mean overstates typical cost and the
  minimum approximates the floor.
- **Absolute numbers drift; ratios survive.** The same Rust binary measured 22.12 ms and
  16.73 ms in two runs an hour apart. Any single figure from this session is soft to about
  25%. The orderings held every time.
- **Prove the code under test actually ran.** This is the one that bit hardest, and it should
  probably be the headline of the whole rung. The compiled gate measured 14.85 ms, which was
  believed for hours. It was timing an early-return path: the benchmark payload failed JSON
  parsing, so the program exited before building any patterns, and the number was bare
  process spawn wearing the label of the gate. What exposed it was a deliberately degenerate
  input, a payload with no command in it at all, which cost **90 ms**. Something fast on real
  work cannot be slow on nothing, and that asymmetry is only possible if the fast case
  skipped the work. Timing alone cannot tell "fast" from "did not run", and **the better the
  number looks, the more likely it is the second one.** A good habit falls out of this: always
  measure a case you know must be slow, and check that it is.
- **Isolate one variable.** To test whether Zig's advantage was real or an artifact of its
  4.6 KB binary, the binary was padded to 117 KB and re-measured. It cost 2.19 ms, so
  about 40% of the gap was file size feeding antivirus scan-on-execute, and 3.0 ms was
  genuine. Without that experiment the conclusion would have been wrong by nearly half.

That padding experiment is, on its own, a complete lesson in experimental design.

### 8. Git's remote-tracking refs are a local cache and lie by default

Three inventory passes reported repositories as safe to delete because they showed zero
unpushed commits. Every one of those numbers was read from **remote-tracking refs stored on
disk**, some of which had not been refreshed in months. `origin/main` is a local note about
what the remote looked like the last time someone asked.

After actually fetching, the picture changed materially: one repository had 4 unpushed
commits, another had 1, and one had **63 commits sharing no common ancestor with its
remote at all**, meaning its history had been rewritten and the local work existed nowhere
else.

Concepts to teach from this: the object store versus refs, what `fetch` does and does not
do, ahead/behind as a two-way comparison, reachability (is this commit contained in any
remote ref), and why a rewritten history produces branches with no shared ancestor.

The habit it should install: **"it is backed up" is a claim that needs a command, not a
memory.**

### 9. Append-only ledgers, hash chains, and why a rename could not rewrite history

A supporting but genuinely useful unit. Lane letters were renumbered, which made an
identifier collide with its own past: a record saying `lane: B` means one thing before the
change and another after.

The tempting fix, editing the old records, was refused for two reasons. One file is a
**hash chain**, where each record commits to its own contents and to the record before it,
so any edit breaks verification and the repair is indistinguishable from tampering. And
independently, editing history so a cosmetic rename looks tidy falsifies the record.

The fix was a resolver that requires each record's own timestamp, making the ambiguity
explicit instead of erased. Teachable concepts: append-only logs, tamper evidence versus
tamper prevention (a hash chain proves alteration, it does not prevent it and authenticates
nobody), and schema migration when identifiers are reused.

## Suggested shape, for Lane C to accept or discard

A dependency-ordered ladder, each rung ending in a prediction the learner makes **before**
running the measurement:

1. What a process costs (items 1 and 2). Predict the Windows-versus-Linux direction first.
2. Boundaries and syscall amplification (item 3). Predict the `/mnt/c` penalty's order of magnitude.
3. Where parallelism cannot help (item 4). Predict whether threading the two hooks helps.
4. Compile and link (item 5).
5. Automata versus backtracking (item 6). The only rung that is theory-first.
6. Measurement methodology (item 7). Best taught by reproducing the MSYS error, then correcting it.
7. Git refs as a cache (item 8).
8. Ledgers and hash chains (item 9).

Item 7 arguably belongs first, since it is the skill that makes the others trustworthy. Lane
C should decide. The argument for keeping it late is that a learner needs to have been
burned by a bad number before the methodology feels necessary rather than pedantic.

## Reproducible artifacts

All under `~/claude-setup` unless noted. The scratchpad scripts are session-local and should
be copied into the learning repo by Lane C if they are wanted, because the scratchpad is
temporary.

| what | where |
|---|---|
| Rust gate, the end product | `tools/hookgate/` (README carries the full measurement table) |
| Differential oracle, Rust versus Python | `tools/hookgate/diff_oracle.py` |
| Generated-rules check | `tools/hookgate/regen_rules.py --check` |
| Tests including "every rule is exercised" | `tests/test_hookgate.py` |
| Lane resolver and the collision problem | `tools/lib/lanes.py`, `tests/test_lane_renumber.py` |
| Renumber decision record | `docs/adr/0016-lane-letters-renumbered-a-through-d.md` |
| Spawn benchmarks, three languages | session scratchpad, `bench3.py` |
| WSL2 filesystem benchmark | session scratchpad, `bench_fs.sh` |
| WSL2 spawn floor | session scratchpad, `wslbench.py` |
| Push-safety audit across every repo | session scratchpad, `fetch_audit.sh` |

## Accuracy constraints on any content built from this

- Every figure is from one Windows 11 machine with Defender active, on 2026-07-30. Soft to
  about 25% run to run. Do not present any single number as a property of a language or an OS.
- The Linux build now exists and is measured: **49.01 ms**, of which 1.46 ms is spawn and
  about 45 ms is regex compilation. The earlier "roughly 2 ms" projection was wrong by 25x
  and is retracted above.
- The Rust gate is verified against its Python original on a 123-command corpus with exact
  agreement **on both platforms**, and it is **not deployed.** Do not describe it as in use.
- The fix for the 45 ms compile cost, a literal prescan so that ordinary commands compile no
  patterns at all, is **designed and not built**. Any figure for it is a projection.
- Nothing here establishes that Rust, Zig, or WSL2 is better in general. The finding is
  narrower and more useful: for programs that start, do microseconds of work, and exit,
  startup cost dominates everything else.

## Prior-art log

The Stop hook's prior-art gate fired on the first version of this handoff, correctly: it
asserted two absences from memory. Queries run 2026-07-30, logged beside the claims per
`prior-art-gate`.

| # | query | vocabulary | outcome |
|---|---|---|---|
| 1 | `rust regex crate lookahead lookbehind not supported linear time guarantee` | practitioner / product | Claim **upheld with two corrections**. `^`, `$`, `\b` are supported, and unbounded captureless lookbehind is in active development preserving linear time. `fancy-regex` is the maintainers' own named workaround. Documented in rust-lang/regex issue #618 and discussion #910. |
| 2 | `"syscall amplification" OR "system call amplification" filesystem performance established term` | academic | Claim **RETRACTED**. No such established term. Nearest real concept is IO amplification (Mohan et al., APSys 2017, arXiv:1707.08514), which measures byte volume rather than round-trip latency and is therefore a different thing. |
| 3 | `WSL2 /mnt/c slow filesystem performance 9p protocol why git status slow cross-OS` | practitioner / product | Measurement **corroborated**, mechanism named correctly as 9P serialisation per VFS request. Surfaced a fact this session had wrong: the boundary is **directional**, `\\wsl$` from Windows is fast while `/mnt/c` from Linux is slow. Corrected above. |

Not-a-gap signals checked. For claim 1 the signal fires hard: a years-long documented
discussion with an official recommended workaround is prior art, not a gap, so the reasoning
is presented as the crate's documented rationale and not as a finding. For claim 2 the signal
fires differently and worse: the concept exists under a different name meaning a different
thing, which is how an invented term survives review. No survey, awesome-list, workshop, or
benchmark family was found that treats the 9P round-trip cost as a named research problem;
it is engineering folklore plus a Microsoft issue tracker, and the handoff now says so
instead of dressing it up.

Sources: [rust-lang/regex issue #618](https://github.com/rust-lang/regex/issues/618),
[rust-lang/regex discussion #910](https://github.com/rust-lang/regex/discussions/910),
[fancy-regex docs](https://docs.rs/fancy-regex/),
[EPFL SystemF on adding lookbehinds to rust regex](https://systemf.epfl.ch/blog/rust-regex-lookbehinds/),
[Analyzing IO Amplification in Linux File Systems](https://arxiv.org/pdf/1707.08514),
[microsoft/WSL issue #4197](https://github.com/microsoft/WSL/issues/4197),
[microsoft/WSL issue #5103](https://github.com/microsoft/WSL/issues/5103),
[Faster git status under WSL2](https://markentier.tech/posts/2020/10/faster-git-under-wsl2/).

## Cross-lane note

Lane A owns the harness artifacts above and will keep them working. If Lane C wants any
scratchpad script preserved, say so and Lane A will land it in the repo, since the
scratchpad does not survive the session.
