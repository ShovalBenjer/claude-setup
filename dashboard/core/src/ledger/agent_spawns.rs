//! `state/agent-spawns.jsonl` -> `AgentSpawn`. Follows the same read
//! algorithm as `gate_runs.rs` (program design section 1.1): open, iterate
//! non-empty lines, parse-then-shape each one, skip-and-count on either
//! failure, never panic, missing file returns an empty report.
//!
//! Row shape observed directly from `state/agent-spawns.jsonl` (real rows,
//! not the program design's speculative sketch), 2026-09-01:
//! `ts`, `subagent_type`, `description`, `model`, `background`, `isolation`,
//! `prompt_chars`, `session`, `cwd`, `router_named`, `router_skills`,
//! `router_named_at`. `model` and `isolation` are both frequently empty
//! strings in real rows (a foreground default-model spawn), so they are
//! `String` with `""` default, not `Option<String>`: an empty string is a
//! real, meaningful value here (no override chosen), not an absent field.

use crate::LedgerReadReport;
use serde::Serialize;
use serde_json::Value;
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct AgentSpawn {
    pub ts: String,
    pub subagent_type: String,
    pub description: String,
    pub model: String,
    pub background: bool,
    pub isolation: String,
    pub prompt_chars: u64,
    pub session: String,
    pub cwd: String,
    pub router_named: Vec<String>,
    pub router_skills: Vec<String>,
    pub router_named_at: String,
}

#[derive(Debug)]
pub struct ShapeError(String);

fn req_str(v: &Value, key: &str) -> Result<String, ShapeError> {
    v.get(key)
        .and_then(Value::as_str)
        .map(str::to_string)
        .ok_or_else(|| ShapeError(format!("missing/non-string field `{key}`")))
}

fn opt_str(v: &Value, key: &str) -> String {
    v.get(key)
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_string()
}

fn opt_bool(v: &Value, key: &str, default: bool) -> bool {
    v.get(key).and_then(Value::as_bool).unwrap_or(default)
}

fn opt_u64(v: &Value, key: &str) -> u64 {
    v.get(key).and_then(Value::as_u64).unwrap_or(0)
}

fn opt_str_vec(v: &Value, key: &str) -> Vec<String> {
    v.get(key)
        .and_then(Value::as_array)
        .map(|a| {
            a.iter()
                .filter_map(Value::as_str)
                .map(str::to_string)
                .collect()
        })
        .unwrap_or_default()
}

impl TryFrom<&Value> for AgentSpawn {
    type Error = ShapeError;

    fn try_from(v: &Value) -> Result<Self, Self::Error> {
        Ok(AgentSpawn {
            ts: req_str(v, "ts")?,
            subagent_type: req_str(v, "subagent_type")?,
            description: opt_str(v, "description"),
            model: opt_str(v, "model"),
            background: opt_bool(v, "background", false),
            isolation: opt_str(v, "isolation"),
            prompt_chars: opt_u64(v, "prompt_chars"),
            session: opt_str(v, "session"),
            cwd: opt_str(v, "cwd"),
            router_named: opt_str_vec(v, "router_named"),
            router_skills: opt_str_vec(v, "router_skills"),
            router_named_at: opt_str(v, "router_named_at"),
        })
    }
}

