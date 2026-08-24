# CS-agent production findings, 2026-07-09 (internal task list)

Source: live Chatwoot inspection (56 conversations, inboxes 35/46, 07-05 to 07-09) run
during the WhatsApp-number retirement work. The WhatsApp number itself is FIXED and live
(seekapa:127 + KB re-embed + Function App deploy, PR #530). These are the remaining,
separate bugs. Bot replies post as "Corp Super Admin"; human agents post under their names.

Note on freshness: most flagged conversations predate the 2026-07-09 ~10:08 deploy. Live
re-smoke of seekapa:127 could NOT reproduce Finding 1 (localization) for the tested cases,
so 1 is likely improved by the deploy but not yet proven closed under load. Verify before
closing.

---

## CS-A: No message debounce -> bot double-answers rapid messages  [HIGH]
Category: duplicate/looping replies. Evidence: conv 4604 (the original session conversation)
sent the "no reference number, contact support" reply TWICE, 13s apart; conv 4549 triple
greeting in 12s; 4588 "Hi, I'm Layla" twice 1s apart; 4322 two greetings 12s apart.
Root cause: the handler dedups only by `message_id` (`seen:{message_id}`, __init__.py:793),
which stops webhook retries, not two distinct rapid customer messages. No debounce, no
batching, no per-conversation in-flight lock. One reply per inbound message.
Fix: coalesce messages arriving within a short window (e.g. 3-5s) per conversation into one
agent turn, OR a per-conversation in-flight lock that defers + merges a second message until
the first reply is sent.
Acceptance: two customer messages <5s apart yield ONE bot reply; regression test with two
back-to-back synthetic webhooks asserts a single send_message.

## CS-B: English canned strings leak into AR/PT replies  [HIGH]
Category: localization leak. Evidence: conv 4602 "...I can't process phone numbers here. هل
الشكوى..."; 4603 "...I've passed this to our support team. Flagged as urgent. Someone will
reach out. حتى نتمكن..."; 4396/4351/4619 "Got it. ..." spliced into PT/AR.
Root cause: specific canned strings ("I can't process phone numbers here", "Got it, tell me
what you need") appear to be English-only in a code path (not the localized Variant/closer
tables). seekapa:127 live-smoke did NOT reproduce for the tested triggers, so the leak may
be an old-version/old-image artifact OR a narrower deterministic path.
Fix: locate every hardcoded English canned string in chatwoot_handler; give each a per-lang
version keyed on conversation language; add to the localization parity test.
Acceptance: AR/PT/ES triggers for phone-note, take-message, and urgent-escalation return
native-language replies; live_smoke.py localization cases stay green.

## CS-C: Whole reply in the wrong language  [HIGH]
Category: language misdetection. Evidence: conv 4310, English conversation throughout, bot
replied in Spanish ("Lo pasé a nuestro equipo de soporte...").
Fix: pin reply language to the conversation's started/detected language at the emit site;
do not let a single foreign token flip it.
Acceptance: an all-English thread never gets an ES/PT/AR reply; add a regression case.

## CS-D: Re-asks name+email already given in the same live conversation  [HIGH]
Category: short-horizon state. Evidence: conv 4603, customer gave name+email at 04:33:26,
bot re-asked at 04:34:39 (65s later, same conversation).
Fix: track intake-collected identity per conversation and skip the identity-ask append when
name+email already captured this session (intake_completed / CW profile).
Acceptance: after identity is supplied once, the bot never re-asks in the same conversation.

## CS-E: Cross-session context loss after idle gap  [MED, verify if by design]
Category: session continuity. Evidence: conv 4310/4320/4525/4546/4549 restart with a generic
greeting after an idle gap on an unresolved issue, forcing re-explanation.
Fix (if desired): on return within N hours to an unresolved thread, resume context instead
of a cold greeting. Confirm whether the session timeout is intended before building.

## CS-F: Phone digits dropped when echoed  [LOW]
Category: numeric fidelity. Evidence: conv 4603, `00971547018008` echoed as `009717018008`.
Fix + regression test: never reformat/echo a customer-supplied number; if quoting, quote
verbatim.

---

## Cross-cutting (not bot-code, flag to owners)
- Withdrawal SLA quoted THREE ways (bot: 3-4 + up to 14 BD, $100 min; Duraam/Hala macro:
  1-3 + 5-10 = 14 BD; another macro: 3 + up to 10 BD, EUR 50 min). Align the source of truth
  (seekapa_facts.yaml withdrawals block) across bot KB and human macros.
- Serious unauthorized-trade-closure complaint (conv 4602/4603, "Enaam", acct 5404581): bot
  triaged + flagged urgent correctly, but the human reply 4h later was a generic margin-call
  disclaimer that didn't address the "closed without authorization" allegation. Duty-of-care
  follow-up on the human side.
- Conv 4442: a human agent, asked human-or-AI, replied literally "بوت" (bot).

## Shipped this session (for context, not a task)
- WhatsApp number retired everywhere (email-only). seekapa:127, KB re-embed, PR #530 -> master.
- Regression guards added: tests/test_no_whatsapp_number.py (blocking, in Build gate) +
  evals/scripts/live_smoke.py + pipeline stage LiveSmokeNoNumberLocalization (advisory).
- FOUNDRY_AGENT_VERSION app setting corrected 119 -> seekapa:127 (telemetry accuracy).
