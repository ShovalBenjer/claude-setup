//! Module registry (DASH-1 slice 3). Program design section 2.3 names
//! `list_modules`/`set_module_enabled` writing to "app-local config", not
//! `state/`, so this file's read/write logic never touches a ledger and does
//! not need the skip-and-count convention for correctness (it does still use
//! it defensively: a malformed `modules.json` should not crash the app).
//!
//! Kept tauri-free like every other `dashboard-core` module: `read_modules`/
//! `write_modules` take a plain `&Path` so this round-trips in a unit test
//! against a `tempfile::TempDir`, with no `AppHandle` and no running app.
//! Path resolution (`app_config_dir()`) is the one thing that stays in
//! `src-tauri/src/commands.rs`.

use serde::{Deserialize, Serialize};
use std::fs;
use std::io;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ModuleDescriptor {
    pub id: String,
    pub name: String,
    pub enabled: bool,
}

/// On-disk shape of `modules.json`. A thin wrapper (not a bare
/// `Vec<ModuleDescriptor>`) so a future field (e.g. schema version) can be
/// added without breaking the array shape on disk.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ModulesFile {
    pub modules: Vec<ModuleDescriptor>,
}

/// The registry seeded on first run (no `modules.json` yet): the meme module
/// is the first real module (program design section 3, `MemeModule` under
/// `ModuleRegistry`), registered enabled by default.
pub fn default_modules() -> ModulesFile {
    ModulesFile {
        modules: vec![ModuleDescriptor {
            id: "meme".to_string(),
            name: "Meme events".to_string(),
            enabled: true,
        }],
    }
}

/// Read `modules.json`. Missing file -> seeded defaults (not an error: same
/// "dashboard runs before its first row" convention as the ledger readers).
/// Malformed file -> seeded defaults too, since a corrupt config is not
/// recoverable partially and failing open to defaults beats a crash.
pub fn read_modules(path: &Path) -> ModulesFile {
    match fs::read_to_string(path) {
        Ok(content) => serde_json::from_str::<ModulesFile>(&content).unwrap_or_else(|_| default_modules()),
        Err(_) => default_modules(),
    }
}

/// Write `modules.json` atomically enough for this use case: write to a
/// sibling temp file, then rename over the target. Avoids a torn write if
/// the process is killed mid-write, which would otherwise corrupt the file
/// `read_modules` above falls back to defaults on.
pub fn write_modules(path: &Path, file: &ModulesFile) -> io::Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let tmp_path = path.with_extension("json.tmp");
    let content = serde_json::to_string_pretty(file)?;
    fs::write(&tmp_path, content)?;
    fs::rename(&tmp_path, path)?;
    Ok(())
}

/// Toggle one module's `enabled` flag and persist. Returns `false` if `id`
/// is not a registered module (caller maps this to `IpcError::InvalidProject`
/// per the program design's reuse of that variant for "unknown module id").
pub fn set_module_enabled(path: &Path, id: &str, enabled: bool) -> io::Result<bool> {
    let mut file = read_modules(path);
    let Some(m) = file.modules.iter_mut().find(|m| m.id == id) else {
        return Ok(false);
    };
    m.enabled = enabled;
    write_modules(path, &file)?;
    Ok(true)
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn modules_path(dir: &TempDir) -> std::path::PathBuf {
        dir.path().join("modules.json")
    }

    #[test]
    fn missing_file_returns_defaults() {
        let dir = TempDir::new().expect("tempdir");
        let file = read_modules(&modules_path(&dir));
        assert_eq!(file, default_modules());
        assert!(file.modules.iter().any(|m| m.id == "meme" && m.enabled));
    }

    #[test]
    fn malformed_file_falls_back_to_defaults_without_panic() {
        let dir = TempDir::new().expect("tempdir");
        let path = modules_path(&dir);
        fs::write(&path, "{not valid json,,,").expect("write");
        let file = read_modules(&path);
        assert_eq!(file, default_modules());
    }

    /// Acceptance check: toggling a module persists across a simulated app
    /// restart, exercised as two independent reads separated by a write, per
    /// the slice-3 acceptance row ("toggle state persists" / "test via two
    /// reads").
    #[test]
    fn toggle_persists_across_two_reads() {
        let dir = TempDir::new().expect("tempdir");
        let path = modules_path(&dir);

        // First "session": read seeds defaults (meme enabled), then toggle off.
        let first_read = read_modules(&path);
        assert!(first_read.modules[0].enabled);
        let toggled = set_module_enabled(&path, "meme", false).expect("write ok");
        assert!(toggled);

        // Second "session" (simulated restart): fresh read from disk.
        let second_read = read_modules(&path);
        assert!(!second_read.modules[0].enabled, "toggle survived restart");

        // Third "session": toggle back on, verify again.
        set_module_enabled(&path, "meme", true).expect("write ok");
        let third_read = read_modules(&path);
        assert!(third_read.modules[0].enabled);
    }

    #[test]
    fn unknown_module_id_returns_false_without_writing() {
        let dir = TempDir::new().expect("tempdir");
        let path = modules_path(&dir);
        let found = set_module_enabled(&path, "does-not-exist", false).expect("no io error");
        assert!(!found);
        assert!(!path.exists(), "no file written for an unknown module id");
    }

    #[test]
    fn round_trip_write_then_read() {
        let dir = TempDir::new().expect("tempdir");
        let path = modules_path(&dir);
        let file = ModulesFile {
            modules: vec![
                ModuleDescriptor { id: "meme".into(), name: "Meme events".into(), enabled: false },
                ModuleDescriptor { id: "other".into(), name: "Other".into(), enabled: true },
            ],
        };
        write_modules(&path, &file).expect("write");
        let read_back = read_modules(&path);
        assert_eq!(read_back, file);
    }
}