/// Identical skip-and-count algorithm to `gate_runs::read_gate_runs`: a
/// missing file is not an error (the dashboard runs before the ledger has
/// its first row), a malformed or short-shaped line increments `skipped`
/// and is never fatal to the read.
pub fn read_agent_spawns(path: &Path) -> LedgerReadReport<AgentSpawn> {
    let content = match fs::read_to_string(path) {
        Ok(c) => c,
        Err(_) => return LedgerReadReport::empty(),
    };

    let mut rows = Vec::new();
    let mut skipped = 0usize;
    let mut total_lines = 0usize;
    let mut first_error: Option<String> = None;

    for line in content.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        total_lines += 1;

        let parsed: Result<AgentSpawn, String> = serde_json::from_str::<Value>(line)
            .map_err(|e| format!("invalid JSON: {e}"))
            .and_then(|v| AgentSpawn::try_from(&v).map_err(|e| e.0));

        match parsed {
            Ok(row) => rows.push(row),
            Err(msg) => {
                skipped += 1;
                if first_error.is_none() {
                    let mut truncated = msg;
                    truncated.truncate(200);
                    first_error = Some(truncated);
                }
            }
        }
    }

    LedgerReadReport {
        rows,
        skipped,
        total_lines,
        first_error,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    fn write_temp(contents: &str) -> tempfile::NamedTempFile {
        let mut f = tempfile::NamedTempFile::new().expect("tempfile");
        f.write_all(contents.as_bytes()).expect("write");
        f
    }

    #[test]
    fn valid_line_parses_with_real_row_shape() {
        // Taken verbatim in shape from a real state/agent-spawns.jsonl row.
        let line = r#"{"ts":"2026-08-18T18:22:34","subagent_type":"engineering-firm","description":"Rebase PR 77","model":"","background":true,"isolation":"worktree","prompt_chars":2071,"session":"s1","cwd":"/x","router_named":[],"router_skills":[],"router_named_at":""}"#;
        let f = write_temp(&format!("{line}\n"));
        let report = read_agent_spawns(f.path());
        assert_eq!(report.skipped, 0);
        assert_eq!(report.rows.len(), 1);
        assert_eq!(report.rows[0].subagent_type, "engineering-firm");
        assert_eq!(report.rows[0].model, "", "empty model is a real value, not absent");
        assert!(report.rows[0].background);
        assert_eq!(report.rows[0].prompt_chars, 2071);
    }

    #[test]
    fn router_named_and_skills_arrays_parse() {
        let line = r#"{"ts":"t","subagent_type":"fork","description":"d","router_named":["communications-desk","release-bureau"],"router_skills":["blog","humanize"]}"#;
        let f = write_temp(&format!("{line}\n"));
        let report = read_agent_spawns(f.path());
        assert_eq!(report.rows.len(), 1);
        assert_eq!(
            report.rows[0].router_named,
            vec!["communications-desk", "release-bureau"]
        );
        assert_eq!(report.rows[0].router_skills, vec!["blog", "humanize"]);
    }

    #[test]
    fn malformed_lines_are_skipped_and_counted_without_panic() {
        let missing_subagent_type = r#"{"ts":"t","description":"d"}"#;
        let not_json = "{this is not valid json,,,";
        let valid = r#"{"ts":"t2","subagent_type":"engineering-firm","description":"d2"}"#;

        let contents = format!("{missing_subagent_type}\n{not_json}\n{valid}\n");
        let f = write_temp(&contents);
        let report = read_agent_spawns(f.path());

        assert_eq!(report.total_lines, 3);
        assert_eq!(report.skipped, 2);
        assert_eq!(report.rows.len(), 1);
        assert_eq!(report.rows[0].subagent_type, "engineering-firm");
        assert!(report.first_error.is_some());
        assert!(report.first_error.as_ref().unwrap().len() <= 200);
    }

    #[test]
    fn missing_file_returns_empty_report_not_error() {
        let report = read_agent_spawns(Path::new("/nonexistent/path/does-not-exist.jsonl"));
        assert_eq!(report, LedgerReadReport::empty());
    }

    #[test]
    fn blank_lines_are_not_counted_as_skipped() {
        let valid = r#"{"ts":"t","subagent_type":"p","description":""}"#;
        let contents = format!("\n{valid}\n\n   \n");
        let f = write_temp(&contents);
        let report = read_agent_spawns(f.path());
        assert_eq!(report.total_lines, 1);
        assert_eq!(report.skipped, 0);
        assert_eq!(report.rows.len(), 1);
    }

    #[test]
    fn missing_optional_fields_default_without_panic() {
        // Only the two required fields present; every optional field must
        // default rather than fail the row.
        let minimal = r#"{"ts":"t","subagent_type":"general-purpose"}"#;
        let f = write_temp(&format!("{minimal}\n"));
        let report = read_agent_spawns(f.path());
        assert_eq!(report.skipped, 0);
        assert_eq!(report.rows.len(), 1);
        let row = &report.rows[0];
        assert_eq!(row.description, "");
        assert_eq!(row.model, "");
        assert!(!row.background);
        assert_eq!(row.isolation, "");
        assert_eq!(row.prompt_chars, 0);
        assert_eq!(row.session, "");
        assert_eq!(row.cwd, "");
        assert!(row.router_named.is_empty());
        assert!(row.router_skills.is_empty());
        assert_eq!(row.router_named_at, "");
    }
}
