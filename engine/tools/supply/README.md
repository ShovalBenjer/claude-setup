# tools/supply

Provenance ledger for third-party artifacts, so this repo can adopt outside tools
on recorded evidence instead of refusing whatever it cannot verify.

`verify.py` fetches or hashes an artifact, records source, sha256, size,
signature status and scanner verdict to the append-only hash-chained
`state/supply-chain.jsonl`, and refuses to mark anything adopted without a
recorded hash of the installed bytes. Signature checking uses `gh attestation
verify` or `cosign verify-blob`, whichever is installed; scanning drives
osv-scanner, trivy, grype, cargo-audit or pip-audit if present, and records
`unavailable` rather than clean when none is.

`fetch-script` is the substitute for `curl ... | sh`: it downloads the installer
to disk, hashes it, records it, and refuses to execute it. The reasoning, the
alternatives that were rejected, and the proposed `supply_chain` gate domain are
in `docs/adr/0019-supply-chain-verification.md`.

```
python tools/supply/verify.py selftest
python tools/supply/verify.py verify-ledger
python tools/supply/verify.py status
```
