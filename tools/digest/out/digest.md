# Claude OS Daily Digest

- TODO: 21 done, 29 open; next: ecosystem.db bootstrap from intent-control-plane schema + tools/eco/db.py (AUTO-06) ← unblocks work-claims (AUTO-04) + FleetView (AUTO-19)
- claude-setup repo: main, dirty (11)
- Branch health: 20 merged-deletable, 2 default-branch drift

- OPEN LESSONS (3) — unenforced until closed:
  - L006: parallel sessions need structural separation (queues+charters), not intent -> ADR-0013 + docs/charters.md + work-claims (db pending AUTO-06)
  - L007: phone must reach a stateless-by-design intake, not a stateful stranger -> ADR-0013 concierge lane; RC pattern test pending (AUTO-05)
  - L008: green must mean green; cosmetic failures train alarm-blindness -> workflow cleanup step needs continue-on-error fix — open proposal

Pending operator decisions: model default, key rotation, PR repo list, WhatsApp cadence, OAuth token.