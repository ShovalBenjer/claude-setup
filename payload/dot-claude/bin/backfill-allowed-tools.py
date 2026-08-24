#!/usr/bin/env python3
"""Backfill accurate allowed-tools contracts on sensitive skills. Idempotent: replaces any
existing allowed-tools line (including the earlier broken one) with the correct value."""
import pathlib

SK = pathlib.Path.home() / ".claude" / "skills"
M = {
    "agent-builder": ["Bash", "Read", "Write", "Edit", "Grep", "Glob"],
    "azure-activity-watch": ["Bash", "Read", "Grep", "Glob"],
    "azure-audit": ["Bash", "Read", "Write", "Grep", "Glob"],
    "azure-devops": ["Bash", "Read", "Edit", "Grep", "Glob"],
    "azure-keyvault-secrets": ["Bash", "Read", "Write"],
    "azure-runtime": ["Bash", "Read", "Grep", "Glob"],
    "cleanup-crew": ["Bash", "Read", "Edit", "Grep", "Glob"],
    "commit-push-pr": ["Bash", "Read", "Grep", "Glob"],
    "eval-runner": ["Bash", "Read", "Edit", "Grep", "Glob"],
    "jira-task-draft": ["Read", "Write"],
    "kill-stale": ["Bash", "Read"],
    "mutation-runner": ["Bash", "Read", "Grep", "Glob"],
    "pii-scrubber": ["Bash", "Read", "Write", "Grep"],
    "prod-deploy-rules": ["Bash", "Read", "Grep", "Glob"],
    "watchdog": ["Bash", "Read", "Write", "Edit", "Grep", "Glob"],
}


def main() -> None:
    fixed = []
    for name, tools in M.items():
        f = SK / name / "SKILL.md"
        if not f.exists() or not f.read_text().startswith("---"):
            continue
        _, fm, body = f.read_text().split("---", 2)
        val = "[" + ", ".join('"%s"' % t for t in tools) + "]"
        keep = [ln for ln in fm.split("\n") if not ln.strip().startswith("allowed-tools:")]
        fm_new = "\n".join(keep).rstrip("\n") + "\nallowed-tools: " + val + "\n"
        f.write_text("---" + fm_new + "---" + body)
        fixed.append(name)
    print("fixed", len(fixed), ":", ", ".join(fixed))


if __name__ == "__main__":
    main()
