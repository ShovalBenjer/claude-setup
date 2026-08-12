# Every boundary needs a typed contract (no raw passthrough)

Global rule. Applies to every project and session. A coding-practice gate that
runs as part of the standing flow: check it while writing boundary code and again
before review or ship. Companion to the Forge Loop (RED/GREEN/COVERAGE/REFACTOR),
the `ponytail` skill, and `testing-pyramid`. Encodes the review standard Vlad
applied to the qc-telephony-api QC-insights proxy.

## What a boundary is

Any seam where data enters or leaves a process: an inbound request, an outbound
call to an upstream service, a (de)serialization step, a payload read off the wire
or off disk. Middle layers (proxies, gateways, adapters, BFFs) are boundaries too,
and they are the ones most likely to skip the contract because "they just forward."
That skip is the defect this rule exists to stop.

## Trigger

Whenever you write or review code that sits between two systems: a proxy, gateway,
adapter, BFF, or an API handler that calls an upstream, and any (de)serialization
at an IO edge. Force the check hardest when the systems on either side already have
contracts (typed frontend, typed backend) and the connecting layer does not: that
connecting layer is where the contract silently goes missing.

## The rule (the checklist to pass)

1. Typed DTOs, no raw passthrough. Decode every inbound and every upstream payload
   into an explicit typed structure. Never read raw bytes and forward them as the
   response. The response you return is built from a typed view, not from the
   upstream's bytes.
2. A contract in both directions. The request you accept and the view you return
   each get a named type. A typed request with an untyped response is half a
   contract, which is not a contract.
3. Never ignore a serialization or IO error. Every marshal, unmarshal, decode, and
   read-body call checks and handles its error. In Go, no `x, _ := json.Marshal(...)`
   and no discarded error from `io.ReadAll`. In Python, no bare `except: pass`
   around parsing. In TypeScript, no unchecked `JSON.parse` or unawaited decode. A
   swallowed serialization error is a silent data-corruption path.
4. Validate the upstream, fail closed. Do not forward an upstream status and body
   unvalidated. If the upstream returns unparseable or contract-violating JSON,
   return 502 (bad gateway), not the garbage. The boundary owns the contract; a
   broken upstream does not get to leak downstream.
5. Extract the client. Upstream call flow (build request, send, read, decode, map
   errors) lives in a named, testable helper (for example a `QCClient` with a
   `GetInsights` method), not inline in the request handler. The handler stays
   thin: parse input, call the client, shape the output.
6. Typed error DTOs. Errors crossing the boundary use a typed error shape, not an
   ad-hoc generic map (`fiber.Map`, a bare `dict`, `any`). The caller relies on the
   error contract as much as the success contract.
7. Boundary tests are mandatory. Five canonical cases at minimum: valid response,
   invalid or malformed upstream payload, missing config, missing resource (the
   requested entity does not exist), and timeout. No test file for a boundary means
   the boundary is unverified, and unverified is not done.
8. Ponytail last, not first. Once the contract holds and the five tests pass, run
   the minimalism pass (`/ponytail` or `/simplify`) to cut anything that does not
   earn its place. Correctness contract first, minimize second. "Keep it minimal"
   is never a reason to skip the contract: ponytail removes bloat, it does not
   remove boundaries.

## Where it bites

The untyped middle layer is the usual defect. When the frontend is typed and the
backend is typed, the connecting proxy is exactly the seam where the contract goes
missing, because it "only forwards." Audit the seams between two already-typed
systems first; that is where the gap hides.

## Why this exists

2026-07-01, qc-telephony-api. The QC-insights proxy sketch at
`docs/integration/qc-dashboard-dropin/qc_insights_proxy.go` was a raw passthrough
that failed all eight points at once: it read the upstream body with a discarded
error and sent the bytes straight back (`out, _ := io.ReadAll` then `c.Send(out)`),
marshaled its request payload with a discarded error (`payload, _ := json.Marshal`),
kept the whole client flow inline in the handler, returned `fiber.Map` for every
error, forwarded the upstream status and body without validating the JSON, and
shipped with no `_test.go` and no minimalism pass. The backend (Python Functions
blueprints, `/v1/insights/*` in `blueprints/scoring.py`) and the frontend (typed
`InsightsView` in `call-analyzer-frontend/lib/qc/types.ts`) both had contracts. The
Go middle layer was the only place without one. Vlad's review named each gap. This
rule turns that review standard into a check that runs before review has to.

## Enforcement checklist (before writing, and before shipping)

- [ ] Inbound request decoded into a named type.
- [ ] Response built from a named view type, not forwarded raw bytes.
- [ ] Every marshal, unmarshal, decode, and read error checked and handled (no
      discarded errors).
- [ ] Upstream response validated; bad upstream JSON returns 502, not a passthrough.
- [ ] Upstream call flow extracted into a named, testable client.
- [ ] Errors returned as typed DTOs, not generic maps.
- [ ] Tests exist for valid, invalid-upstream, missing-config, missing-resource,
      and timeout.
- [ ] Ponytail or simplify pass run after the contract and tests are green.
