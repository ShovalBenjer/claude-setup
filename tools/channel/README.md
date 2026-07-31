# tools/channel

Purpose: measure whether a compressed inter-agent channel actually carried the
content, rather than whether the receiver produced a plausible reply.

`roundtrip.py` is the oracle required by ADR-0018 before any `dense-text` or
`kv` channel is allowed on the dispatch bus. It sends a document over a channel,
asks probes whose answers exist only in that document, and normalises the
channel's probe accuracy against the same probes over plain text. Substring
recovery, not model judgement, so the verdict is deterministic and is not graded
by the same class of system that might be hallucinating over the channel.

```bash
python tools/channel/roundtrip.py selftest              # identity passes, truncation fails
python tools/channel/roundtrip.py run --channel identity
python tools/channel/roundtrip.py run --channel truncate --floor 0.9   # expected FAIL
python tools/channel/roundtrip.py run --channel command \
    --compress "<peer that densifies stdin>" --read "<peer that restores stdin>"
```

The `truncate` channel is not a toy left in by accident. It is the regression
that keeps this gate falsifiable: if truncating half a document ever reports
PASS, the oracle is broken and ADR-0018's falsifier has fired.

Fidelity is a property of a compressor-reader pair, not of a channel name.
arXiv 2606.19857 measured retention varying strongly by pair, with compression
strength between roughly 75% and 95% across frontier models, so a floor that
passes on one pair carries no claim about another. Record the pair with the
verdict.
