//! Regression oracle for the dead IPC boundary this file is named after
//! (`window.__TAURI__` was never injected because `withGlobalTauri`
//! defaults to `false` in Tauri 2, and `dashboard/web/src/ipc.ts` used to
//! resolve `invoke` off that global at call time, so every real webview
//! call rejected). The fix moved the frontend to `@tauri-apps/api/core`'s
//! `invoke`, which is a JS-side change this Rust test cannot see directly.
//! What this test DOES prove, headlessly (no window, no webview, no
//! display server): that the Rust half of the boundary -- the exact
//! `invoke_handler(tauri::generate_handler![...])` list registered in
//! `src/lib.rs` -- dispatches a real `InvokeRequest` for `cmd:
//! "latest_gate_verdict"` through Tauri's own IPC message-processing path
//! (`Webview::on_message`, `tauri::test::get_ipc_response`) and returns
//! real data deserialized from an actual `state/gate-runs.jsonl` fixture,
//! not a mocked function call. `tauri::test::mock_builder()` +
//! `tauri::test::get_ipc_response` are Tauri's own supported headless IPC
//! test surface (`tauri::test` module, "test" feature), not a bespoke
//! substitute for the real dispatcher.
//!
//! What this test does NOT cover, named honestly: it never creates a real
//! OS window and never loads `window.__TAURI_INTERNALS__` inside an actual
//! WebKitGTK/WebView2 engine, so it cannot detect a frontend-only wiring
//! break (wrong import path, wrong global name, a JS bundling problem).
//! `dashboard/web/scripts/dom-test.mjs` covers that half, stubbing
//! `window.__TAURI_INTERNALS__.invoke` and driving the real `ipc.ts`
//! exports through it. Together the two tests cover both sides of the
//! boundary; neither alone proves a live webview round-trip, which was
//! attempted and found infeasible in this sandbox (WSLg RDP surface never
//! paints Tauri/WebKitGTK windows; see the PR body for the measured
//! evidence: Weston assigns real window IDs to each launch, but the
//! surface never renders and no IPC call ever fires from a live window).

use dashboard_lib::commands;
// See `build_test_app` below for why `list_modules`/`set_module_enabled`
// (AppHandle-typed commands) are excluded from this mock registration.
use std::fs;
use std::io::Write;
use tauri::ipc::CallbackFn;
use tauri::test::{get_ipc_response, mock_builder, INVOKE_KEY};
use tauri::webview::InvokeRequest;
use tauri::WebviewWindowBuilder;

/// Registers the same project/ledger-reading commands `src/lib.rs` wires
/// against the real runtime, on `MockRuntime` instead. Any command dropped
/// from this list (the exact defect class this test exists to catch, since
/// it is how the frontend/backend boundary drifts silently) makes a
/// dispatch below fail with "unknown command" instead of a real response.
///
/// `list_modules` and `set_module_enabled` are deliberately NOT registered
/// here: both take a real `tauri::AppHandle<R>` (used to resolve
/// `app_config_dir()`), which only implements `CommandArg` for a concrete
/// desktop runtime, not `MockRuntime`. That is a `tauri::test` limitation
/// on AppHandle-typed commands, not a gap in this boundary's coverage --
/// those two commands take no project path and are unrelated to the
/// `window.__TAURI__`/`__TAURI_INTERNALS__` defect this test targets. Their
/// Rust-side logic is already covered by `dashboard_core::modules`'s own
/// unit tests (round-trip write/read, unknown-id handling) under `cargo
/// test --workspace`.
fn build_test_app() -> tauri::App<tauri::test::MockRuntime> {
    mock_builder()
        .invoke_handler(tauri::generate_handler![
            commands::list_projects,
            commands::read_gate_runs,
            commands::latest_gate_verdict,
            commands::read_claims_cmd,
            commands::read_agent_spawns_cmd,
            commands::read_skill_use_cmd,
            commands::read_routing_cmd,
            commands::read_bus_cmd,
            commands::meme_list_events,
            commands::meme_find,
        ])
        // The real `tauri.conf.json` + `capabilities/default.json` (not
        // `tauri::test::mock_context`'s empty ACL), so this test's
        // permission resolution matches what the shipped app actually
        // grants a webview -- if `latest_gate_verdict` were missing from
        // the real capability file, this test would fail the same way the
        // live app would reject the call.
        .build(tauri::generate_context!())
        .expect("failed to build mock app")
}

