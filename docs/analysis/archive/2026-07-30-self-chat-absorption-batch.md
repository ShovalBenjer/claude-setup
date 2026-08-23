# Self-chat absorption batch, 2026-07-30

Read-only analysis of the operator's WhatsApp self-chat inbox. Nothing was sent,
posted, or published. This file is the only artifact written.

## 0. Urgent, read this first

1. **A live-looking credential sits in the chat store and in three files on disk.**
   On 2026-07-21 a two-line paste landed in the self-chat containing an account
   identifier and an API token whose prefix identifies it as a Cloudflare API
   token. A follow-up message was deleted two minutes later, but the token
   message itself was only edited, not removed, so the value is still present in:
   the live decrypted store, `C:\Users\shova\wa-export-archive\SENSITIVE-self-chat\_chat.txt`,
   and `C:\Users\shova\Downloads\WhatsApp Chat - תזכורת לעצמי.zip`. The value is
   not reproduced here. Action: rotate that token, then decide whether the three
   files get scrubbed or stay as they are with the token treated as burned.
   This predates the watermark, which is why the 2026-07-29 link run never
   surfaced it: that run extracted URLs only.
2. **No credential-shaped string appears after the watermark.** A case-insensitive
   scan of the post-watermark window for `api key`, `token`, `secret`, `sk-`,
   `ghp_`, `cfat_`, `password`, and `bearer` returned zero hits.
3. **One third-party phone contact** was noted to self on 2026-07-27. It is
   recorded in the ledger as a redacted note row, with no number and no name.
4. **A full decrypted copy of every message the operator has** now sits at
   `%LOCALAPPDATA%\Temp\wa-decrypted` (about 90 MB across six files), created by
   this run. It is outside any repo and was not committed. It stays there until
   deleted, so treat it like a vault file.
5. **This run supersedes the ABSORB-07 plan.** `TODO.md` line 60 says to run the
   external brief in Claude Desktop with the CSV attached. The live store is
   reachable and current, so the CSV path is now the fallback, not the plan.

## 1. Source, coverage, and watermark

| item | value |
|---|---|
| source used | live WhatsApp Desktop store, decrypted locally via the `whatsapp-query` skill |
| chat | the self-chat, resolved by matching a known shared URL rather than by name (console encoding mangles the Hebrew title) |
| messages in that thread | 411 |
| coverage of that thread | 2025-07-29 00:37 to 2026-07-30 00:20 |
| watermark file | `C:\Users\shova\wa-export-archive\self-chat-links-2026-07-29.csv`, 806 URL rows |
| watermark cutoff measured | last row is dated 26.7.2026 and the five links of that date are all present in it |
| new window analysed | 2026-07-26 15:50 exclusive, to 2026-07-30 00:20 |
| staleness avoided | the two export artifacts both stop at 2026-07-26 20:31, so they would have missed 17 items across four days |

How "new" was determined: the CSV's final rows are the five links of 26.7.2026
(vibeue, awesome-design-md, HyperAgents, MemRL, cognee). Those five reappear at
the head of the live thread dump and are therefore treated as already processed.
Everything the thread holds after 2026-07-26 15:50 is new.

One coverage limit, stated rather than glossed: the watermark CSV records URLs
only, so any note without a link from before 2026-07-26 has never been processed
by anything. Those are out of scope here and remain unmeasured.

Two URLs arrive truncated in the store because the message row holds a link
preview whose text is clipped. Both were resolved by search and the canonical
form is recorded, with the correction noted in the row's reason.

## 2. Ledger-ready rows

Columns match `C:\Users\shova\Downloads\new-recruit\ledger.csv` exactly. Titles
have had em dashes normalised to colons so the prose gate passes; the upstream
titles use em dashes.

