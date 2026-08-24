#!/usr/bin/env python3
"""Reversible PII tokenization for text bound for a hosted free tier.

Reanimation stage 2 masks each corpus chunk with this BEFORE router.chat() (the
pii-handling rule: no raw PII crosses a model boundary, and a free tier may train
on inputs). Masking is reversible tokenization, not redaction: a value becomes a
stable <TYPE_n> token and the token->value map stays local, so a persona card can
be rehydrated by a non-model builder later.

Phone/email/URL/long-digit-id are regex-caught. Names are the hard case and are
NOT solved here: Hebrew first names have no cheap detector, so this masks the
structured identifiers and leaves free-text names, which is why the corpus never
leaves ~/.intent and only tokenized CHUNKS (not the whole store) reach a lane.
Stated plainly rather than claimed complete.
"""
import re

_PATTERNS = [
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("URL", re.compile(r"https?://\S+")),
    ("PHONE", re.compile(r"(?<!\d)(?:\+?972[-\s]?|0)5\d(?:[-\s]?\d){7}(?!\d)")),
    ("ID", re.compile(r"(?<!\d)\d{9}(?!\d)")),
]


class Vault:
    """Holds the token->value map for one masking session."""

    def __init__(self) -> None:
        self.fwd: dict[str, str] = {}   # value -> token
        self.rev: dict[str, str] = {}   # token -> value
        self._n = 0

    def _token(self, kind: str, value: str) -> str:
        if value in self.fwd:
            return self.fwd[value]
        self._n += 1
        tok = f"<{kind}_{self._n}>"
        self.fwd[value] = tok
        self.rev[tok] = value
        return tok

    def mask(self, text: str) -> str:
        for kind, pat in _PATTERNS:
            text = pat.sub(lambda m: self._token(kind, m.group(0)), text)
        return text

    def unmask(self, text: str) -> str:
        for tok, val in self.rev.items():
            text = text.replace(tok, val)
        return text


if __name__ == "__main__":
    v = Vault()
    sample = "call me 052-1234567 or shov@x.com id 123456789 see https://a.b/c"
    masked = v.mask(sample)
    print("masked:", masked)
    assert v.unmask(masked) == sample, "roundtrip broke"
    print("roundtrip ok,", len(v.rev), "tokens")
