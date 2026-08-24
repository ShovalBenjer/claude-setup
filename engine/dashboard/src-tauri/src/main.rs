// Not compiled in this slice; see commands.rs doc comment.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    dashboard_lib::run();
}
