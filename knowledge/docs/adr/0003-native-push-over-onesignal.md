# ADR-0003 — Native Claude push for the personal approvals rail, not OneSignal

Status: Accepted (2026-07-22)

## Context
The approvals rail needs push to the operator's phone. Options: OneSignal SDK
(app 4b74b3a3-…, 57 MCP tools wired) vs native Claude `PushNotification` +
Notification hook. The OneSignal iOS doc assumed a native Xcode project that does
not exist; the harness is Python/Windows.

## Decision
The personal approvals rail is native `PushNotification` (→ Claude app via Remote
Control, verified 2026-07-22) plus a `Notification` hook → WinRT toast for desktop.
OneSignal is retired from the personal loop, reserved for the operator's own apps'
END USERS (learning-platform web push, Kith Expo later).

## Consequences
+ Zero SDK, zero integration, subscription-native; verified end-to-end.
+ Suppression is idle-based → headless cron pushes never suppressed (the daemon's
  approval gate always reaches the phone).
- Depends on Remote Control pairing to the right session; a pairing check is needed.
- Reaching non-operator humans (recruiters) still needs a separate outbound channel;
  OneSignal/email fills that, not the approvals rail.
