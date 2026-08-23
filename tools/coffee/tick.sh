#!/bin/bash
# The coffee-v2 local tick: check the telemetry, mine yesterday's gripes, print a
# flaneur briefing. Runs from the operator's own machine via a systemd user timer,
# NOT a GitHub cron: a scheduled Action would spend the minutes the self-hosted
# runner just saved, and this only reads local ledgers. Zero cost, always-on.
#
# Install (once):
#   cp tools/coffee/coffee-tick.{service,timer} ~/.config/systemd/user/
#   systemctl --user daemon-reload && systemctl --user enable --now coffee-tick.timer
set -euo pipefail
cd "$(dirname "$0")/../.."
echo "=== coffee tick $(date -u +%FT%TZ) ==="
python tools/coffee/smoking.py scan --window-hours 24 || true
echo "--- mined gripes -> TODO candidates ---"
python tools/coffee/smoking.py mine || true
echo "--- flaneur briefing ---"
python tools/coffee/flaneur.py brief || true
