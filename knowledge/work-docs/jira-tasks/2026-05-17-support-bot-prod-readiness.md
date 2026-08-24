# Initiative: Support Bot Prod-Readiness + Support Comms Unification

**Date drafted:** 2026-05-17
**Owner:** Shoval
**Context (1-2 sentences):** Seekapa support bot is moving from QA into production on Telegram. Yasha (Support owner) needs to sign off on approved-topic scope + live-CRM RO reliability, and we need a TEST CRM account so Korin's QA OTP flow stops being able to reach real customers. Parallel track: unify Support off Voicepin (TG/WA) + LiveAgent (email) onto the in-house IM/Chatwoot stack already replacing Voicepin in HL.

> **EPIC (create first in Jira, then attach every TASK below to it):**
> **Summary:** Support bot prod-readiness + Support comms unification
> **Description:** Productionize the seekapa Telegram support bot with Yasha as owner-reviewer (topic scope + live-CRM RO reliability), add a CRM TEST account so QA can't accidentally OTP real customers, and scope migration of Support's Voicepin + LiveAgent traffic onto our in-house IM/Chatwoot stack.

---

## TASK 1: Yasha owner-review — approved-topic scope for support bot

- **Type:** Task
- **Priority:** P1
- **Components / labels:** Support, AI, cs-agent, owner-review
- **Estimate:** M
- **Depends on:** none

**Description:**
Yasha is the Support area owner and needs to define what the bot is allowed to talk about and what is out of scope before we open it to real clients. Today the bot answers freely across account info, verification, balance, deposits, withdrawals, etc. We need an explicit allowlist/denylist so the bot doesn't ship content Support doesn't want clients to receive.

**Acceptance criteria:**
- Written list of approved topics (what bot MAY answer) signed off by Yasha
- Written list of out-of-scope topics (what bot MUST escalate or refuse) signed off by Yasha
- Allowlist committed under `docs/specs/` in cs-agent repo and linked from this ticket
- Bot's escalation rules updated to match the denylist (no overlap with response phrases — see CLAUDE.md circular-escalation rule)

### Subtasks

- [ ] **SUB 1.1:** Send Yasha current de-facto topic list (extracted from KB v2 + prompt)
      Description: Dump the topics the bot currently answers on. Send as a checklist for Yasha to mark approve/deny/edit.
      Estimate: S
- [ ] **SUB 1.2:** Capture Yasha's edits into `docs/specs/support-bot-topic-scope.md`
      Description: Approved / denied / escalate-only sections. One source of truth.
      Estimate: S
- [ ] **SUB 1.3:** Update escalation keyword list + bot response templates to match denylist
      Description: Grep-check both sides for overlap before merge (CLAUDE.md anti-pattern).
      Estimate: M

---

## TASK 2: Yasha owner-review — live-CRM RO reliability sign-off

- **Type:** Task
- **Priority:** P1
- **Components / labels:** Support, CRM, cs-agent, owner-review
- **Estimate:** M
- **Depends on:** none

**Description:**
Bot is now wired to live CRM in read-only mode and answers account-info questions (balance, verification status, account details). Before exposing this to real clients on Telegram, Yasha needs to validate that the answers the bot gives are actually correct against CRM ground truth across a spread of real account states.

**Acceptance criteria:**
- Test plan covers: verified / unverified / partially verified / blocked / closed accounts; positive / zero / negative balance; multiple currencies
- Yasha reviews a sample (≥20 real-data probes) and confirms answers match CRM
- Any miss is filed as a separate bug ticket and blocked-by'd to this task
- Yasha's sign-off recorded in the ticket comments

### Subtasks

- [ ] **SUB 2.1:** Build 20-row probe set covering account-state matrix
      Description: Use `qa_probe.py` / `chat_seekapa.py`. PII handled per memory rule — no CRM lookups for real customer data, fixtures only.
      Estimate: M
- [ ] **SUB 2.2:** Run probes against seekapa:117, capture answers + CRM ground truth side-by-side
      Description: Output a single markdown table Yasha can review in one pass.
      Estimate: S
