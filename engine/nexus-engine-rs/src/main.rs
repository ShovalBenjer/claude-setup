//! nexus-engine-rs: a native, physics-driven viewer over the same plan contract
//! the browser console reads.
//!
//! Data comes from `command_center/plan_data.js`, produced by
//! `command_center/plan_export.py`. Run the exporter first. If the file is absent
//! this exits with a message rather than opening an empty window, because an empty
//! graph and a missing data file look identical on screen and only one of them is
//! a problem you can fix.

mod app;
mod models;
mod physics;

use std::path::PathBuf;

fn repo_root() -> PathBuf {
    // projects/nexus-engine-rs -> projects -> repo
    let here = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    here.parent()
        .and_then(|p| p.parent())
        .map(PathBuf::from)
        .unwrap_or(here)
}

fn main() -> eframe::Result<()> {
    let root = repo_root();
    let data_path = std::env::args()
        .nth(1)
        .filter(|a| !a.starts_with("--"))
        .map(PathBuf::from)
        .unwrap_or_else(|| root.join("command_center").join("plan_data.js"));

    let src = match std::fs::read_to_string(&data_path) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("cannot read {}: {e}", data_path.display());
            eprintln!("run: python command_center/plan_export.py");
            std::process::exit(2);
        }
    };
    let data = match models::PlanData::from_js(&src) {
        Ok(d) => d,
        Err(e) => {
            eprintln!("{} is not the expected contract: {e}", data_path.display());
            std::process::exit(2);
        }
    };
    println!(
        "loaded {} nodes, {} edges, {} contracts from {}",
        data.nodes.len(),
        data.edges.len(),
        data.contracts.len(),
        data_path.display()
    );

    // --check exits after parsing. This is what a headless box can run: it
    // exercises the real data path end to end without needing a window server,
    // which is the difference between "it compiles" and "it reads your repo".
    if std::env::args().any(|a| a == "--check") {
        println!("check ok");
        return Ok(());
    }

    let decisions = root.join("state").join("plan_decisions.json");
    let opts = eframe::NativeOptions {
        viewport: eframe::egui::ViewportBuilder::default()
            .with_inner_size([1500.0, 900.0])
            .with_title("nexus  ·  plan graph"),
        ..Default::default()
    };
    eframe::run_native(
        "nexus-engine-rs",
        opts,
        Box::new(move |_cc| Ok(Box::new(app::App::new(data, decisions)))),
    )
}