fn invoke_request(cmd: &str, args: serde_json::Value) -> InvokeRequest {
    InvokeRequest {
        cmd: cmd.into(),
        callback: CallbackFn(0),
        error: CallbackFn(1),
        // Matches `tauri::test`'s own doc example: on Windows/Android the
        // local origin is `http://tauri.localhost`, everywhere else
        // (including this Linux CI target) it is `tauri://localhost`. The
        // wrong scheme resolves as a remote origin, which the app's
        // capability never grants, and denies every command -- not a
        // property of the app under test.
        url: if cfg!(any(windows, target_os = "android")) {
            "http://tauri.localhost"
        } else {
            "tauri://localhost"
        }
        .parse()
        .unwrap(),
        body: tauri::ipc::InvokeBody::Json(args),
        headers: Default::default(),
        invoke_key: INVOKE_KEY.to_string(),
    }
}

#[test]
fn latest_gate_verdict_ipc_round_trip_returns_real_fixture_data() {
    // Real fixture, not a fabricated struct literal: a project root with a
    // state/gate-runs.jsonl the command reads exactly the way the shipped
    // app would (dashboard-core's own gate_runs::latest_gate_verdict).
    let project_dir = tempfile::tempdir().expect("tempdir");
    let state_dir = project_dir.path().join("state");
    fs::create_dir_all(&state_dir).unwrap();
    let mut f = fs::File::create(state_dir.join("gate-runs.jsonl")).unwrap();
    writeln!(
        f,
        r#"{{"ts":"2026-08-23T00:00:00Z","project":"fixture","project_path":"/tmp/fixture","commit":"deadbeef","dirty":false,"fingerprint":"abc123","partial":false,"verdict":"PASS","domains":{{}},"blocking":[],"waivers_unconfirmed":[],"unmeasured":[],"duration_seconds":1.5,"domain_seconds":{{}}}}"#
    )
    .unwrap();

    let app = build_test_app();
    let webview = WebviewWindowBuilder::new(&app, "main", Default::default())
        .build()
        .expect("failed to build mock webview");

    let project_path = project_dir.path().to_string_lossy().to_string();
    let request = invoke_request(
        "latest_gate_verdict",
        serde_json::json!({ "project": project_path }),
    );

    let response = get_ipc_response(&webview, request)
        .expect("latest_gate_verdict IPC call must succeed, not reject");
    let value: serde_json::Value = response
        .deserialize()
        .expect("response body must deserialize as JSON");

    // Real data from the fixture file, round-tripped through the same
    // dispatch path a live webview's window.__TAURI_INTERNALS__.invoke
    // would use -- not a value this test invented.
    assert_eq!(value["commit"], "deadbeef");
    assert_eq!(value["verdict"], "pass");
    assert_eq!(value["fingerprint"], "abc123");
}

#[test]
fn unknown_command_is_rejected_not_silently_ignored() {
    // Guards the oracle itself: if this ever returns Ok, the mock dispatch
    // stopped enforcing the registered command list and every assertion
    // above would be meaningless.
    let app = build_test_app();
    let webview = WebviewWindowBuilder::new(&app, "main", Default::default())
        .build()
        .expect("failed to build mock webview");

    let request = invoke_request("this_command_does_not_exist", serde_json::json!({}));
    let response = get_ipc_response(&webview, request);
    assert!(
        response.is_err(),
        "an unregistered command must reject, not resolve"
    );
}