- [ ] **SUB 2.3:** Walk through results with Yasha, file misses as bugs
      Description: One bug per failure mode, blocked-by this task.
      Estimate: S

---

## TASK 3: Create CRM TEST account for QA OTP flow

- **Type:** Task
- **Priority:** P0
- **Components / labels:** CRM, QA, Infra, Support
- **Estimate:** S
- **Depends on:** none

**Description:**
Yasha flagged: if we flip OTP from "send to Yasha (safety gate)" to "send to customer", and Korin runs QA, the bot will OTP and contact real customers about a QA test. Yasha asked: *"אתה בטוח? לא עדיף איזשהו חשבון TEST שיהיה ב-CRM?"* — yes, that's the right answer. We need a dedicated TEST account (or small set) inside PandaTS CRM with a Support-controlled email/phone so QA can exercise the full OTP→details flow end-to-end without ever reaching a real client.

**Acceptance criteria:**
- ≥1 TEST account exists in PandaTS CRM marked as non-production (label/flag/segment — whatever CRM supports)
- TEST account email + phone route to a mailbox/number Support owns (not a real client)
- TEST account covers each major state QA needs to exercise (verified, balance > 0, KYC complete)
- Account credentials documented in 1Password/KV (NOT in this ticket)
- Bot does not treat TEST account differently in logic — only the routing endpoint differs

### Subtasks

- [ ] **SUB 3.1:** Confirm with Yasha which CRM fields/flags mark an account as TEST
      Description: Whatever PandaTS supports — segment, tag, custom field.
      Estimate: S
- [ ] **SUB 3.2:** Provision TEST mailbox + phone for OTP delivery
      Description: Support-owned, not Shoval's personal, not Yasha's. Document recipient in KV.
      Estimate: S
- [ ] **SUB 3.3:** Create the TEST account(s) in CRM with the right state matrix
      Description: At minimum: verified + funded. Extend if QA needs more.
      Estimate: S
- [ ] **SUB 3.4:** Document TEST account list in `docs/specs/qa-test-accounts.md` (creds in KV only)
      Description: So future QA hires don't re-invent the wheel.
      Estimate: S

---

## TASK 4: OTP recipient toggle — QA mode (→ Yasha) vs Prod mode (→ customer)

- **Type:** Task
- **Priority:** P1
- **Components / labels:** Backend, AI, cs-agent, Support
- **Estimate:** M
- **Depends on:** TASK 3

**Description:**
Today the bot sends the OTP approval email to Yasha as a safety gate during QA. For prod we need it to send to the customer. Yasha confirmed he wants to keep the current QA-mode-to-him behavior until prod cutover. Need an explicit, gated toggle — not a code branch we have to remember to flip — so QA can keep running without risk of OTPing real customers, and prod cutover is a single config switch.

**Acceptance criteria:**
- Env var or KV config controls OTP recipient: `OTP_RECIPIENT_MODE=qa|prod`
- In `qa` mode: OTP always emails Yasha (or configured QA recipient), never the customer
- In `prod` mode: OTP emails the customer's CRM-on-file email
- Mode is logged on every OTP send (one log line, no PII — `xx***@domain` rule)
- Default in code = `qa` (fail-safe — never accidentally hit a customer)
- Cutover to `prod` requires explicit deploy + Yasha sign-off in PR

### Subtasks

- [ ] **SUB 4.1:** Add `OTP_RECIPIENT_MODE` config read at startup, default `qa`
      Description: Read from env / KV. No silent fallback to prod.
      Estimate: S
- [ ] **SUB 4.2:** Branch OTP send path on mode; route + log accordingly
      Description: One code path, two recipient resolvers. No duplication.
      Estimate: M
- [ ] **SUB 4.3:** Test both modes against TEST account from TASK 3
      Description: qa mode → Yasha's inbox; prod mode → TEST account inbox. Verify both end-to-end.
      Estimate: S
- [ ] **SUB 4.4:** Document mode switch in `docs/specs/otp-recipient-modes.md`
      Description: Including "how to cut over to prod" runbook.
      Estimate: S

