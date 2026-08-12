# agent-feed timer

Status: live, 2026-08-04. The units below are deployed and the timer is enabled;
`systemctl --user list-timers agent-feed.timer` is the check.

The deployed copy of the two units that keep GitHub issue #38 fed. These files are
payload, not live config: editing them here changes nothing until they are copied
to `~/.config/systemd/user/` and reloaded. That is the same trap `dot-claude/`
carries and it is worth stating twice.

```bash
cp tools/telemetry/systemd/agent-feed.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now agent-feed.timer
systemctl --user list-timers agent-feed.timer   # NEXT must show a time, not a dash
```

## Why a systemd user timer and not a hook

A `Stop` hook would fire on every turn, and three already run there. A
`SessionStart` hook would fire only when a session begins, which is exactly when
nobody is reading. The timer is independent of session activity, which is the
point: the feed exists so that an agent that is NOT running still gets told what
happened.

It also avoids editing `~/.claude/settings.json`. `tools/refute/checks/config_drift.py`
watches that file against a recorded baseline, so a hook added here would have to
be accompanied by a baseline update or it reads as a silent cross-session rewrite.

## Why the throttle is set twice

`OnUnitActiveSec=30min` governs how often the unit FIRES. `--throttle 30` governs
how often it may POST. They are not redundant: `Persistent=true` makes systemd
catch up a missed window after the machine was asleep, and a manual
`systemctl --user start agent-feed.service` bypasses the timer entirely. The
throttle is what makes both of those safe.

WSL caveat: systemd only runs while a WSL session is up. The timer is not a cron
on a server and will not fire on a laptop with WSL shut down. `Persistent=true`
means one catch-up run when it comes back, not one per missed window.
