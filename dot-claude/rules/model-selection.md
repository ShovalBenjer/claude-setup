# Claude model selection

Use model choice as a risk and verification decision, not a quality claim.
Model internals are not public; behavior on this repository is the relevant
evidence.

- `opus` is the lead default on this machine. A July 25 probe resolved it to
  `claude-opus-5`.
- Use `claude-sonnet-5` for bounded implementation and parallel workers.
- Use Haiku only for low-risk inventory or transformation with a cheap oracle.
- `fable` is exceptional-only; it existed in the local CLI but the July 25
  probe was quota-blocked.
- Keep first-party Claude.ai OAuth routing. Do not introduce gateways or free
  proxies unless the user explicitly requests a controlled experiment.
- Adaptive thinking stays enabled. The 1M context capability is available, but
  select it only when measured retrieval and deliberate compaction are inadequate.
- Do not copy the whole transcript to a worker. Send goal, constraints, relevant
  files, required evidence, write scope, and stop condition.
- Escalate by task risk: a stronger model does not replace tests, independent
  review, benchmarks, or external-state verification.

For a non-trivial implementation, use `/prove-implementation`. For domain
knowledge, retrieve a narrow pack with `/learn-on-demand`.