---

## TASK 5: Korin QA pass against seekapa:117 / current prod bot

- **Type:** Task
- **Priority:** P1
- **Components / labels:** QA, cs-agent, Support
- **Estimate:** L
- **Depends on:** TASK 3, TASK 4

**Description:**
Korin runs a structured QA pass against the support bot using the TEST CRM account (TASK 3) with OTP in QA mode (TASK 4). She must NEVER be running QA against real customer accounts — that's the whole point of TASKs 3+4. Coverage: topic scope (TASK 1), CRM RO answers (TASK 2), OTP flow, escalation triggers, multilingual (he/en/ar/es/pt).

**Acceptance criteria:**
- QA test plan exists and is reviewed by Yasha
- All scenarios executed against TEST account, results logged
- Each failure filed as its own bug with reproduction steps
- Pass rate target agreed with Yasha before pass starts (current baseline: 40.6% on v109 acceptance eval — set realistic gate)
- Korin signs off on the pass in this ticket's comments

### Subtasks

- [ ] **SUB 5.1:** Draft QA test plan covering topic scope + CRM RO + OTP + escalation + multilingual
      Description: Hand off to Korin for review before execution.
      Estimate: M
- [ ] **SUB 5.2:** Korin executes the plan against seekapa:117 (TEST account only)
      Description: Logs results in a shared sheet / Jira test cycle.
      Estimate: L
- [ ] **SUB 5.3:** Triage failures, file bugs, link to this ticket
      Description: One bug per distinct failure mode.
      Estimate: M

---

## TASK 6: Bug — Chatwoot IM chat assignment sticks on agent reply

- **Type:** Bug
- **Priority:** P2
- **Components / labels:** Chatwoot, Infra, IM
- **Estimate:** M
- **Depends on:** none

**Description:**
Known glitch flagged in the Yasha email: when an agent replies to a chat in IM (Chatwoot), the conversation is auto-assigned to them and stays assigned. To "reset" you currently have to resolve the conversation and start a new message in TG. This breaks normal Support flow where multiple agents rotate on a queue.

**Acceptance criteria:**
- Reproduction documented (TG → reply → check assignment + reset path)
- Root cause identified (Chatwoot auto-assignment rule? agent-on-reply config? webhook bug?)
- Fix shipped OR documented workaround formalized in Support runbook
- Yasha confirms the new behavior is acceptable for Support's workflow

### Subtasks

- [ ] **SUB 6.1:** Reproduce on staging Chatwoot and capture the assignment-rule config
      Description: Screenshot + which Chatwoot setting/automation triggers it.
      Estimate: S
- [ ] **SUB 6.2:** Decide: fix the auto-assignment, or formalize the resolve-and-restart workflow
      Description: With Yasha — which matches Support's actual desk model?
      Estimate: S
- [ ] **SUB 6.3:** Ship fix or update runbook
      Description: Whichever path TASK 6.2 selected.
      Estimate: M

---

## TASK 7: Bug — Chatwoot occasionally hides agent response until refresh

- **Type:** Bug
- **Priority:** P2
- **Components / labels:** Chatwoot, Infra, IM, frontend
- **Estimate:** M
- **Depends on:** none

**Description:**
Known render glitch: sometimes after sending a reply in Chatwoot IM the agent doesn't see their own response. Workaround today is refresh page, or switch to another chat and back. Looks like a frontend state-sync issue. Want it filed properly because Support agents will hit it daily once we cut over from Voicepin/LiveAgent.

**Acceptance criteria:**
- Frequency captured (how often per agent per day — log-based or survey)
- Root cause hypothesis (websocket drop? state mutation? race?) — at least one strong lead
- Fix shipped OR a 1-key shortcut workaround (e.g. press F5 binding) documented in Support runbook

### Subtasks

- [ ] **SUB 7.1:** Add browser-side log capture to quantify how often it happens
      Description: Lightweight client log → infra channel, no PII.
      Estimate: S
