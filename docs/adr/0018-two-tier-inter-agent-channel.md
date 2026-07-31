# ADR-0018: inter-agent messages get two channels, and the dense one carries an oracle

Date: 2026-07-30
Status: accepted
Lane: B (harness)

## Context

A cross-vendor dispatch bus is being built in this repo (Kilo Cloud inbound
trigger, plus Codex, Gemini, NVIDIA and Qwen alongside Claude). Every leg of it
currently carries natural-language text, because that is the only thing an API
peer accepts.

The 2026 literature says that text is the wrong default when the reader is
another model, and it splits cleanly into two mechanisms that are easy to
conflate. Conflating them is the reason this ADR exists.

**Dense text, black box.** `Large Language Models Do Not Always Need Readable
Language`, arXiv 2606.19857, 2026-06-18, Shanghai Jiao Tong University
(corresponding), University of Sydney, Hefei University of Technology, Xi'an
Jiaotong, Nanjing. A compressor model emits a deliberately unreadable string;
a reader model recovers the semantics. Measured: Dale-Chall 16.70 against 10.28
for the source, 80.19% difficult words against 35.97%, perplexity 176.60 on
Llama-3-8B against 9.63. Human question accuracy fell from 56.10% to 35.80%
while Gemini 3.1 Pro rose from 90.00% to 96.70%. Inter-agent token reduction
38.96% homogeneous and 44.21% heterogeneous, at 96.6% to 99.7% of the
uncompressed task score. It needs no weights, no training, and no hidden states,
so it works over any API.

**KV cache, white box.** The line opens with Cache-to-Cache, arXiv 2510.03215,
Shanghai AI Laboratory, SJTU, Tsinghua, CUHK, Infinigence-AI, and continues in
2026 with `Latent Space Communication via K-V Cache Alignment` (2601.06123),
`See What I See` (2606.13594, first across heterogeneous models) and
`Latent Cache Flow` (2605.22863). `Learning to Communicate` (2604.21794,
University of Illinois Urbana-Champaign) goes further and trains the channel
itself: Qwen3-8B on AIME24 from 50.0% to 76.7%, GPQA-Diamond from 39.9% to
60.1%, with the learned protocol saturating at about 10 latent steps and getting
worse at 40 and beyond. All of it requires both sides' caches, hence open
weights and a projector.

Two facts constrain any design here. The first is that no API peer can ever do
the second mechanism. The second is that nobody has shipped a way to check
either one: `Do Latent Channels Actually Communicate?` (2607.26773, 2026-07-29)
states that representational capacity does not establish that a channel carries
information, and `LCGuard` (2605.22786) with `When Latent Agents Lie`
(2606.28958) show the channel is both unauditable and attackable, including an
agent that sends a benign visible message while passing its full state
underneath.

## Decision

1. A dispatch envelope declares `channel` as one of `text`, `dense-text`, or
   `kv`. There is no implicit default and no silent downgrade. A `kv` dispatch
   to a peer that has not declared the capability is an error, not a fallback,
   because a silent fallback to text is exactly the failure that reads as
   success.

2. Peer capability is declared per peer and checked before send. API-only peers
   (Claude, Codex, Gemini) may declare `text` and `dense-text` and may never
   declare `kv`.

3. `kv` is permitted only on legs where both endpoints are open-weight and under
   our control. Today that is Qwen through NVIDIA NIM or a local checkpoint. It
   is one measured leg, never the bus default.

4. **No dense channel ships without passing the round-trip oracle.**
   `tools/channel/roundtrip.py` sends a document over the channel, asks the
   receiver probe questions answerable only from that document, and scores
   fidelity against the same probes over the plain-text channel. A channel below
   its declared floor fails. This is the condition on 1 through 3, not a
   follow-up task.

5. `dot-claude/agents/latent-systems-lab.md` already scopes its prohibition
   correctly ("between closed models"), so nothing is being relaxed. What it
   lacked was the positive case: open-weight legs are permitted, and are
   governed by 3 and 4 rather than by silence. The agent file gains that
   pointer. Note that `dot-claude/` is committed payload, not live config, so
   this changes no running session until deployed, and
   `python tools/audit/skills_sync.py check` is what measures the drift.

## Consequences

- The bus gains a message type whose payload is unreadable to a human reviewer.
  `state/bus.jsonl` is hash-chained, so the encoding of a dense payload is a
  chain-integrity decision and has to be settled before the first dense row is
  appended. The prose gate must exempt dense payloads by envelope field, never
  by heuristic, or `tools/slop_lint.py` becomes the thing that blocks a correct
  message.
- Fidelity is measured per compressor-reader pair, not per channel. 2606.19857
  found retention depends strongly on the pair, and that compression strength
  varies from over 95% (Gemini 3.1 Pro) to about 75% (GPT-5.4). A floor that
  passes on one pair says nothing about another.
- Token savings on the order of 40% are worth having, and they are also the
  reason to be suspicious: the cheapest way to make the oracle quiet is to weaken
  the probes. The probe set is an oracle and falls under the do-not-weaken rule.
- This ADR does not authorise a live cross-vendor call. Rows 1 through 3 are
  design; row 4 is what exists on disk today.

## Falsifier

If the round-trip oracle reports fidelity at or above the floor for a channel
that is in fact dropping content, this ADR is wrong about being able to gate the
thing at all. The regression for that case is the lossy channel in
`roundtrip.py selftest`, which must stay red.
