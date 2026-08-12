//! PreToolUse gate: the deny rules of safety_gate.py, in Rust.
//!
//! WHY THIS EXISTS. Measured 2026-07-30, native process creation, warm, valid payload: the
//! two Python PreToolUse hooks cost ~242 ms on EVERY Bash tool call. This binary costs
//! 91.87 ms on Windows and 49.01 ms on Linux, so ~2.6x and ~4.9x.
//!
//! AN EARLIER VERSION OF THIS COMMENT CLAIMED 16.7 ms AND 1.67 ms. Both were wrong, and the
//! error is instructive. That benchmark's payload failed JSON parsing, so `main` returned at
//! the parse guard BEFORE `compiled()` was ever reached, and the number reported was bare
//! process spawn wearing the label of the gate. A payload with no command in it at all costs
//! 90 ms, and something fast on real work cannot be slow on nothing.
//!
//! WHAT THE REAL COST WAS. Term isolation on Linux: /bin/true 1.08 ms, Rust empty main
//! 1.46 ms, compiling the 17 patterns and exiting 47.09 ms, the eager version of this binary
//! 49.01 ms. So ~45 ms of the 49 ms was BUILDING THE PATTERNS, redone on every invocation.
//! Removing the Python process-startup cost exposed a larger cost underneath it.
//!
//! THE PRESCAN, now built. See `first_match`. A command containing none of a rule's trigger
//! literals cannot match it, so the pattern is never compiled. Ordinary commands compile
//! nothing. The literal sets are fuzz-verified in regen_rules.py before rules.rs is written,
//! and that verifier is mutation-tested against five deliberately unsound sets, because an
//! under-approximated literal skips a rule silently.
//!
//! WHY fancy-regex AND NOT regex. Rust's `regex` crate deliberately has no lookahead or
//! lookbehind, which is how it guarantees linear time. Six of the seventeen ported rules
//! depend on lookaround, including a negative lookahead that permits the staged-only form
//! of one git subcommand while blocking every other form of it. Rewriting those patterns
//! by hand to avoid lookaround would change the semantics of a safety guard, so the
//! patterns are copied verbatim and matched by an engine that supports them.
//!
//! WHAT IS AND IS NOT PORTED. The deny rules are here. pre_push_gate.py is NOT: it is
//! git-repository inspection and evidence binding, and it only ever acts on a command
//! matching PUSH. Those commands are delegated to it unchanged. That keeps the hot path
//! compiled and leaves the cold path's logic untouched rather than reimplemented blind.
//!
//! CORRECTNESS. src/rules.rs is generated, never hand-written, and the differential
//! oracle is the only thing that establishes agreement with Python. `--diff-mode` reads
//! one command per line and prints the index of the first matching rule, or -1, which is
//! exactly what the Python side can be made to print for the same corpus.

mod rules;

use std::io::{self, Read, Write};
use std::path::PathBuf;
use std::process::{Command, Stdio};

/// Where `pre_push_gate.py` lives on THIS machine.
///
/// Order: `$CLAUDE_CONFIG_DIR/hooks`, then `$HOME/.claude/hooks`, then the Windows tree
/// reachable from WSL. Each candidate must actually exist; a missing path is skipped
/// rather than returned, so the delegate is never a name for nothing.
///
/// When nothing resolves, the last candidate is returned anyway and the spawn fails,
/// which `main` already handles by failing OPEN with a note on stderr. That is the
/// deliberate direction: this binary must never block a push because it could not find
/// its own inspector, and a note the operator can read beats a guard that stops work.
fn push_delegate() -> String {
    let mut candidates: Vec<PathBuf> = Vec::new();
    if let Ok(dir) = std::env::var("CLAUDE_CONFIG_DIR") {
        candidates.push(PathBuf::from(dir).join("hooks").join("pre_push_gate.py"));
    }
    if let Ok(home) = std::env::var("HOME") {
        candidates.push(
            PathBuf::from(home).join(".claude").join("hooks").join("pre_push_gate.py"),
        );
    }
    candidates.push(PathBuf::from("/mnt/c/Users/shova/.claude/hooks/pre_push_gate.py"));

    for c in &candidates {
        if c.is_file() {
            return c.to_string_lossy().into_owned();
        }
    }
    candidates
        .last()
        .map(|p| p.to_string_lossy().into_owned())
        .unwrap_or_default()
}

use fancy_regex::Regex;

/// Same trigger as pre_push_gate.py::PUSH. Kept identical so the delegation boundary
/// matches the guard's own idea of what a push is.
const PUSH: &str = r"(?i)\bgit\b[^\r\n;&|]{0,400}\bpush\b";

