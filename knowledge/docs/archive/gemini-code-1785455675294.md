# MISSION SPECIFICATION: Build "nexus-engine-rs"

Build a single-binary, GPU-accelerated Rust engine that combines an Agentic Divergence Sandbox with a Real-Time Physics & Visual Architecture Auditor.

The system must bypass web DOM overhead entirely by utilizing immediate-mode GPU rendering (`egui` + `wgpu`), a 2D physical solver (`rapier2d`), AST syntax parsing (`tree-sitter`), zero-cost git worktree reverts, and WGSL compute shaders.

---

## 1. CARGO DEPENDENCIES (`Cargo.toml`)

```toml
[package]
name = "nexus-engine-rs"
version = "0.1.0"
edition = "2021"

[dependencies]
eframe = "0.28"
egui = "0.28"
wgpu = "0.20"
rapier2d = "0.18"
petgraph = "0.6"
similar = { version = "2.4", features = ["inline"] }
bytemuck = { version = "1.16", features = ["derive"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
tokio = { version = "1.38", features = ["full"] }
chrono = { version = "0.4", features = ["serde"] }
