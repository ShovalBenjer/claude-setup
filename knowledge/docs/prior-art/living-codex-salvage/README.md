# living-codex salvage

Four files rescued from `C:\Users\shova\codex-sites\living-codex-build` on 2026-07-30, before
that tree was deleted at the operator's instruction. It had **no git remote and one commit**
(`683865a Build The Living Codex`), so deletion was irreversible and nothing could be cloned
back.

The verdict that authorised the deletion: every learning capability in it is superseded by
`daily-deep-learning`, usually by an order of magnitude. Its talent trees had 3 trees with 4
hardcoded nodes each; the PWA has 42 nodes over 5 tiers with cross-tree synergies and
evidence-gated ranks. Its "spaced recall" was copy only, with no engine; the PWA runs a real
`[1,3,7,21,60]` ladder. Its research archive had three entries all labelled `DEMO ENTRY`.

Two facts about it that were believed and are wrong, recorded so nobody re-derives them:

- **State persistence never worked.** The `PUT /api/state 202` lines in `dev.stdout.log` are the
  FAILURE path, returning `{saved:false, persistence:"device"}`. No write ever reached D1.
- **`app/chatgpt-auth.ts` was not hand-built auth.** It is verbatim starter-template code, and
  the application never imported it.

## Why each of these four survived

| file | why it could not be regenerated |
|---|---|
| `.openai_hosting.json` | Holds `project_id: appgprj_6a52f49b099081918bb4674279566794`, the identifier of an OpenAI Sites hosting project. Searched `claude-setup`, `daily-deep-learning` and `oren-roast-hq`: zero other hits. If that hosted site still exists, this was the only local record able to claim it. Not a credential, but irreversible information about an external system. |
| `app_LivingCodex.tsx` | `CLAUDE-OS.md:168` cites "the Living Codex design (mastery = Recognize/Explain/Apply/Connect/Challenge; spaced recall; no guilt mechanics)" as a live architectural reference for the L8 learning-card emitter. Those five dimensions are hardcoded in this file. Deleting the tree without this would have left the spine pointing at a design with no artifact. |
| `app_globals.css` | The visual system for a direction the operator explicitly rejected on 2026-07-21 ("Its a slop merging... Even the name living codex you took as is. Disappointed from lack of reasoning"). A rejected direction is a taste-ledger input under the `docs/taste.md` discipline, and a rejection with no artifact cannot be learned from. |
| `build_sites-vite-plugin.ts` | The only genuinely hand-authored infrastructure in the tree, 45 lines, and the only record of the OpenAI Sites packaging contract: it copies `.openai/hosting.json` and `drizzle/` into `dist/.openai/` on `closeBundle`. |

## Template identity, recorded because it may not be regenerable

```
site-creator-vinext-starter 0.1.0
vinext        0.0.50        (github.com/cloudflare/vinext)
next          16.2.6
react         19.2.6
vite          8.0.13
wrangler      4.92.0
drizzle-orm   0.45.2
tailwindcss   4.2.1
```

24 of the 32 tracked files were unmodified scaffolding from that template. They are omitted
here on the assumption they are recoverable, with one stated risk: `vinext` is at `0.0.x` and
the `site-creator` scaffolder appears to be an OpenAI-side generator rather than a public CLI,
so whether this exact template version can be regenerated later is **UNKNOWN**. That is why
the version numbers are recorded above even though the code is not.

## What was deleted with it

759 MiB of `node_modules`, `dist`, `.vinext`, `.wrangler`; `living-codex-build.tar.gz` (2,939,015
bytes, verified to contain only `dist/` entries and therefore not a source backup);
`living-codex-migrations` (4 files, all byte-identical by MD5 to files inside the build tree);
`living-codex-drizzle` (empty); and `living-codex-work`, a dangling symlink into a deleted
OneDrive path.

One loose end left deliberately: `tools/hookgate/bench/fetch_audit.sh:27` still lists the
deleted path in its sweep. It handles absence gracefully, printing `NOT A REPO (or absent)`, so
it does not break; the line is simply dead now.