```csv
date_shared,canonical,kind,title,license,gate_absorb,status,last_activity,stars,state,reason_that_survives,decided_by,n_shares,url
2026-07-27,note:university-dept-contact,note_only,Phone contact for a university department (redacted),,n/a,n/a,,,used-as-is,personal admin note; nothing crosses the tree boundary,mechanical,1,
2026-07-27,note:wa_act-send-path-test,note_only,Self-sent smoke test of his own wa_act send path,,n/a,n/a,,,used-as-is,consumed; nothing to carry into the tree,mechanical,1,
2026-07-28,attachment:silent-failures-presentation-v4.pdf,note_only,Own deck on silent failures,,n/a,local,2026-07-28,,used-as-is,operator's own artifact and not external input,mechanical,1,
2026-07-28,attachment:DoubleAI_NLPIL.pptx,note_only,Own deck for an NLP-IL talk,,n/a,local,2026-07-28,,used-as-is,operator's own artifact and not external input,mechanical,1,
2026-07-28,attachment:DevMind-Overview.pdf,note_only,Own DevMind overview document,,n/a,local,2026-07-28,,used-as-is,operator's own artifact and not external input,mechanical,1,
2026-07-29,Sdraugel/albert,github_repo,Autonomous multi-agent harness for Claude Code plus a zero-dependency live HUD console,PolyForm-Noncommercial-1.0.0,fail(PolyForm-Noncommercial-1.0.0),live,2026-07-26,85,used-as-is,licence PolyForm-Noncommercial-1.0.0 is not permissive so code cannot cross the boundary; the two mechanisms worth having are already scheduled for independent rebuild under TODO ABSORB-03,mechanical,2,https://github.com/Sdraugel/albert
2026-07-29,lmsys:dflash-spec-v2,blog_post,The next generation of speculative decoding: DFlash and Spec V2,,n/a,live,2026-06-15,,used-as-is,updates the speculative-decoding figure ADR-0009 cites (2-3x) to above 4.3x baseline throughput; a fact with no licence and nothing to install,mechanical,1,https://www.lmsys.org/blog/2026-06-15-next-generation-speculative-decoding-dflash-v2/
2026-07-29,modal:kimi-k3,blog_post,Kimi K3 by Moonshot now available on Modal,,n/a,live,2026-07-27,,rejected,solves a problem this repo does not have (no self-hosted inference path; ADR-0002 fixes routing to subscription OAuth),mechanical,1,https://modal.com/blog/kimi-k3-by-moonshot-now-available-on-modal
2026-07-29,ecc.tools/skills,product,Skills: ECC Selective Install Builder,UNKNOWN,unknown(hosted product with no repo resolved),live,UNKNOWN,,TBD,selective-install profiles over an OSS catalog address the 91-of-186 undeployed dot-claude units directly; a competitor product so the absorb-or-ignore call is the operator's,TBD,1,https://ecc.tools/skills
2026-07-29,luma:szopk5wy,other,The Future of Compute: A Live Panel,,n/a,live,2026-07-29,,used-as-is,event he attended; consumed; nothing to carry into the tree,mechanical,1,https://luma.com/szopk5wy
2026-07-29,claude-artifact:e96e48ed,other,Own briefing artifact for the compute panel,,n/a,live,2026-07-29,,used-as-is,operator's own output and already consumed at read time,mechanical,1,https://claude.ai/code/artifact/e96e48ed-942f-44e0-9e82-74b37b713170
2026-07-29,awesomeclaude.ai/claude-code-best-practices,docs_page,Claude Code Best Practices: 80+ Expert Tips plus Workflows and Concepts,CC0-1.0,pass,live,2026-06-12,1595,TBD,82 tips including a 200-line CLAUDE.md ceiling this repo's own CLAUDE.md is near; licence taken from the backing repo webfuse-com/awesome-claude and not proven to cover the page text,TBD,1,https://awesomeclaude.ai/claude-code-best-practices
2026-07-29,awesomeclaude.ai/top-mcp-servers,docs_page,Top MCP Servers ranked by GitHub stars,CC0-1.0,pass,live,2026-06-12,1595,TBD,1076-server directory; useful as a prior-art lookup surface for the prior-art-gate rather than as anything installed,TBD,1,https://awesomeclaude.ai/top-mcp-servers
2026-07-29,awesomeclaude.ai/claude-code-tips,docs_page,Claude Code Tips: 40+ tips from basics to advanced,CC0-1.0,pass,live,2026-06-12,1595,TBD,overlaps the best-practices page above; keep one of the two or neither,TBD,1,https://awesomeclaude.ai/claude-code-tips
2026-07-29,awesomeclaude.ai/claude-code-workflows,docs_page,Claude Code Dynamic Workflows: Guide plus 24 Copy-Paste Scripts,CC0-1.0,pass,live,2026-06-12,1595,TBD,shared URL was truncated in the store and resolved by search; documents the script API (agent/pipeline/parallel/phase) and the 16-concurrent and 1000-per-run ceilings that bound any fan-out this repo plans,TBD,1,https://awesomeclaude.ai/claude-code-workflows
2026-07-30,mattpocock/skills,github_repo,Skills for Real Engineers. Straight from my .agents directory.,MIT,pass,live,2026-07-29,194828,TBD,MIT so bounded snippets may be absorbed; 194.8k stars makes it the de facto skills baseline to compare dot-agents against; needs a prior-art check per skill before anything is taken,TBD,1,https://github.com/mattpocock/skills
2026-07-30,linkedin:okf-over-default-rag,blog_post,Hebrew post arguing an ontology or knowledge-fabric approach over default RAG,UNKNOWN,n/a,live,2026-07-30,,TBD,third-party author with subject only recorded; bears on whether the intent-control-plane memory layer stays vector-shaped which is an open design question not an ADR,TBD,1,
```