/// Index of the first rule that matches, mirroring Python's first-match-wins loop.
///
/// THE PRESCAN. An earlier version compiled all 17 patterns eagerly into a `OnceLock<Vec>`,
/// which measured ~45 ms of the gate's ~49 ms on Linux. Every rule needs some literal present
/// before it can fire, so a substring test decides whether a pattern is worth compiling at
/// all. An ordinary command (`echo`, `ls`, `cd`) contains none of them and compiles nothing.
///
/// The asymmetry that makes this safe: over-approximating a literal set costs a wasted
/// compile, while UNDER-approximating skips a rule on a command it should block and reports
/// nothing. The sets are therefore fuzz-verified in regen_rules.py before rules.rs is
/// written, and that verifier is itself mutation-tested. Nothing here re-checks it at
/// runtime, because a runtime check would mean compiling the pattern, which is the cost
/// being avoided.
///
/// No caching. Each pattern is compiled at most once per rule per process, and a process
/// handles exactly one command, so a `OnceLock` would add synchronisation for no reuse.
///
/// A pattern that errors at match time is treated as NOT matching and reported on stderr:
/// failing open is safety_gate.py's own documented contract, and a guard that panics would
/// brick every Bash call in the session.
fn first_match(command: &str) -> Option<usize> {
    // One allocation, reused by every rule's prescan. The patterns are all case-insensitive
    // and regen_rules.py rejects any literal that is not already lowercase, so comparing
    // against a lowercased haystack cannot lose a match.
    let lower = command.to_lowercase();

    for (i, rule) in rules::RULES.iter().enumerate() {
        // Conjunction of disjunctions: EVERY group must contribute a present member. No
        // groups at all means "always compile", the conservative default. A group that is
        // not genuinely necessary would narrow this below the rule's real precondition and
        // skip it silently, which is why regen_rules.py fuzzes each group and is itself
        // mutation-tested against bogus ones.
        if !rule
            .literal_groups
            .iter()
            .all(|group| group.iter().any(|l| lower.contains(l)))
        {
            continue;
        }
        match Regex::new(rule.pattern) {
            Ok(re) => match re.is_match(command) {
                Ok(true) => return Some(i),
                Ok(false) => {}
                Err(e) => eprintln!("hookgate: rule {} match error: {}", i, e),
            },
            Err(e) => eprintln!("hookgate: rule {} failed to compile: {}", i, e),
        }
    }
    None
}

/// Byte-identical to safety_gate.py::GUIDANCE. Pinned equal by tests/test_hookgate.py,
/// because a guard that gives different advice depending on which implementation happens to
/// be deployed teaches the caller two different things about the same refusal.
///
/// This is appended to the refusal, not to a rule. RULES is untouched, so src/rules.rs stays
/// byte-identical and the differential oracle (which compares rule indices) is unaffected.
const GUIDANCE: &str = " If you were WRITING this text rather than executing it, for example \
a heredoc, a doc comment, or a test fixture, use the Write tool instead: it is not gated by \
this hook. This guard cannot tell a heredoc bound for a file from one piped to a shell, and \
exempting heredoc bodies would create a real bypass, so the false positive is kept on purpose.";

fn emit_denial(reason: &str) {
    // Shape must match safety_gate.py::emit_denial exactly or the platform ignores it.
    let payload = serde_json::json!({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": format!("{}{}", reason, GUIDANCE),
        }
    });
    println!("{}", payload);
}

fn diff_mode() -> io::Result<()> {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input)?;
    let out = io::stdout();
    let mut w = io::BufWriter::new(out.lock());
    for line in input.lines() {
        let idx = first_match(line).map(|i| i as i64).unwrap_or(-1);
        writeln!(w, "{}", idx)?;
    }
    Ok(())
}

fn main() {
    if std::env::args().nth(1).as_deref() == Some("--diff-mode") {
        if let Err(e) = diff_mode() {
            eprintln!("hookgate diff-mode: {}", e);
            std::process::exit(1);
        }
        return;
    }

    let mut raw = Vec::new();
    if io::stdin().read_to_end(&mut raw).is_err() {
        println!("{{}}");
        return;
    }

    // Fail open on malformed input, matching safety_gate.py: a broken guard must not
    // brick the CLI, and native permission rules are the first line of defence.
    let v: serde_json::Value = match serde_json::from_slice(&raw) {
        Ok(v) => v,
        Err(_) => {
            println!("{{}}");
            return;
        }
    };
    let command = v
        .get("tool_input")
        .and_then(|t| t.get("command"))
        .and_then(|c| c.as_str())
        .unwrap_or("");

    if let Some(i) = first_match(command) {
        emit_denial(rules::RULES[i].reason);
        return;
    }

    // Cold path only. Delegate to the Python push gate, unmodified, feeding it the exact
    // bytes we were given so its own parsing sees what it would have seen.
    //
    // The delegate path used to be the literal string
    // "/mnt/c/Users/shova/.claude/hooks/pre_push_gate.py", and on 2026-08-10 that cost a
    // whole class of fix. The operator was still being prompted on compound pushes after
    // pre_push_gate.py had been taught to segment them, because the fix landed in the
    // Linux copy at ~/.claude/hooks while this binary went on calling the Windows one,
    // ten days stale and 6191 bytes shorter. Two copies of a guard, one of them fixed,
    // and the fixed one was not the one that ran. Same shape as L-2026-07-31-g: a check
    // that is correct on the host it was written for and wrong on the other.
    //
    // Resolution is now per host and every candidate is a real file test, because a path
    // that does not exist must not silently become the answer.
    let is_push = Regex::new(PUSH)
        .map(|re| re.is_match(command).unwrap_or(false))
        .unwrap_or(false);
    if !is_push {
        println!("{{}}");
        return;
    }

    let gate = std::env::var("HOOKGATE_PUSH_DELEGATE").unwrap_or_else(|_| push_delegate());
    let py = std::env::var("HOOKGATE_PYTHON").unwrap_or_else(|_| "python3".to_string());
    let child = Command::new(&py)
        .arg(&gate)
        .stdin(Stdio::piped())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .spawn();
    match child {
        Ok(mut c) => {
            if let Some(si) = c.stdin.as_mut() {
                let _ = si.write_all(&raw);
            }
            drop(c.stdin.take());
            let _ = c.wait();
        }
        Err(e) => {
            // Cannot inspect the push. Fail open with a note rather than blocking work.
            eprintln!("hookgate: push delegate {} failed: {}", gate, e);
            println!("{{}}");
        }
    }
}
