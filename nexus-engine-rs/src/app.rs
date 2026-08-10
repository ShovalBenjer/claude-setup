//! egui shell: physics graph canvas, inspector, decision writeback.
//!
//! Scope, stated against the spec so the gap is legible rather than implied.
//! BUILT: models, physics, canvas view, inspector, decision writeback.
//! NOT BUILT: `sandbox/` (ContractLock + RevertSandbox), `gpu/shader.wgsl`
//! (WGSL SDF background), `views/diff_panel.rs`, `views/timeline.rs`.
//! The sandbox half already exists in Python as the `plan-divergence` skill and
//! duplicating it in Rust would fork the ledger, so this reads that ledger instead
//! of reimplementing it. The shader and the diff/timeline panels are real gaps.

use crate::models::{PlanData, Status};
use crate::physics::World;
use eframe::egui;
use std::collections::HashMap;

// command_center/style.md, not a second palette.
const GROUND: egui::Color32 = egui::Color32::from_rgb(0x0b, 0x1a, 0x1c);
const PANEL: egui::Color32 = egui::Color32::from_rgb(0x0f, 0x24, 0x27);
const RULE: egui::Color32 = egui::Color32::from_rgb(0x1c, 0x3b, 0x3d);
const TEAL: egui::Color32 = egui::Color32::from_rgb(0x16, 0x86, 0x7e);
const BRASS: egui::Color32 = egui::Color32::from_rgb(0xc9, 0x9a, 0x3f);
const INK: egui::Color32 = egui::Color32::from_rgb(0xcf, 0xe3, 0xe0);
const MUTED: egui::Color32 = egui::Color32::from_rgb(0x6f, 0x8a, 0x88);

/// Characters of a document title drawn inside a node box.
pub const LABEL_CHARS: usize = 30;

fn hsv_to_rgb(h: f32, s: f32, v: f32) -> (u8, u8, u8) {
    let c = v * s;
    let x = c * (1.0 - ((h / 60.0) % 2.0 - 1.0).abs());
    let m = v - c;
    let (r, g, b) = match h as u32 / 60 {
        0 => (c, x, 0.0),
        1 => (x, c, 0.0),
        2 => (0.0, c, x),
        3 => (0.0, x, c),
        4 => (x, 0.0, c),
        _ => (c, 0.0, x),
    };
    (((r + m) * 255.0) as u8, ((g + m) * 255.0) as u8, ((b + m) * 255.0) as u8)
}

pub struct App {
    data: PlanData,
    world: World,
    edges: Vec<(String, String)>,
    selected: Option<String>,
    filter_kind: Option<String>,
    last_pointer: Option<egui::Pos2>,
    laid_out: bool,
    status_line: String,
    open_term: Option<String>,
    canvas_rect: egui::Rect,
    logged_rect: bool,
    bar_h: f32,
    focus: Option<String>,
    tag_group: Option<String>,
    flow_on: bool,
    child_of: HashMap<String, String>,
    decisions_path: std::path::PathBuf,
}

impl App {
    pub fn new(data: PlanData, decisions_path: std::path::PathBuf) -> Self {
        let mut world = World::new();
        for (i, n) in data.nodes.iter().enumerate() {
            let x = 120.0 + ((i % 7) as f32) * 130.0;
            let y = 80.0 + ((i / 7) as f32) * 46.0;
            world.add_node(&n.id, x, y);
        }
        let ids: std::collections::HashSet<&str> =
            data.nodes.iter().map(|n| n.id.as_str()).collect();
        let edges = data
            .edges
            .iter()
            .filter(|e| ids.contains(e.from.as_str()) && ids.contains(e.to.as_str()))
            .map(|e| (e.from.clone(), e.to.clone()))
            .collect();
        // parent index, from the `contains` edges the exporter emits
        let mut child_of: HashMap<String, String> = HashMap::new();
        for e in &data.edges {
            if e.kind == "contains" {
                child_of.insert(e.to.clone(), e.from.clone());
            }
        }
        let selected = data.nodes.first().map(|n| n.id.clone());
        Self {
            data,
            world,
            edges,
            selected,
            filter_kind: None,
            last_pointer: None,
            laid_out: false,
            status_line: String::new(),
            open_term: None,
            canvas_rect: egui::Rect::from_min_size(
                egui::pos2(0.0, 0.0),
                egui::vec2(1000.0, 700.0),
            ),
            logged_rect: false,
            bar_h: 30.0,
            focus: None,
            tag_group: None,
            flow_on: false,
            child_of,
            decisions_path,
        }
    }

