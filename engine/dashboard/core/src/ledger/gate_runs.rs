//! `state/gate-runs.jsonl` -> `GateRun`. Program design section 1.2.

use crate::LedgerReadReport;
use serde::Serialize;
use serde_json::Value;
use std::collections::HashMap;
use std::fs;
use std::path::Path;

/// A gate run's verdict. `Unknown(String)` exists because a future gate run
/// may emit a verdict string this build has never seen; the UI renders it
/// rather than crashing on it (program design section 1.2).
#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum Verdict {
    Pass,
    Fail,
    Partial,
    Unknown(String),
}

impl Verdict {
    fn from_str(s: &str) -> Verdict {
        match s.to_ascii_uppercase().as_str() {
            "PASS" => Verdict::Pass,
            "FAIL" => Verdict::Fail,
            "PARTIAL" => Verdict::Partial,
            _ => Verdict::Unknown(s.to_string()),
        }
    }
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct GateRun {
    pub ts: String,
    pub project: String,
    pub project_path: String,
    pub commit: String,
    pub dirty: bool,
    pub fingerprint: String,
    pub partial: bool,
    pub verdict: Verdict,
    pub domains: HashMap<String, String>,
    pub blocking: Vec<String>,
    pub waivers_unconfirmed: Vec<String>,
    pub unmeasured: Vec<String>,
    pub duration_seconds: Option<f64>,
    pub domain_seconds: Option<HashMap<String, f64>>,
}

/// Reasons a single JSON value fails to become a `GateRun`. Kept private:
/// callers only need skip-and-count, not the reason, per the read algorithm
/// in the program design (the reason feeds `first_error`, truncated).
#[derive(Debug)]
pub struct ShapeError(String);

fn req_str(v: &Value, key: &str) -> Result<String, ShapeError> {
    v.get(key)
        .and_then(Value::as_str)
        .map(str::to_string)
        .ok_or_else(|| ShapeError(format!("missing/non-string field `{key}`")))
}

fn opt_bool(v: &Value, key: &str, default: bool) -> bool {
    v.get(key).and_then(Value::as_bool).unwrap_or(default)
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

fn opt_str_map(v: &Value, key: &str) -> HashMap<String, String> {
    v.get(key)
        .and_then(Value::as_object)
        .map(|o| {
            o.iter()
                .filter_map(|(k, val)| val.as_str().map(|s| (k.clone(), s.to_string())))
                .collect()
        })
        .unwrap_or_default()
}

fn opt_f64_map(v: &Value, key: &str) -> Option<HashMap<String, f64>> {
    v.get(key).and_then(Value::as_object).map(|o| {
        o.iter()
            .filter_map(|(k, val)| val.as_f64().map(|f| (k.clone(), f)))
            .collect()
    })
}

impl TryFrom<&Value> for GateRun {
    type Error = ShapeError;

    fn try_from(v: &Value) -> Result<Self, Self::Error> {
        Ok(GateRun {
            ts: req_str(v, "ts")?,
            project: req_str(v, "project")?,
            project_path: v
                .get("project_path")
                .and_then(Value::as_str)
                .unwrap_or_default()
                .to_string(),
            commit: v
                .get("commit")
                .and_then(Value::as_str)
                .unwrap_or_default()
                .to_string(),
            dirty: opt_bool(v, "dirty", false),
            fingerprint: v
                .get("fingerprint")
                .and_then(Value::as_str)
                .unwrap_or_default()
                .to_string(),
            partial: opt_bool(v, "partial", false),
            verdict: Verdict::from_str(&req_str(v, "verdict")?),
            domains: opt_str_map(v, "domains"),
            blocking: opt_str_vec(v, "blocking"),
            waivers_unconfirmed: opt_str_vec(v, "waivers_unconfirmed"),
            unmeasured: opt_str_vec(v, "unmeasured"),
            duration_seconds: v.get("duration_seconds").and_then(Value::as_f64),
            domain_seconds: opt_f64_map(v, "domain_seconds"),
        })
    }
}

/// Read algorithm (program design section 1.1), identical in shape across
/// all six readers: open file, iterate lines, skip empty/whitespace-only
/// lines without counting them as skipped, for each non-empty line parse as
/// JSON then shape into the row type; either failure increments `skipped`
/// and records the first error, never panics. A missing file is not an
/// error: it returns an empty report, since the dashboard runs before a
/// ledger has its first row.
pub fn read_gate_runs(path: &Path) -> LedgerReadReport<GateRun> {
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

        let parsed: Result<GateRun, String> = serde_json::from_str::<Value>(line)
            .map_err(|e| format!("invalid JSON: {e}"))
            .and_then(|v| GateRun::try_from(&v).map_err(|e| e.0));

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

/// `latest_gate_verdict` (program design section 2.1): last row by `ts`
/// order in the file (append-only, so the last parsed row is the latest).
pub fn latest_gate_verdict(path: &Path) -> Option<GateRun> {
    read_gate_runs(path).rows.into_iter().last()
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
    fn valid_line_parses() {
        let line = r#"{"ts":"2026-08-17T00:00:00Z","project":"claude-setup","project_path":"/x","commit":"abc123","dirty":false,"fingerprint":"f1","partial":false,"verdict":"PASS","domains":{"tests":"PASS"},"blocking":[],"duration_seconds":12.5}"#;
        let f = write_temp(&format!("{line}\n"));
        let report = read_gate_runs(f.path());
        assert_eq!(report.skipped, 0);
        assert_eq!(report.total_lines, 1);
        assert_eq!(report.rows.len(), 1);
        assert_eq!(report.rows[0].verdict, Verdict::Pass);
        assert_eq!(report.rows[0].duration_seconds, Some(12.5));
    }

    /// Acceptance check (a) from the program design slice 2 row: a
    /// hand-crafted malformed line (missing `verdict`) and a line that is
    /// not valid JSON must both increment `skipped` and must not panic.
    #[test]
    fn malformed_lines_are_skipped_and_counted_without_panic() {
        let missing_verdict =
            r#"{"ts":"2026-08-17T00:00:00Z","project":"claude-setup","fingerprint":"f1"}"#;
        let not_json = "{this is not valid json,,,";
        let valid = r#"{"ts":"2026-08-17T00:01:00Z","project":"claude-setup","project_path":"/x","commit":"abc124","dirty":false,"fingerprint":"f2","partial":false,"verdict":"FAIL","domains":{}}"#;

        let contents = format!("{missing_verdict}\n{not_json}\n{valid}\n");
        let f = write_temp(&contents);

        // The point of this test: read_gate_runs must return normally
        // (no panic) even though two of three lines are malformed.
        let report = read_gate_runs(f.path());

        assert_eq!(report.total_lines, 3, "all three non-empty lines counted");
        assert_eq!(report.skipped, 2, "the two malformed lines are skipped");
        assert_eq!(report.rows.len(), 1, "only the valid line parses");
        assert_eq!(report.rows[0].verdict, Verdict::Fail);
        assert!(report.first_error.is_some());
        assert!(report.first_error.as_ref().unwrap().len() <= 200);
    }

    #[test]
    fn missing_file_returns_empty_report_not_error() {
        let report = read_gate_runs(Path::new("/nonexistent/path/does-not-exist.jsonl"));
        assert_eq!(report, LedgerReadReport::empty());
    }

    #[test]
    fn blank_lines_are_not_counted_as_skipped() {
        let valid = r#"{"ts":"t","project":"p","project_path":"","commit":"","dirty":false,"fingerprint":"","partial":false,"verdict":"PASS","domains":{}}"#;
        let contents = format!("\n{valid}\n\n   \n");
        let f = write_temp(&contents);
        let report = read_gate_runs(f.path());
        assert_eq!(report.total_lines, 1);
        assert_eq!(report.skipped, 0);
        assert_eq!(report.rows.len(), 1);
    }

    #[test]
    fn unknown_verdict_string_does_not_panic() {
        let line = r#"{"ts":"t","project":"p","project_path":"","commit":"","dirty":false,"fingerprint":"","partial":false,"verdict":"SOMETHING_NEW","domains":{}}"#;
        let f = write_temp(&format!("{line}\n"));
        let report = read_gate_runs(f.path());
        assert_eq!(report.rows.len(), 1);
        assert_eq!(
            report.rows[0].verdict,
            Verdict::Unknown("SOMETHING_NEW".to_string())
        );
    }

    #[test]
    fn latest_gate_verdict_returns_last_row() {
        let first = r#"{"ts":"t1","project":"p","project_path":"","commit":"","dirty":false,"fingerprint":"","partial":false,"verdict":"FAIL","domains":{}}"#;
        let second = r#"{"ts":"t2","project":"p","project_path":"","commit":"","dirty":false,"fingerprint":"","partial":false,"verdict":"PASS","domains":{}}"#;
        let f = write_temp(&format!("{first}\n{second}\n"));
        let latest = latest_gate_verdict(f.path()).expect("some row");
        assert_eq!(latest.verdict, Verdict::Pass);
        assert_eq!(latest.ts, "t2");
    }
}
