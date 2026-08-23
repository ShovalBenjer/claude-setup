//! Tauri app entry (library form, matches the `tauri-cli` scaffold shape).

pub mod commands;
mod meme_process;

pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            commands::list_projects,
            commands::read_gate_runs,
            commands::latest_gate_verdict,
            commands::read_claims_cmd,
            commands::read_agent_spawns_cmd,
            commands::read_skill_use_cmd,
            commands::read_routing_cmd,
            commands::read_bus_cmd,
            commands::list_modules,
            commands::set_module_enabled,
            commands::meme_list_events,
            commands::meme_find,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
