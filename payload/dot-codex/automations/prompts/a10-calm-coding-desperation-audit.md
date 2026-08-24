# A10. Calm-Coding Desperation Audit

Schedule: Weekdays 8:00 PM
Repo root: all active project repos
Mode: read + ADO comment on PR if found

For commits made in the last 24 hours across all active feature branches, grep the diff for desperation artifacts:

- `except: pass` or `except Exception: pass`.
- Deferred-marker comments; look for the literal marker strings for TODO, FIXME, and XXX without adding new marker comments yourself.
- Added `any` type in TypeScript, not removals.
- Added `console.log` or `print` statements.
- Magic numbers added without comment.
- Copy-pasted blocks longer than 10 contiguous lines, hash-detected.
- `--no-verify` in commit messages or hook bypass mentions.
- Silent error swallowing, such as `catch (e) {}` or `except: continue`.

For each finding:

- File path, line, pattern.
- Commit SHA, author, and message.
- Severity: `HIGH` if `--no-verify` or pass-on-exception; `MEDIUM` otherwise.

Output `~/.claude/docs/DESPERATION_AUDIT_<DATE>.md`.

For `HIGH` findings: comment on the source PR via `work-item.sh` if the PR has an ADO work item linked. Do not auto-revert.