    /// Which nodes belong on screen right now.
    ///
    /// C4 drill-down, after IcePanel: the top level is the system and its
    /// containers only. Descending into a container shows that container and its
    /// own components. This is what makes 89 nodes legible; eight flat columns
    /// never were, at any inspector width.
    fn node_visible(&self, n: &crate::models::PlanNode) -> bool {
        if let Some(k) = &self.filter_kind {
            if &n.kind != k {
                return false;
            }
        }
        match &self.focus {
            None => n.kind == "SystemContext" || n.kind == "Container",
            Some(parent) => {
                if &n.id == parent {
                    return true;
                }
                self.child_of.get(&n.id).map(|p| p == parent).unwrap_or(false)
            }
        }
    }

    fn visible(&self, kind: &str) -> bool {
        match &self.filter_kind {
            None => true,
            Some(k) => k == kind,
        }
    }

    /// One column per kind, same arrangement as the HTML console, so the two
    /// viewers over the same contract also read the same way.
    fn relayout(&mut self, rect: egui::Rect) {
        // Focused: parent in the centre, children in a ring around it. A handful
        // of nodes does not need columns, and a ring shows containment directly.
        if let Some(parent) = self.focus.clone() {
            let centre = rect.center();
            self.world.set_anchor(&parent, centre.x, centre.y);
            if !self.laid_out {
                self.world.teleport(&parent, centre.x, centre.y);
            }
            let kids: Vec<String> = self
                .data
                .nodes
                .iter()
                .filter(|n| self.child_of.get(&n.id).map(|p| p == &parent).unwrap_or(false))
                .map(|n| n.id.clone())
                .collect();
            let count = kids.len().max(1) as f32;
            let rx = (rect.width() * 0.36).min(430.0);
            let ry = (rect.height() * 0.40).min(330.0);
            for (i, id) in kids.iter().enumerate() {
                let a = (i as f32 / count) * std::f32::consts::TAU - std::f32::consts::FRAC_PI_2;
                let x = centre.x + rx * a.cos();
                let y = centre.y + ry * a.sin();
                self.world.set_anchor(id, x, y);
                if !self.laid_out {
                    self.world.teleport(id, x, y);
                }
            }
            return;
        }
        let kinds = self.data.kinds();
        let col_w = rect.width() / kinds.len().max(1) as f32;
        let mut per_kind: HashMap<String, Vec<String>> = HashMap::new();
        for n in &self.data.nodes {
            per_kind.entry(n.kind.clone()).or_default().push(n.id.clone());
        }
        for (i, k) in kinds.iter().enumerate() {
            let group = match per_kind.get(k) {
                Some(g) => g.clone(),
                None => continue,
            };
            let n = group.len().max(1) as f32;
            for (j, id) in group.iter().enumerate() {
                let x = rect.left() + col_w * (i as f32 + 0.5);
                let y = rect.top() + 40.0 + ((j as f32 + 0.5) / n) * (rect.height() - 70.0);
                self.world.set_anchor(id, x, y);
                if !self.laid_out {
                    self.world.teleport(id, x, y);
                }
            }
        }
    }


