//! Meme module: parsers for `claude-memes list` and `claude-memes find
//! <concept>` stdout (DASH-1 slice 3).
//!
//! **Named divergence from the program design** (docs/specs/2026-08-17-
//! session-dashboard-program-design.md section 2.3): that document specifies
//! `meme_find -> MemeResult { path, source }` proxying `claude-memes mcp`'s
//! stdio `find_meme`/`play_meme` tools. The operator's slice-3 direction
//! instead names subprocess-per-call against `claude-memes list` / `find`
//! directly. This module implements the operator's later direction; the
//! return shape here (`FindHit { hub, score, queries }`, a ranked list) does
//! not match `MemeResult`, and `play_meme` is not implemented in this slice.
//! Rejected alternative: the `claude-memes mcp` stdio process. Rejected for
//! this slice because it requires managing a long-lived child process
//! lifecycle (spawn, stdio framing, shutdown) for a binary that is otherwise
//! stable and fast to invoke per call; subprocess-per-call has no process to
//! keep alive or restart on crash. Revisit if per-call spawn latency (model
//! load in `find`) proves too slow for interactive use.
//!
//! Parsers are pure functions over captured stdout, unit-tested against real
//! output run directly from the binary (not a mock of the boundary: the
//! fixture text below is `claude-memes list`/`find "tests failed"` output
//! captured 2026-08-18, per the no-mocks rule — the boundary under test is
//! text parsing, and the subprocess call itself is exercised separately by
//! the Tauri command in `src-tauri` against the real binary).

use serde::Serialize;

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct MemeEvent {
    pub id: String,
    pub query: String,
    pub trigger: String,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct FindHit {
    pub hub: String,
    pub score: f64,
    pub queries: Vec<String>,
}

/// Parse `claude-memes list` stdout. Shape: a header line, a blank line,
/// then pairs of lines per event: `  id  →  query` followed by an indented
/// continuation line holding the trigger description. Unparseable lines are
/// skipped rather than erroring, since this is display data, not a ledger,
/// but a total-miss (zero events parsed from non-empty input) is left for
/// the caller to detect and report as `IpcError::Io`.
pub fn parse_list(stdout: &str) -> Vec<MemeEvent> {
    let lines: Vec<&str> = stdout.lines().collect();
    let mut events = Vec::new();
    let mut i = 0;
    while i < lines.len() {
        let line = lines[i];
        if let Some(arrow_pos) = line.find('\u{2192}') {
            let id = line[..arrow_pos].trim().to_string();
            let query = line[arrow_pos + '\u{2192}'.len_utf8()..].trim().to_string();
            if !id.is_empty() && !query.is_empty() {
                let trigger = lines
                    .get(i + 1)
                    .map(|s| s.trim())
                    .filter(|s| !s.is_empty() && !s.contains('\u{2192}'))
                    .unwrap_or("")
                    .to_string();
                events.push(MemeEvent { id, query, trigger });
            }
        }
        i += 1;
    }
    events
}

/// Parse `claude-memes find <concept>` stdout. Shape: `concept: ...` header,
/// blank line, ranked `→  score  hub   query1 | query2 | ...` rows, blank
/// line, `threshold: ...` footer. Rows are whitespace-delimited after the
/// arrow: score (float), hub (identifier, no spaces), then the remainder is
/// the pipe-separated query list.
pub fn parse_find(stdout: &str) -> Vec<FindHit> {
    let mut hits = Vec::new();
    for line in stdout.lines() {
        let trimmed = line.trim_start();
        let Some(rest) = trimmed.strip_prefix('\u{2192}') else {
            continue;
        };
        let rest = rest.trim_start();
        let Some(space_pos) = rest.find(char::is_whitespace) else { continue };
        let score_str = &rest[..space_pos];
        let Ok(score) = score_str.parse::<f64>() else { continue };
        let after_score = rest[space_pos..].trim_start();
        let hub_end = after_score.find(char::is_whitespace).unwrap_or(after_score.len());
        let hub = after_score[..hub_end].to_string();
        let queries_raw = after_score[hub_end..].trim();
        let queries: Vec<String> = queries_raw
            .split('|')
            .map(|q| q.trim().to_string())
            .filter(|q| !q.is_empty())
            .collect();
        if !hub.is_empty() {
            hits.push(FindHit { hub, score, queries });
        }
    }
    hits
}

#[cfg(test)]
mod tests {
    use super::*;

    // Captured 2026-08-18 from `claude-memes list` run directly against the
    // real binary at /home/shov/work/repos/claude-memes-skills/target/
    // release/claude-memes (real output, not synthesized).
    const LIST_FIXTURE: &str = "22 events (installed config):\n\n  agent_team           \u{2192} avengers assemble\n                         /agent-team skill invoked\n  brainstorm_start     \u{2192} its always sunny pepe silvia conspiracy\n                         /brainstorming skill invoked\n  ci_build_fail         \u{2192} leeroy jenkins\n                         CI build fails\n  tests_all_pass        \u{2192} lebron james thats too easy\n                         Full test suite passes (all green)\n";

    // Captured 2026-08-18 from `claude-memes find "tests failed"`.
    const FIND_FIXTURE: &str = "concept: tests failed\n\n\u{2192}  0.626  tests_lie              fake smile everything is good | behind the curtain wizard of oz\n\u{2192}  0.490  build_broken           everything is broken panic | error error error glitch\n\u{2192}  0.400  flaky                  slot machine random | schrodinger box maybe\n\nthreshold: 0.28 (auto mode fires on '\u{2192}' rows; tune auto_threshold in events.toml)\n";

    #[test]
    fn parses_all_events_from_real_list_fixture() {
        let events = parse_list(LIST_FIXTURE);
        assert_eq!(events.len(), 4);
        assert_eq!(events[0].id, "agent_team");
        assert_eq!(events[0].query, "avengers assemble");
        assert_eq!(events[0].trigger, "/agent-team skill invoked");
        assert_eq!(events[3].id, "tests_all_pass");
        assert_eq!(events[3].trigger, "Full test suite passes (all green)");
    }

    #[test]
    fn parses_ranked_hits_from_real_find_fixture() {
        let hits = parse_find(FIND_FIXTURE);
        assert_eq!(hits.len(), 3);
        assert_eq!(hits[0].hub, "tests_lie");
        assert!((hits[0].score - 0.626).abs() < 1e-9);
        assert_eq!(
            hits[0].queries,
            vec![
                "fake smile everything is good".to_string(),
                "behind the curtain wizard of oz".to_string()
            ]
        );
        assert_eq!(hits[1].hub, "build_broken");
        assert_eq!(hits[2].hub, "flaky");
        // descending score order preserved from the binary's own ranking
        assert!(hits[0].score > hits[1].score && hits[1].score > hits[2].score);
    }

    #[test]
    fn empty_input_yields_no_hits_no_panic() {
        assert_eq!(parse_list(""), Vec::new());
        assert_eq!(parse_find(""), Vec::new());
    }

    #[test]
    fn find_ignores_header_and_footer_lines() {
        let hits = parse_find(FIND_FIXTURE);
        // header ("concept: ...") and footer ("threshold: ...") never
        // produce a spurious hit
        assert!(hits.iter().all(|h| h.hub != "concept" && h.hub != "threshold"));
    }
}
