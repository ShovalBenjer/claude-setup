//! Data contract, shared with the HTML console.
//!
//! This is the load-bearing decision in the whole project: the Rust engine and
//! `command_center/plan_console.html` read the SAME file, produced by
//! `command_center/plan_export.py`. Two viewers over one contract, so a plan can
//! be reviewed in a browser on a phone or shoved around in a native window on the
//! desktop without either becoming the source of truth. If this struct and that
//! exporter drift apart, `plan_export.py`'s contract tests are the ones that fail,
//! and they should stay that way.
//!
//! Deviation from the nexus-engine spec, stated: the spec's `NodeType` enumerates
//! C4 levels (SystemContext / Container / Component). The real corpus on disk is
//! documents, so the kinds here are the ones that actually exist: prd, adr, spec,
//! research, analysis. Inventing C4 levels nothing produces would have made a
//! pretty graph of nothing.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum Status {
    Undecided,
    Approved,
    Rejected,
    Blocked,
}

impl Status {
    /// Petrol/brass system from `command_center/style.md`, not a new palette.
    pub fn color(&self) -> egui::Color32 {
        match self {
            Status::Undecided => egui::Color32::from_rgb(0x6f, 0x8a, 0x88),
            Status::Approved => egui::Color32::from_rgb(0xc9, 0x9a, 0x3f),
            Status::Rejected => egui::Color32::from_rgb(0xb4, 0x55, 0x3f),
            Status::Blocked => egui::Color32::from_rgb(0x7a, 0x5f, 0xa8),
        }
    }
    pub fn label(&self) -> &'static str {
        match self {
            Status::Undecided => "undecided",
            Status::Approved => "approved",
            Status::Rejected => "rejected",
            Status::Blocked => "blocked",
        }
    }
}

impl Default for Status {
    fn default() -> Self {
        Status::Undecided
    }
}

/// A one-line definition, written for a fresh BSc graduate, plus a file in this
/// repo where the term is in use so the definition can be checked rather than
/// believed.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct GlossaryEntry {
    #[serde(default)]
    pub one_line: String,
    #[serde(default)]
    pub where_: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlanNode {
    pub id: String,
    pub label: String,
    pub kind: String,
    pub path: String,
    #[serde(default)]
    pub summary: String,
    #[serde(default)]
    pub status: Status,
    #[serde(default)]
    pub note: String,
    #[serde(default)]
    pub links: Vec<String>,

    // Content layer. `what` and `why` are extracted from the source, never
    // paraphrased: an empty `why` means the source states no reason, and the UI
    // must say that rather than fill the gap.
    #[serde(default)]
    pub what: String,
    #[serde(default)]
    pub why: Vec<String>,
    #[serde(default)]
    pub how: serde_json::Value,
    #[serde(default)]
    pub terms: Vec<String>,
    /// Derived tag groups (technology / risk / size). Every value is recomputable
    /// from the tree, so a stale tag is impossible; see tags_export.py.
    #[serde(default)]
    pub tags: std::collections::HashMap<String, String>,
}

