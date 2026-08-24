#!/usr/bin/env bash
set -euo pipefail

echo "== Claude Code =="
command -v claude || true
claude --version || true

echo
echo "== Memory =="
free -h || true

echo
echo "== Claude / Node / MCP Processes =="
ps -eo pid,ppid,pcpu,pmem,rss,etime,comm,args --sort=-%mem \
  | rg 'claude|node|bun|mcp|obscura' \
  | rg -v 'rg claude|claude-resource-check' || true

echo
echo "== Active Settings =="
jq '{env, hooks: (.hooks | keys), skipDangerousModePermissionPrompt}' "$HOME/.claude/settings.json" 2>/dev/null || true
jq '{enableAllProjectMcpServers, enabledMcpjsonServers, sandbox}' "$HOME/.claude/settings.local.json" 2>/dev/null || true

echo
echo "== Claude State Size =="
du -xhd1 "$HOME/.claude" 2>/dev/null | sort -h | tail -30 || true

echo
echo "== Largest Recent Sessions =="
find "$HOME/.claude/projects" -name '*.jsonl' -mtime -14 -printf '%s %p\n' 2>/dev/null \
  | sort -nr \
  | head -20 || true

echo
echo "== File History Snapshot Suspects =="
find "$HOME/.claude/projects" -name '*.jsonl' -mtime -14 -print0 2>/dev/null \
  | xargs -0 -r sh -c '
    for f do
      c=$(rg -c "\"type\":\"file-history-snapshot\"" "$f" 2>/dev/null || true)
      c=${c##*:}
      [ -n "$c" ] && [ "$c" != "0" ] && printf "%s %s\n" "$c" "$f"
    done
  ' sh \
  | sort -nr \
  | head -20 || true

echo
echo "== MCP Configs =="
find "$HOME" "$HOME/projects" -maxdepth 3 \( -name '.mcp.json' -o -name 'mcp.json' \) -print 2>/dev/null \
  | sort || true