Two caveats on the rows above. First, `albert` is recorded as used-as-is rather
than absorbed, which reads as a downgrade against `TODO.md` ABSORB-03. It is not.
The mechanical gate forbids `absorbed` for a non-permissive licence, and ABSORB-03
already says the two mechanisms get rebuilt rather than copied. Independent
re-derivation of an idea is not absorption of that repo, so the row and the ticket
agree once the vocabulary lines up. If the operator wants ABSORB-03's eventual
outcome to read `absorbed`, the honest way is a second row keyed to the rebuilt
component, not a state change on this one.

Second, the four `awesomeclaude.ai` rows share one licence and one activity date
because they share one backing repo. Whether that CC0 covers the rendered page
prose is UNKNOWN. It does not matter for `used-as-is`; it would matter before any
text is copied.

## 3. Counts

| bucket | n |
|---|---|
| rows total | 17 |
| decidable mechanically now | 10 |
| blocked on a fetch | 0 |
| needs the operator | 7 |
| rejected | 1 |
| used-as-is | 9 |
| absorbed | 0 |
| adopted | 0 |

Every URL resolved. Zero dead links in this batch, which is itself a change from
the eight-row seed ledger where one of eight was a 404.

The base rate holds. Nothing in four days of saved links reached `adopted`, and
that is the expected outcome at roughly 70 evaluated to 1 taken, not a failure of
the batch.

## 4. What he is actually circling

Seventeen items over four days, and they are not seventeen topics. They are three,
plus one interruption.

### 4.1 The dominant thread: other people's harnesses, and a distribution problem he has not named

Nine of the seventeen are somebody else's Claude Code harness or a catalog of one:
albert (reshared, second sighting), ecc.tools' selective install builder,
mattpocock's skills repo at 194.8k stars, and four pages of an aggregator site.
Add the 2026-07-24 sightings of `amirfish1/claude-command-center` and
`Master0fFate/just-my-skills` that the previous run already logged, and the shape
is clear: he is benchmarking his tree against the field roughly daily.

The thing worth saying is that he is looking at these for the wrong axis. Every
one of the nine is strong at the axis his repo is weakest on, which is
**distribution and selective activation**, and weak at the axis his repo already
leads, which is verification. `ecc.tools/skills` exists to let you install a
subset of a catalog into a specific repo without dragging the whole stack. That is
a direct answer to the open ticket in `TODO.md` reading
"91/186 dot-claude units deployed (48.9%); 14 hook bodies still 44-61 byte
pointers; dot-agents has no deploy target". His migration-activation backlog is
not a migration problem, it is a missing selective-install layer, and two products
in this batch are built around exactly that.

Decision the batch implies: `dot-claude` and `dot-agents` need install profiles,
not more deploy scripts. That is a lane B design decision that should run
`/diverge` with `ecc.tools` and `mattpocock/skills` as the two named anchors, and
`docs/CODEBASE-MAP.md` plus `docs/dir-purpose.txt` as the repo model per the
whole-repo stack rule. Cost estimate: this is a profile manifest plus a resolver
over the existing tree, not a new subsystem, so the risk is that it becomes one.

`mattpocock/skills` at MIT is the only item in the batch where a licence gate PASS
plus real capability overlap plus scale would ordinarily justify `adopted`. It is
still TBD rather than adopted because the prior-art check per skill has not run,
and skipping that is precisely the failure ABSORB-01 documents.

### 4.2 The second thread: agent memory, and a contradiction he should see

