# Gitignored trees are invisible to search, not to reading

Measured 2026-07-30 in `~/Downloads/new-recruit`. Same query, same directory, same
second:

```
rg -l "sora2_smoke|repin_beats" .              ->  0 hits
rg -l --no-ignore "sora2_smoke|repin_beats" .  -> 26 hits
```

The Grep tool is ripgrep, and ripgrep honours `.gitignore` when it walks a tree.
`/projects/` and `/archive/` are ignored there (`.gitignore` lines 133 and 131), so
**17,292 files of the operator's last seven months of project work return zero hits
from any repo-root search.** 278 top-level entries are ignored, including
`PROJECTS-MANIFEST.md`, which means the index to the hidden work is itself hidden.

## Why this is a capability loss and not a permission problem

Nothing is forbidden. Read, Bash and an explicitly-named Grep path all reach these
files. What is lost is DISCOVERY: a search can only return what is already
reachable, so an ignored tree can only be found by someone who already knows it is
there. Unknown unknowns stay unknown, and a sweep reports clean while missing more
files than it examined.

The cost is already on the record. `tools/audit/pointers.py` reported
`~/projects/campaign-analysis` as an absent path five times. It is not absent: it is
1,626 files at `Downloads/new-recruit/projects/campaign-analysis`. The reference
path was wrong AND the real location was ignored, so an audit tool called a live
project missing. That is the absence-claim class (L-2026-07-29-a) mechanised into an
oracle.

## What to do

- Before claiming any sweep of a repo is complete, run
  `git status --ignored --porcelain | grep '^!!' | wc -l`. A non-trivial count means
  a plain search did not cover the repository.
- To search an ignored tree, either name its path directly in Grep, or use Bash with
  `rg --no-ignore`. Say which one you used, because the two answer different
  questions.
- `.gitignore` is the right place for these trees. Do not "fix" this by tracking
  17k files of another project's work. The fix is that the searcher knows.
- Cross-repo duplicates hide here. `intent-control-plane` exists twice, 1,037 py
  files under `claude-setup` and 616 under `new-recruit/projects`, both touched
  since 2026-07-01. Which is authoritative is an open operator question, and it was
  invisible from either repo's own search.