impl PlanNode {
    /// Mechanism lines for the HOW block, flattened out of the untyped `how`
    /// object so the view does not have to know which exporter produced it.
    pub fn how_lines(&self) -> Vec<String> {
        let mut out = Vec::new();
        let obj = match self.how.as_object() {
            Some(o) => o,
            None => return out,
        };
        if let Some(cs) = obj.get("contracts").and_then(|v| v.as_array()) {
            for c in cs {
                let name = c.get("name").and_then(|v| v.as_str()).unwrap_or("");
                let does = c.get("does").and_then(|v| v.as_str()).unwrap_or("");
                out.push(format!("{name}  —  {does}"));
            }
        }
        if let Some(ss) = obj.get("sections").and_then(|v| v.as_array()) {
            for s in ss {
                if let Some(t) = s.as_str() {
                    out.push(format!("§ {t}"));
                }
            }
        }
        if let Some(is) = obj.get("imports").and_then(|v| v.as_array()) {
            let names: Vec<&str> = is.iter().filter_map(|v| v.as_str()).collect();
            if !names.is_empty() {
                out.push(format!("imports: {}", names.join(", ")));
            }
        }
        if let Some(l) = obj.get("lines").and_then(|v| v.as_i64()) {
            if l > 0 {
                out.push(format!("{l} lines"));
            }
        }
        out
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlanEdge {
    pub from: String,
    pub to: String,
    #[serde(default)]
    pub kind: String,
}

/// A closed contract from `state/plan_divergence.jsonl`, surfaced so the graph can
/// show where a plan actually failed rather than only what was proposed.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Contract {
    pub id: String,
    #[serde(default)]
    pub outcome: Option<String>,
    #[serde(default)]
    pub category: Option<String>,
    #[serde(default)]
    pub note: String,
    #[serde(default)]
    pub drift: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlanData {
    #[serde(default)]
    pub generated_at: String,
    #[serde(default)]
    pub nodes: Vec<PlanNode>,
    #[serde(default)]
    pub edges: Vec<PlanEdge>,
    #[serde(default)]
    pub contracts: Vec<Contract>,
    #[serde(default)]
    pub glossary: std::collections::HashMap<String, GlossaryEntry>,
    #[serde(default)]
    pub tag_groups: std::collections::HashMap<String, Vec<String>>,
    #[serde(default)]
    pub flows: Vec<Flow>,
}

/// A numbered path across the graph, after IcePanel's journey overlay.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Flow {
    #[serde(default)]
    pub name: String,
    /// Where the ordering came from. This one is transcribed from prose, not
    /// derived, and the field exists so that stays visible.
    #[serde(default)]
    pub source: String,
    #[serde(default)]
    pub steps: Vec<FlowStep>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct FlowStep {
    #[serde(default)]
    pub n: usize,
    #[serde(default)]
    pub node: String,
    #[serde(default)]
    pub label: String,
    #[serde(default)]
    pub why: String,
}

impl PlanData {
    /// Reads the same `plan_data.js` the browser console reads, by stripping the
    /// `window.PLAN_DATA = ...;` wrapper. Parsing the JS assignment rather than
    /// emitting a second .json file is deliberate: one artifact, so the two
    /// viewers cannot silently diverge on which one is current.
    pub fn from_js(src: &str) -> Result<Self, String> {
        let start = src
            .find('{')
            .ok_or_else(|| "no JSON object found in plan_data.js".to_string())?;
        let end = src
            .rfind('}')
            .ok_or_else(|| "unterminated JSON object in plan_data.js".to_string())?;
        serde_json::from_str(&src[start..=end]).map_err(|e| format!("parse: {e}"))
    }

    pub fn kinds(&self) -> Vec<String> {
        let mut out: Vec<String> = Vec::new();
        for n in &self.nodes {
            if !out.contains(&n.kind) {
                out.push(n.kind.clone());
            }
        }
        out.sort();
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const SAMPLE: &str = r#"window.PLAN_DATA = {
      "generated_at": "2026-07-31T00:00:00",
      "nodes": [
        {"id":"a.md","label":"A","kind":"spec","path":"a.md","summary":"s","links":["b.md"]},
        {"id":"b.md","label":"B","kind":"prd","path":"b.md","status":"approved"}
      ],
      "edges": [{"from":"a.md","to":"b.md","kind":"references"}],
      "contracts": []
    };
    "#;

    #[test]
    fn parses_the_browser_artifact() {
        let d = PlanData::from_js(SAMPLE).expect("should parse");
        assert_eq!(d.nodes.len(), 2);
        assert_eq!(d.edges.len(), 1);
    }

    #[test]
    fn status_defaults_to_undecided_when_absent() {
        let d = PlanData::from_js(SAMPLE).unwrap();
        assert_eq!(d.nodes[0].status, Status::Undecided);
        assert_eq!(d.nodes[1].status, Status::Approved);
    }

    #[test]
    fn kinds_are_deduped_and_sorted() {
        let d = PlanData::from_js(SAMPLE).unwrap();
        assert_eq!(d.kinds(), vec!["prd".to_string(), "spec".to_string()]);
    }

    #[test]
    fn a_file_without_json_is_an_error_not_a_panic() {
        assert!(PlanData::from_js("window.PLAN_DATA = ;").is_err());
    }
}