    /// Stable colour per tag value. Hashed so a new tag value gets a colour
    /// without anyone maintaining a palette, and the same value always lands on
    /// the same hue between runs.
    fn tag_color(v: &str) -> egui::Color32 {
        let mut h: u32 = 2166136261;
        for b in v.as_bytes() {
            h ^= *b as u32;
            h = h.wrapping_mul(16777619);
        }
        let hue = (h % 360) as f32;
        let (r, g, b) = hsv_to_rgb(hue, 0.45, 0.85);
        egui::Color32::from_rgb(r, g, b)
    }

    /// Incoming and outgoing edges for a node, as (kind, other-label) pairs.
    fn connections(&self, id: &str) -> (Vec<String>, Vec<String>) {
        let label = |i: &str| {
            self.data
                .nodes
                .iter()
                .find(|n| n.id == i)
                .map(|n| n.label.clone())
                .unwrap_or_else(|| i.to_string())
        };
        let mut inc = Vec::new();
        let mut out = Vec::new();
        for e in &self.data.edges {
            if e.to == id {
                inc.push(format!("{} <- {}", e.kind, label(&e.from)));
            } else if e.from == id {
                out.push(format!("{} -> {}", e.kind, label(&e.to)));
            }
        }
        inc.sort();
        out.sort();
        (inc, out)
    }

    fn flow_step_of(&self, id: &str) -> Option<usize> {
        if !self.flow_on {
            return None;
        }
        self.data
            .flows
            .first()?
            .steps
            .iter()
            .find(|st| st.node == id)
            .map(|st| st.n)
    }

    fn counts(&self) -> (usize, usize, usize, usize) {
        let mut c = (0, 0, 0, 0);
        for n in &self.data.nodes {
            match n.status {
                Status::Undecided => c.0 += 1,
                Status::Approved => c.1 += 1,
                Status::Rejected => c.2 += 1,
                Status::Blocked => c.3 += 1,
            }
        }
        c
    }

    fn set_status(&mut self, status: Status) {
        let id = match &self.selected {
            Some(i) => i.clone(),
            None => return,
        };
        if let Some(n) = self.data.nodes.iter_mut().find(|n| n.id == id) {
            n.status = status;
        }
    }

    /// Writes the same `state/plan_decisions.json` the browser console exports, so
    /// `plan_export.py` picks it up on the next run regardless of which viewer made
    /// the decision. This is the only file this program writes.
    fn save(&mut self) {
        let mut map = serde_json::Map::new();
        for n in &self.data.nodes {
            if n.status != Status::Undecided || !n.note.is_empty() {
                let mut o = serde_json::Map::new();
                o.insert("status".into(), serde_json::Value::String(n.status.label().into()));
                o.insert("note".into(), serde_json::Value::String(n.note.clone()));
                map.insert(n.id.clone(), serde_json::Value::Object(o));
            }
        }
        let payload = serde_json::json!({ "decisions": serde_json::Value::Object(map) });
        if let Some(dir) = self.decisions_path.parent() {
            let _ = std::fs::create_dir_all(dir);
        }
        match std::fs::write(
            &self.decisions_path,
            serde_json::to_string_pretty(&payload).unwrap_or_default(),
        ) {
            Ok(_) => {
                self.status_line = format!("wrote {}", self.decisions_path.display());
            }
            Err(e) => {
                // Never claim a write that failed.
                self.status_line = format!("WRITE FAILED: {e}");
            }
        }
    }
}

