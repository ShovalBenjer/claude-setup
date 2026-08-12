---
PRD: prd/claude-os.md
Ticket: SETUP-OS
Status: active, needs an operator action that no commit can perform
---

# A secret reached a pushed commit, and removing it from HEAD does not remove it

Written 2026-08-10, immediately after the gate caught it. Lead with what is still true
rather than what was fixed: **the value is in git history on a branch that is on GitHub,
and it stays there until someone rotates it or rewrites that history.**

## What happened

`docs/inbox-from-new-recruit/` is an untracked drop of another repository's `.claude`
tree and docs, 74 files, placed here for reading. It was not created by the session that
committed it. A `git add -A` in commit `e695af5` swept the whole tree into the index
along with the intended change, 83 files and 15647 insertions where the real diff was one
Rust file, and the push went out before the gate ran.

`docs/inbox-from-new-recruit/.claude/bin/elevenlabs-mcp-launcher.sh:9` assigns a secret
to a shell variable. The value is not reproduced here, in the commit message, or in any
report.

## What has been done, and what it does not achieve

The tree is untracked (`git rm -r --cached`, files still on disk) and added to
`.gitignore`. That removes it from HEAD and from every future commit.

It does **not** remove it from `e695af5`, which is pushed. `git log -p` on that commit
still shows the value, on GitHub, to anyone with access to the repository. A later commit
that deletes a file is not a redaction.

## The operator action, which the assistant cannot take

Two options and they are not equivalent.

1. **Rotate the ElevenLabs key.** Treat the value as burned, issue a new one, update
   whatever consumes it. This is the option that works regardless of what any git command
   does afterwards, and it is the recommended one: the repository is private, but a
   pushed secret in a private repository is still a secret that left the machine.
2. **Rewrite the branch history** to drop the blob, then force-push. This needs
   `--force-with-lease` and it is blocked for the assistant by design (`hookgate` denies
   bare force-push, and rewriting shared history is the operator's decision). It also
   does not help if anything has already fetched the branch, and GitHub may retain the
   unreferenced object.

Doing 1 is sufficient. Doing 2 without 1 is not.

## Why the gate caught it and the push did not

The `security` domain scans tracked files and it found this on the first run after the
commit. The push happened first because the working order that session was commit, push,
then gate, and the gate is the slowest step. That ordering is the actual defect and it is
cheap to fix: gate before push, not after. The pre-push hook inspects push shape and
repository binding, not file contents, so it was never going to catch this.

## The narrower lesson

`git add -A` in a repository that receives untracked drops is not a safe default. This
session used it eleven times, correctly ten of them, and the eleventh cost a secret. The
existing rule about regenerating maps prescribes `git add -A`, so the fix is not "stop
using it" but "read what it staged before committing": `git diff --cached --stat` was
available and would have shown 83 files where 3 were expected.
