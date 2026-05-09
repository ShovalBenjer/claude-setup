---
name: meme-control
description: Toggle Codex meme playback on/off and report current meme state (session + durable config).
---

# /meme-control

Use this skill when the user wants to:
- stop memes immediately
- re-enable memes
- check current meme status

## Usage

```text
/meme-control off
/meme-control on
/meme-control status
```

## Behavior

Determine intent from the user message (`off`, `on`, or `status`) and run the matching commands.

### OFF (immediate stop)

```bash
touch /tmp/.Codex-meme-disabled
rm -f /tmp/.Codex-meme-enabled
pkill -f ffplay 2>/dev/null || true
echo "Memes OFF"
```

### ON (re-enable)

```bash
rm -f /tmp/.Codex-meme-disabled
touch /tmp/.Codex-meme-enabled
echo "Memes ON"
```

### STATUS (show effective state)

```bash
python3 - <<'PY'
import json
from pathlib import Path

cfg = Path("/home/shovalbe/.Codex/config/memes.json")
durable = None
if cfg.exists():
    try:
        durable = bool(json.loads(cfg.read_text()).get("enabled", False))
    except Exception:
        durable = None

disabled_flag = Path("/tmp/.Codex-meme-disabled").exists()
enabled_flag = Path("/tmp/.Codex-meme-enabled").exists()

effective = (durable is True) and not disabled_flag
print(f"durable_enabled={durable}")
print(f"session_enabled_flag={enabled_flag}")
print(f"session_disabled_flag={disabled_flag}")
print(f"effective_enabled={effective}")
PY
```

## Rules

- For `off`, always stop active playback (`pkill -f ffplay`) so the effect is immediate.
- Prefer session flags (`/tmp/.Codex-meme-disabled`, `/tmp/.Codex-meme-enabled`) for quick toggles.
- Do not edit `~/.Codex/config/memes.json` unless the user explicitly asks for a durable default change.