impl eframe::App for App {
    fn ui(&mut self, ui: &mut egui::Ui, _f: &mut eframe::Frame) {
        let ctx = ui.ctx().clone();
        ctx.request_repaint();

        let mut visuals = egui::Visuals::dark();
        visuals.panel_fill = PANEL;
        visuals.window_fill = GROUND;
        visuals.override_text_color = Some(INK);
        ctx.set_visuals(visuals);

        // ---- keyboard, same bindings as the HTML console ----
        ctx.input(|i| {
            if i.key_pressed(egui::Key::A) {
                self.set_status(Status::Approved);
            }
            if i.key_pressed(egui::Key::R) {
                self.set_status(Status::Rejected);
            }
            if i.key_pressed(egui::Key::B) {
                self.set_status(Status::Blocked);
            }
            if i.key_pressed(egui::Key::U) {
                self.set_status(Status::Undecided);
            }
            if i.key_pressed(egui::Key::Backspace) {
                self.focus = None;
                self.laid_out = false;
            }
        });

        let bar = egui::Panel::top(egui::Id::new("nexus_bar")).show(ui, |ui| {
            let (u, a, r, b) = self.counts();
            ui.horizontal_wrapped(|ui| {
                ui.colored_label(MUTED, format!("{u} undecided"));
                ui.colored_label(BRASS, format!("{a} approved"));
                ui.colored_label(MUTED, format!("{r} rejected  {b} blocked"));
                ui.separator();
                ui.colored_label(MUTED, &self.data.generated_at);
                ui.separator();
                // Breadcrumb. Where you are in the drill-down, and the way back.
                let crumb = match &self.focus {
                    None => "system".to_string(),
                    Some(f) => {
                        let label = self
                            .data
                            .nodes
                            .iter()
                            .find(|n| &n.id == f)
                            .map(|n| n.label.clone())
                            .unwrap_or_else(|| f.clone());
                        format!("system / {label}")
                    }
                };
                if ui.button(format!("< {crumb}")).clicked() {
                    self.focus = None;
                    self.laid_out = false;
                }
                ui.separator();
                let kinds = self.data.kinds();
                for k in kinds {
                    let on = self.filter_kind.as_deref() == Some(k.as_str());
                    if ui.selectable_label(on, &k).clicked() {
                        self.filter_kind = if on { None } else { Some(k.clone()) };
                    }
                }
                ui.separator();
                // Tag overlay selector. Clicking a group recolours the map by
                // that group's derived values.
                let groups: Vec<String> = {
                    let mut g: Vec<String> = self.data.tag_groups.keys().cloned().collect();
                    g.sort();
                    g
                };
                for g in groups {
                    let on = self.tag_group.as_deref() == Some(g.as_str());
                    if ui.selectable_label(on, format!("#{g}")).clicked() {
                        self.tag_group = if on { None } else { Some(g.clone()) };
                    }
                }
                if let Some(f) = self.data.flows.first() {
                    let on = self.flow_on;
                    if ui.selectable_label(on, format!("flow: {}", f.name)).clicked() {
                        self.flow_on = !on;
                    }
                }
                ui.separator();
                if ui.button("save decisions").clicked() {
                    self.save();
                }
                if ui.button("shake").clicked() {
                    let ids: Vec<String> = self.data.nodes.iter().map(|n| n.id.clone()).collect();
                    for (i, id) in ids.iter().enumerate() {
                        let s = ((i * 37) % 41) as f32 - 20.0;
                        let t = ((i * 17) % 31) as f32 - 15.0;
                        self.world.nudge(id, s * 6.0, t * 6.0);
                    }
                }
                if !self.status_line.is_empty() {
                    ui.colored_label(
                        if self.status_line.starts_with("WRITE FAILED") { egui::Color32::LIGHT_RED } else { TEAL },
                        &self.status_line,
                    );
                }
            });
        });

        // Third attempt at this panel's width, so the history is worth recording.
        // `default_size(380)` collapsed it to ~90px. `exact_size(400)` alone did
        // NOT fix it: the second screenshot still showed ~124px with the path and
        // the reject button clipped. A panel persists its PanelState under its Id
        // and stays resizable by default, so the stored width kept winning over the
        // builder. Pinning resizable(false) AND changing the Id to discard the
        // stale state is what actually holds it. Two of the three fixes here were
        // asserted as done before they were looked at.
        // Attempt five, and the first that is not a request to the layout system.
        // default_size(380) -> ~90px. exact_size(400) -> ~124px. Adding
        // resizable(false) and a fresh Id -> unchanged. Every screenshot showed
        // the path, the buttons and the WHY text clipped. So the width is no
        // longer asked for: the rectangle is carved and drawn into directly,
        // which is exactly what the canvas already does without trouble.
        // Viewport, not ui.max_rect(): the latter shrinks as this frame's own
        // children consume it, which made the inspector width depend on the
        // previous frame's layout and converge on ~390px instead of 430.
        let screen = ctx.content_rect();
        let full = egui::Rect::from_min_max(
            egui::pos2(screen.left(), screen.top() + self.bar_h),
            screen.max,
        );
        let insp_w = 430.0_f32.min(full.width() * 0.42);
        let insp_rect = egui::Rect::from_min_max(
            egui::pos2(full.right() - insp_w, full.top()),
            full.max,
        );
        self.canvas_rect = egui::Rect::from_min_max(
            full.min,
            egui::pos2(full.right() - insp_w, full.bottom()),
        );
        if !self.logged_rect {
            self.logged_rect = true;
            let sr = ctx.content_rect();
            eprintln!(
                "RECTS full={:?} insp={:?} canvas={:?} ui_avail={:?}",
                full, insp_rect, self.canvas_rect, ui.available_rect_before_wrap()
            );
        }
        ui.painter().rect_filled(insp_rect, 0.0, PANEL);
        ui.scope_builder(egui::UiBuilder::new().max_rect(insp_rect.shrink(10.0)), |ui| {
            let sel = self.selected.clone();
            let node = sel.and_then(|id| self.data.nodes.iter().find(|n| n.id == id).cloned());
            match node {
                None => {
                    ui.colored_label(MUTED, "nothing selected");
                }
                Some(n) => {
                    ui.colored_label(n.status.color(), n.status.label().to_uppercase());
                    ui.heading(&n.label);
                    ui.colored_label(MUTED, &n.path);
                    ui.separator();

                    // WHAT / WHY / HOW. Written for a fresh BSc graduate: assumes
                    // programming, assumes nothing about this repo's vocabulary.
                    egui::ScrollArea::vertical()
                        .max_height(430.0)
                        .show(ui, |ui| {
                            ui.colored_label(TEAL, "WHAT");
                            ui.label(if n.what.is_empty() { &n.summary } else { &n.what });

                            ui.add_space(8.0);
                            ui.colored_label(TEAL, "WHY");
                            if n.why.is_empty() {
                                // Never fill this in. An empty reason is a fact
                                // about the source, and inventing one here would
                                // make the tool a worse reader than the file.
                                ui.colored_label(
                                    MUTED,
                                    "The source states no reason. Not summarised, not guessed.",
                                );
                            } else {
                                for w in &n.why {
                                    ui.label(format!("• {w}"));
                                }
                            }

                            ui.add_space(8.0);
                            ui.colored_label(TEAL, "HOW");
                            let lines = n.how_lines();
                            if lines.is_empty() {
                                ui.colored_label(MUTED, "no mechanism extracted");
                            } else {
                                for l in lines {
                                    ui.colored_label(INK, l);
                                }
                            }

                            if !n.tags.is_empty() {
                                ui.add_space(8.0);
                                ui.colored_label(TEAL, "TAGS");
                                let mut ts: Vec<(&String, &String)> = n.tags.iter().collect();
                                ts.sort();
                                for (g, v) in ts {
                                    ui.colored_label(Self::tag_color(v), format!("{g}: {v}"));
                                }
                            }

                            let (inc, outg) = self.connections(&n.id);
                            if !inc.is_empty() || !outg.is_empty() {
                                ui.add_space(8.0);
                                ui.colored_label(TEAL, "CONNECTIONS");
                                for l in outg.iter().take(10) {
                                    ui.colored_label(INK, l);
                                }
                                for l in inc.iter().take(10) {
                                    ui.colored_label(MUTED, l);
                                }
                            }

                            if !n.terms.is_empty() {
                                ui.add_space(8.0);
                                ui.colored_label(TEAL, "TERMS  (click to open)");
                                ui.horizontal_wrapped(|ui| {
                                    for t in &n.terms {
                                        let open = self.open_term.as_deref() == Some(t.as_str());
                                        if ui.selectable_label(open, t).clicked() {
                                            self.open_term =
                                                if open { None } else { Some(t.clone()) };
                                        }
                                    }
                                });
                                if let Some(t) = self.open_term.clone() {
                                    if let Some(g) = self.data.glossary.get(&t) {
                                        ui.add_space(4.0);
                                        ui.colored_label(BRASS, format!("{t}: {}", g.one_line));
                                        if let Some(w) = &g.where_ {
                                            ui.colored_label(MUTED, format!("seen in {w}"));
                                        }
                                    }
                                }
                            }
                        });

                    ui.separator();
                    ui.horizontal_wrapped(|ui| {
                        if ui.button("approve  a").clicked() { self.set_status(Status::Approved); }
                        if ui.button("reject  r").clicked() { self.set_status(Status::Rejected); }
                        if ui.button("blocked  b").clicked() { self.set_status(Status::Blocked); }
                        if ui.button("undecide  u").clicked() { self.set_status(Status::Undecided); }
                    });
                    ui.separator();
                    ui.colored_label(MUTED, "note");
                    let id = n.id.clone();
                    if let Some(m) = self.data.nodes.iter_mut().find(|x| x.id == id) {
                        ui.text_edit_multiline(&mut m.note);
                    }
                    if !n.links.is_empty() {
                        ui.separator();
                        ui.colored_label(MUTED, "links out");
                        for l in &n.links {
                            if ui.link(l).clicked() {
                                self.selected = Some(l.clone());
                            }
                        }
                    }
                }
            }
            if !self.data.contracts.is_empty() {
                ui.separator();
                ui.colored_label(MUTED, "plan-divergence contracts");
                for c in &self.data.contracts {
                    let cat = c.category.clone().unwrap_or_else(|| "-".into());
                    ui.colored_label(
                        if c.outcome.as_deref() == Some("held") { TEAL } else { BRASS },
                        format!("{}  {}  drift {}", c.id, cat, c.drift),
                    );
                }
            }
        });

        // No CentralPanel: it claims all remaining space and fills it, which is
        // what was painting over the inspector. The canvas gets exactly the rect
        // left beside the inspector, and fills only that.
        ui.painter().rect_filled(self.canvas_rect, 0.0, GROUND);
        ui.scope_builder(
            egui::UiBuilder::new().max_rect(self.canvas_rect),
            |ui| {
                let rect = self.canvas_rect;
                let resp = ui.allocate_rect(rect, egui::Sense::click_and_drag());
                self.relayout(rect);
                self.laid_out = true;

                // cursor force field
                if let Some(p) = resp.hover_pos() {
                    let speed = self
                        .last_pointer
                        .map(|q| (p - q).length())
                        .unwrap_or(0.0)
                        .min(60.0);
                    self.world.apply_cursor(p.x, p.y, 150.0, speed);
                    self.last_pointer = Some(p);
                }

                self.world.apply_anchors(0.35);
                let edges = self.edges.clone();
                self.world.apply_springs(&edges, 180.0, 0.05);
                self.world.step();

                let mut descend: Option<String> = None;
                if resp.clicked() {
                    if let Some(p) = resp.interact_pointer_pos() {
                        for n in &self.data.nodes {
                            if let Some((x, y)) = self.world.position(&n.id) {
                                if (p.x - x).abs() < crate::physics::NODE_HALF_W
                                    && (p.y - y).abs() < crate::physics::NODE_HALF_H
                                {
                                    self.selected = Some(n.id.clone());
                                    // A container is a door, not a leaf: clicking
                                    // one descends into its components.
                                    if n.kind == "Container" && self.focus.as_deref() != Some(n.id.as_str()) {
                                        descend = Some(n.id.clone());
                                    }
                                    break;
                                }
                            }
                        }
                    }
                }

                if let Some(d) = descend {
                    self.focus = Some(d);
                    self.laid_out = false;
                }

                let painter = ui.painter_at(rect);

                // Column captions. The HTML console has these and the first render
                // of this one did not, so the columns were unlabelled and you could
                // not tell a spec column from a research column.
                let kinds = self.data.kinds();
                let col_w = rect.width() / kinds.len().max(1) as f32;
                for (i, k) in kinds.iter().enumerate() {
                    painter.text(
                        egui::pos2(rect.left() + col_w * (i as f32 + 0.5), rect.top() + 14.0),
                        egui::Align2::CENTER_CENTER,
                        k.to_uppercase(),
                        egui::FontId::monospace(10.0),
                        egui::Color32::from_rgb(0x3d, 0x5f, 0x60),
                    );
                }

                for (a, b) in &self.edges {
                    if let (Some(pa), Some(pb)) = (self.world.position(a), self.world.position(b)) {
                        painter.line_segment(
                            [egui::pos2(pa.0, pa.1), egui::pos2(pb.0, pb.1)],
                            egui::Stroke::new(1.0, RULE),
                        );
                    }
                }
                for n in &self.data.nodes {
                    if !self.node_visible(n) {
                        continue;
                    }
                    let (x, y) = match self.world.position(&n.id) {
                        Some(p) => p,
                        None => continue,
                    };
                    let is_sel = self.selected.as_deref() == Some(n.id.as_str());
                    let r = egui::Rect::from_center_size(
                        egui::pos2(x, y),
                        egui::vec2(crate::physics::NODE_HALF_W * 2.0, crate::physics::NODE_HALF_H * 2.0),
                    );
                    // Tag overlay wins over status colouring while a group is
                    // active: the whole point of the overlay is to read one
                    // property across the map at once.
                    let stroke_c = if let Some(g) = &self.tag_group {
                        match n.tags.get(g) {
                            Some(v) => Self::tag_color(v),
                            None => RULE,
                        }
                    } else if n.status == Status::Undecided {
                        if is_sel { TEAL } else { RULE }
                    } else {
                        n.status.color()
                    };
                    painter.rect_filled(r, 0.0, if is_sel { PANEL } else { GROUND });
                    painter.rect_stroke(
                        r,
                        0.0,
                        egui::Stroke::new(if is_sel { 2.0 } else { 1.0 }, stroke_c),
                        egui::StrokeKind::Inside,
                    );
                    // 15 chars was too few to tell documents apart: four separate
                    // files all rendered as "RESEARCH PROMPT." in the first run.
                    // The box is sized to the text instead, capped, and the ellipsis
                    // is a real one so a truncated title cannot be mistaken for a
                    // sentence that happens to end in a full stop.
                    let mut short: String = n.label.chars().take(LABEL_CHARS).collect();
                    if n.label.chars().count() > LABEL_CHARS {
                        short.push('…');
                    }
                    if let Some(step) = self.flow_step_of(&n.id) {
                        let c = egui::pos2(x - crate::physics::NODE_HALF_W - 9.0, y);
                        painter.circle_filled(c, 9.0, BRASS);
                        painter.text(
                            c,
                            egui::Align2::CENTER_CENTER,
                            format!("{step}"),
                            egui::FontId::monospace(10.0),
                            GROUND,
                        );
                    }
                    painter.text(
                        egui::pos2(x, y),
                        egui::Align2::CENTER_CENTER,
                        short,
                        egui::FontId::monospace(11.0),
                        if n.status == Status::Approved { BRASS } else { INK },
                    );
                }
            });
    }
}
