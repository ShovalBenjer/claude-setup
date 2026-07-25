#!/usr/bin/env python3
"""Read-only audit of the live and canonical Claude Code control plane.

The report never prints environment-variable values or suspicious setting
values. It reports only names, paths, counts, and remediation-oriented findings.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable


SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "info": 3}
SECRET_KEY = re.compile(
    r"(?i)(?:api[_-]?key|secret|token|password|credential|private[_-]?key|sas)"
)
SECRET_VALUE = re.compile(
    r"(?i)(?:[?&](?:sig|token|key|secret|code)=|bearer\s+[A-Za-z0-9._-]{12,}|"
    r"(?:sk|pat|ghp|xox)[-_A-Za-z0-9]{16,})"
)
PROVIDER_ENV_NAMES = {
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
}
HOOK_SUFFIXES = {".py", ".sh", ".ps1", ".cmd", ".bat", ".exe"}
STALE_GLOBAL_PHRASES = (
    "senior solution engineer",
    "24% to 64%",
    "/home/shovalbe",
    "shoval.be",
    "seekapa-specific",
)


def finding(severity: str, check: str, message: str, path: Path | None = None) -> dict[str, str]:
    item = {"severity": severity, "check": check, "message": message}
    if path is not None:
        item["path"] = str(path)
    return item


def json_file(path: Path, findings: list[dict[str, str]]) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        findings.append(finding("critical", "json", f"Invalid JSON: {type(exc).__name__}", path))
        return None
    if not isinstance(data, dict):
        findings.append(finding("high", "json", "Top-level JSON value is not an object.", path))
        return None
    return data


def absolute_hook_paths(settings: dict[str, Any]) -> Iterable[Path]:
    hooks = settings.get("hooks", {})
    if not isinstance(hooks, dict):
        return
    for groups in hooks.values():
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            for hook in group.get("hooks", []):
                if not isinstance(hook, dict):
                    continue
                values = [hook.get("command"), *hook.get("args", [])]
                for value in values:
                    if not isinstance(value, str):
                        continue
                    candidate = Path(value)
                    if candidate.is_absolute() and candidate.suffix.lower() in HOOK_SUFFIXES:
                        yield candidate


def audit_settings(path: Path, label: str, findings: list[dict[str, str]]) -> dict[str, Any] | None:
    data = json_file(path, findings)
    if data is None:
        return None
    permissions = data.get("permissions", {})
    mode = permissions.get("defaultMode") if isinstance(permissions, dict) else None
    if mode == "bypassPermissions":
        findings.append(finding("critical", "permissions", f"{label} uses bypassPermissions.", path))
    elif mode is not None and mode not in {"acceptEdits", "plan", "default"}:
        findings.append(finding("medium", "permissions", f"{label} permission mode is {mode!r}.", path))
    if data.get("skipDangerousModePermissionPrompt") is True:
        findings.append(finding("high", "permissions", f"{label} suppresses the dangerous-mode warning.", path))
    if data.get("skipAutoPermissionPrompt") is True:
        findings.append(finding("high", "permissions", f"{label} suppresses automatic permission prompts.", path))
    if data.get("remoteControlAtStartup") is True:
        findings.append(finding("medium", "remote-control", f"{label} starts remote control automatically.", path))
    if data.get("enableAllProjectMcpServers") is True:
        findings.append(finding("high", "mcp", f"{label} enables every project MCP server.", path))

    missing = sorted({str(item) for item in absolute_hook_paths(data) if not item.exists()})
    for hook_path in missing:
        findings.append(finding("critical", "hook-existence", "Referenced hook file is missing.", Path(hook_path)))
    return data


def walk_settings(root: Path) -> Iterable[Path]:
    if not root.exists():
        return
    pruned = {
        ".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build",
        "automation-chrome-profile", "cache", "backups", "file-history", "archive",
    }
    for base, directories, files in os.walk(root):
        directories[:] = [
            name for name in directories
            if name not in pruned
            and "retired" not in name.lower()
            and "broken-worktree" not in name.lower()
        ]
        current = Path(base)
        if ".claude" not in {part.lower() for part in current.parts}:
            continue
        for name in files:
            if name.lower().startswith("settings") and name.lower().endswith(".json"):
                yield current / name


def secret_shape_paths(value: Any, path: str = "$", key: str = "") -> list[str]:
    if isinstance(value, dict):
        matches: list[str] = []
        for child_key, child in value.items():
            matches.extend(
                secret_shape_paths(child, f"{path}.{child_key}", str(child_key))
            )
        return matches
    if isinstance(value, list):
        matches = []
        for index, child in enumerate(value):
            matches.extend(secret_shape_paths(child, f"{path}[{index}]", key))
        return matches
    if isinstance(value, str):
        if SECRET_VALUE.search(value):
            return [path]
        if SECRET_KEY.search(key) and value.strip() and not value.startswith("${"):
            return [path]
    return []


def audit_rule_context(rule_root: Path, findings: list[dict[str, str]]) -> dict[str, int]:
    files = sorted(rule_root.glob("*.md")) if rule_root.exists() else []
    scoped = 0
    unconditional_bytes = 0
    stub_count = 0
    for path in files:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if text.startswith("---\n") or text.startswith("---\r\n"):
            scoped += 1
        else:
            unconditional_bytes += len(text.encode("utf-8"))
        if len(text) < 256 and text.strip().startswith(("/home/", "/Users/")):
            stub_count += 1
            findings.append(finding("high", "broken-pointer", "Rule is a non-portable path stub.", path))
    if unconditional_bytes > 24_000:
        findings.append(
            finding(
                "medium",
                "context-budget",
                f"Unconditional global rules total {unconditional_bytes} bytes; scope or consolidate them.",
                rule_root,
            )
        )
    return {
        "files": len(files),
        "path_scoped": scoped,
        "unconditional": len(files) - scoped,
        "unconditional_bytes": unconditional_bytes,
        "path_stubs": stub_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-root", default=str(Path.home() / ".claude"))
    parser.add_argument("--canonical-root", default=str(Path.home() / "claude-setup" / "dot-claude"))
    parser.add_argument("--project-root", default=str(Path.cwd()))
    args = parser.parse_args()

    live = Path(args.live_root)
    canonical = Path(args.canonical_root)
    project = Path(args.project_root)
    findings: list[dict[str, str]] = []

    live_settings = live / "settings.json"
    canonical_settings = canonical / "settings.json"
    audit_settings(live_settings, "live settings", findings)
    audit_settings(canonical_settings, "canonical settings", findings)

    seen_settings = {live_settings.resolve(), canonical_settings.resolve()}
    project_setting_count = 0
    secret_shape_files = 0
    for path in walk_settings(project):
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        if resolved in seen_settings:
            continue
        data = audit_settings(path, "project settings", findings)
        project_setting_count += 1
        locations = secret_shape_paths(data) if data is not None else []
        if locations:
            secret_shape_files += 1
            findings.append(
                finding(
                    "critical",
                    "secret-shape",
                    "A setting has a credential-like key or value at "
                    + ", ".join(locations[:6])
                    + "; rotate it and use secret injection. Values withheld.",
                    path,
                )
            )

    global_contract = live / "CLAUDE.md"
    contract_bytes = 0
    if not global_contract.exists():
        findings.append(finding("high", "global-contract", "Live global CLAUDE.md is missing.", global_contract))
    else:
        contract = global_contract.read_text(encoding="utf-8-sig", errors="replace")
        contract_bytes = len(contract.encode("utf-8"))
        if contract_bytes > 12_000:
            findings.append(finding("medium", "context-budget", f"Global CLAUDE.md is {contract_bytes} bytes.", global_contract))
        lowered = contract.lower()
        for phrase in STALE_GLOBAL_PHRASES:
            if phrase in lowered:
                findings.append(finding("high", "stale-global-context", f"Found stale phrase: {phrase}", global_contract))

    provider_overrides = sorted(name for name in PROVIDER_ENV_NAMES if os.environ.get(name))
    if provider_overrides:
        findings.append(
            finding(
                "high",
                "provider-routing",
                "Provider/API override variables are present: " + ", ".join(provider_overrides) + ". Values withheld.",
            )
        )

    rule_stats = audit_rule_context(live / "rules", findings)
    skill_state: dict[str, str] = {}
    for name in ("prove-implementation", "learn-on-demand"):
        entrypoint = live / "skills" / name / "SKILL.md"
        skill_state[name] = "present" if entrypoint.exists() else "missing"
        if not entrypoint.exists():
            findings.append(finding("high", "required-skill", f"Required skill is missing: {name}", entrypoint))

    counts = {severity: sum(item["severity"] == severity for item in findings) for severity in SEVERITY_ORDER}
    findings.sort(key=lambda item: (SEVERITY_ORDER[item["severity"]], item.get("path", ""), item["check"]))
    result = {
        "audit": "claude-control-plane.v1",
        "live_root": str(live),
        "canonical_root": str(canonical),
        "project_root": str(project),
        "summary": {
            "findings": len(findings),
            "by_severity": counts,
            "project_settings_checked": project_setting_count,
            "credential_shape_files": secret_shape_files,
            "global_contract_bytes": contract_bytes,
            "provider_override_names": provider_overrides,
            "rule_context": rule_stats,
            "required_skills": skill_state,
        },
        "findings": findings,
    }
    print(json.dumps(result, indent=2))
    return 1 if counts["critical"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