- [ ] **SUB 7.2:** Inspect Chatwoot frontend / websocket logs at reproduction time
      Description: Find what fails to fire the message-list update.
      Estimate: M
- [ ] **SUB 7.3:** Patch or document workaround
      Description: Patch preferred; workaround acceptable if root cause is upstream.
      Estimate: M

---

## TASK 8: Scope Voicepin → in-house IM migration for Support (TG + WA)

- **Type:** Task
- **Priority:** P1
- **Components / labels:** Infra, Support, IM, migration
- **Estimate:** L
- **Depends on:** none

**Description:**
First and simplest step of the unification: move Support's Telegram + WhatsApp traffic off Voicepin onto our in-house IM (Chatwoot) — the same stack already replacing Voicepin in HL call-center + marketing campaigns, with UY rollout in progress. Need to scope what Support specifically uses Voicepin for so the cutover doesn't drop a workflow.

**Acceptance criteria:**
- Inventory of every Voicepin feature Support actively uses for TG + WA
- Each feature mapped to in-house IM capability: ✅ have / ⚠️ gap / ❌ missing
- Gap list reviewed with Yasha, prioritized for build vs accept
- Cutover plan written (channels to migrate, sequence, rollback)

### Subtasks

- [ ] **SUB 8.1:** Shadow Support for a half-day, list every Voicepin feature they actually touch
      Description: Don't trust the docs — watch real usage. TG + WA only in this task.
      Estimate: M
- [ ] **SUB 8.2:** Map each feature to in-house IM (have / gap / missing)
      Description: One row per feature in a table. Reuse what's already been built for HL.
      Estimate: M
- [ ] **SUB 8.3:** Review gap list with Yasha, decide build-vs-accept
      Description: Yasha decides which gaps block migration vs are acceptable.
      Estimate: S
- [ ] **SUB 8.4:** Write cutover plan + rollback for Support TG + WA
      Description: Phased channel-by-channel, not big-bang.
      Estimate: M

---

## TASK 9: LiveAgent email — gap analysis vs in-house IM

- **Type:** Task
- **Priority:** P2
- **Components / labels:** Infra, Support, IM, email, migration
- **Estimate:** L
- **Depends on:** TASK 8

**Description:**
Second wave of the unification: replace LiveAgent (Support's email tooling) with in-house IM email. Yasha previously raised that there are LiveAgent features we don't yet have. We need that list explicitly so the in-house email side can close those gaps before cutover — same have/gap/missing approach as TASK 8 but for email instead of TG/WA.

**Acceptance criteria:**
- Full list of LiveAgent features Support actively uses for email
- Each feature mapped to in-house IM email: ✅ have / ⚠️ gap / ❌ missing
- Gap list shared with Yasha and prioritized
- A build plan exists for must-have gaps before email cutover is scheduled

### Subtasks

- [ ] **SUB 9.1:** Collect LiveAgent feature list from Support (shadow + interview Yasha)
      Description: Templates, canned replies, SLA timers, ticket-routing rules, reporting — all of it.
      Estimate: M
- [ ] **SUB 9.2:** Map each LiveAgent feature against in-house IM email
      Description: One row per feature, same table format as TASK 8.
      Estimate: M
- [ ] **SUB 9.3:** Build plan for must-have gaps
      Description: Concrete tickets per gap, sized, prioritized. Output of this subtask = more Jira tickets.
      Estimate: M

---

## Notes for Shoval when creating in Jira

- Create the **Epic** first → use it as the parent for every TASK below.
- TASK 3 (TEST CRM account) is the **gating P0** — TASKs 4 and 5 both depend on it. Create it first among the children.
- TASKs 1, 2, 3, 4, 5 form the **prod-readiness track**. TASKs 8, 9 form the **unification track**. TASKs 6, 7 are infra bugs surfacing now because we're about to put real agents on the stack daily.
- Hebrew quote preserved in TASK 3 description — Yasha will recognize his own words.
- After creation, paste Jira keys back next to each TASK / SUB line in this file so we have the local→Jira mapping.