The 2026-07-26 links the previous run captured (cognee, MemRL, HyperAgents) plus
the 2026-07-30 post arguing against default RAG are one continuous line of
thought about persistent agent memory. That line runs straight into a measured
fact this repo already recorded and has not acted on.

`TODO.md` ABSORB-08 reports that of 70 vulture findings at 60% confidence, 57 sit
in `intent-control-plane/src/intent_control_plane/`, with `memory.py` the joint
top file at 6 unused symbols. So the memory layer he is reading research about is,
in his own tree, the single most measurably unconnected component he owns. He is
sourcing external memory architectures while his own is dead code.

That is the sharpest thing in the batch and it does not need new dependencies to
act on. The 2026-07-30 post's argument, that throwing PDFs at a vector store and
hoping was the reflex answer for three years, lands on ADR-0011 (one operational
state DB) and on the unbuilt `ecosystem.db` bootstrap (AUTO-06). AUTO-06 is
blocking work-claims (AUTO-04) and FleetView (AUTO-19), so it is already the
highest-leverage unstarted ticket, and this batch supplies the reason to shape its
schema deliberately rather than reaching for embeddings by default.

Does anything here supersede a decision? No ADR is contradicted. But it is a
genuinely new direction in one respect: none of ADR-0010, ADR-0011, or ADR-0017
takes a position on whether recall is retrieval-shaped or graph-shaped, and four
saved resources in five days all argue that the choice matters. That gap deserves
an ADR rather than a default.

### 4.3 The third thread: inference serving, which is not his problem

Two items, the LMSYS DFlash post and the Modal Kimi K3 post, are about serving
throughput. ADR-0002 fixes this estate to subscription OAuth and forbids
gateways, and there is no self-hosted serving anywhere in the tree. The Kimi row
is rejected on exactly that ground.

The DFlash post is not rejected, because it carries one fact that touches a
committed document. `docs/adr/0009-slm-swarm-asymmetric-leaf-executors.md` line 18
cites speculative decoding at "2-3x, identical output" as one of two robust
asymmetric wins. The current published figure is above 4.3x baseline throughput,
and DFlash is now the default in SGLang's Spec V2 engine. ADR-0009's conclusion
gets stronger, not weaker, so this is a citation refresh rather than a
supersession. Worth a one-line update to that ADR with the dated source, which is
the kind of decay the repo has no check for.

### 4.4 The interruption, and what it says about the pipeline

Five of the seventeen are not resources at all: a phone contact, a one-line smoke
test of his own send path, and three of his own documents pushed into the chat as
a transfer channel. They are correctly classified `note_only` and they cost
nothing, but they are 29% of the batch, and they are the reason a link-only
extractor cannot be the pipeline. The 2026-07-29 CSV run saw none of these five,
and it also saw none of the credential paste, for the same reason.

The `wa_act send path test` message on 2026-07-27 is worth one further note: it
means he was testing an outbound WhatsApp path two days ago. Nothing in this
run sent anything, and this analysis stayed read-only, but an outbound path
pointed at a chat that contains a credential and a decrypted local mirror is a
combination that deserves an explicit boundary before it is used.

### 4.5 What the batch does not do

It does not close any ticket. It does not obsolete any ticket. It adds evidence to
three that already exist (the activation backlog, AUTO-06, ABSORB-08) and it
supplies one small correction to ADR-0009's citation. Anyone reading this hoping
the saved-link pile contained a shortcut should note the honest result: four days
of high-quality saved links produced zero adoptions and one rejection, and the
value was entirely in what the pattern revealed about work already on the board.

## 5. Method, so this is repeatable

1. Read the watermark CSV tail, establish the cutoff date and its final rows.
2. Decrypt the live store with the `whatsapp-query` skill. Confirm freshness by
   comparing the thread's last timestamp against both export artifacts.
3. Resolve the self-chat by matching a known post-watermark URL, not by name,
   because the console mangles the Hebrew title.
4. Dump the thread from the cutoff, extract URLs, scan the same window for
   credential shapes before reading anything else.
5. Resolve each URL through the GitHub API for repos and a direct fetch for
   pages. Take the licence from `/license` rather than the repo summary when the
   summary says NOASSERTION, since that hides real terms.
6. Apply the licence gate mechanically, then judge.

The step that mattered most was step 4, and it was the step the previous run
skipped.
