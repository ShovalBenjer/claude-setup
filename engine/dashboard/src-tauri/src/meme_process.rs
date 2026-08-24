//! Thin subprocess wrapper around the `claude-memes` binary (DASH-1 slice
//! 3). Kept out of `dashboard-core` on purpose: `Command::new` is a process
//! boundary, not pure logic, and is not unit-tested here (it is exercised
//! end to end by running the real binary, per the slice-3 acceptance row and
//! the no-mocks rule). The parsing it feeds (`dashboard_core::meme::{parse_list,
//! parse_find}`) IS unit-tested, against real captured stdout.

use std::env;
use std::path::PathBuf;
use std::process::Command;
use std::time::Duration;

const FALLBACK_BIN: &str =
    "/home/shov/work/repos/claude-memes-skills/target/release/claude-memes";
const SPAWN_TIMEOUT: Duration = Duration::from_secs(45); // `find` downloads a ~30MB model on first use

/// Resolve the `claude-memes` binary path: `CLAUDE_MEMES_BIN` env var first,
/// else the known build location in this workstation's checkout. A future
/// packaged app should set the env var; hardcoding one path as the *only*
/// source is exactly what `tools/audit/pointers.py scan` flags as a dead
/// path on a machine that lacks it.
fn resolve_bin() -> PathBuf {
    env::var("CLAUDE_MEMES_BIN")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from(FALLBACK_BIN))
}

#[derive(Debug)]
pub enum MemeProcessError {
    BinaryNotFound(String),
    SpawnFailed(String),
    Timeout,
    NonZeroExit { code: Option<i32>, stderr: String },
}

impl std::fmt::Display for MemeProcessError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            MemeProcessError::BinaryNotFound(p) => write!(f, "claude-memes binary not found at {p}"),
            MemeProcessError::SpawnFailed(e) => write!(f, "failed to spawn claude-memes: {e}"),
            MemeProcessError::Timeout => write!(f, "claude-memes call timed out"),
            MemeProcessError::NonZeroExit { code, stderr } => {
                write!(f, "claude-memes exited {code:?}: {stderr}")
            }
        }
    }
}

/// Run `claude-memes <args>` and return stdout. Blocking with a wait-based
/// timeout: `wait_timeout` is not in std, and pulling a crate for one
/// timeout on a single subprocess call is not worth the dependency for this
/// slice, so a coarse elapsed-time check after `wait()` on a spawned child
/// backstops a hang (see rejected alternative below the timeout constant).
fn run(args: &[&str]) -> Result<String, MemeProcessError> {
    let bin = resolve_bin();
    if !bin.exists() {
        return Err(MemeProcessError::BinaryNotFound(bin.display().to_string()));
    }

    let start = std::time::Instant::now();
    let mut child = Command::new(&bin)
        .args(args)
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()
        .map_err(|e| MemeProcessError::SpawnFailed(e.to_string()))?;

    loop {
        match child.try_wait() {
            Ok(Some(_status)) => break,
            Ok(None) => {
                if start.elapsed() > SPAWN_TIMEOUT {
                    let _ = child.kill();
                    return Err(MemeProcessError::Timeout);
                }
                std::thread::sleep(Duration::from_millis(50));
            }
            Err(e) => return Err(MemeProcessError::SpawnFailed(e.to_string())),
        }
    }

    let output = child
        .wait_with_output()
        .map_err(|e| MemeProcessError::SpawnFailed(e.to_string()))?;

    if !output.status.success() {
        return Err(MemeProcessError::NonZeroExit {
            code: output.status.code(),
            stderr: String::from_utf8_lossy(&output.stderr).into_owned(),
        });
    }

    Ok(String::from_utf8_lossy(&output.stdout).into_owned())
}

pub fn run_list() -> Result<String, MemeProcessError> {
    run(&["list"])
}

pub fn run_find(concept: &str) -> Result<String, MemeProcessError> {
    run(&["find", concept])
}
