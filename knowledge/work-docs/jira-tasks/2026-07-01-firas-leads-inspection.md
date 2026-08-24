# Initiative: Firas leads count (DEV-5013 agent-call-tracker)

**Date drafted:** 2026-06-30 (for 2026-07-01)
**Owner:** Shoval (coordinates) | Yasha/Vlad (firewall) | Amit (definition)
**Context:** The CTeam B email-scope fix landed and Amit confirmed CTeam B works. But Amit disputes Firas: the report shows ~2 leads and he says it is "not 2". The tracker computes leads = COUNT(DISTINCT related_to) over the same rows as calls; calls=137 on 06-29 looks right, so the 2 is a faithful distinct count over those rows. Either his calls mostly have a blank related_to (CRM-linkage, not a tracker bug) or "leads" means a different field than related_to (definition gap). Can't query the CRM locally: panda_db (GCP, 34.38.141.12) is firewalled to the VNet; my shell + your machine are blocked, and Amit can't run SQL.

---

## TASK 1: Inspect Firas's leads and find the root cause

- **Type:** Task
- **Priority:** P1
- **Components / labels:** agent-call-tracker, DEV-5013, data, CRM
- **Estimate:** S (under an hour once CRM access exists)
- **Depends on:** none

**Description:**
Settle whether the tracker undercounts Firas's leads or faithfully reflects the CRM. Get a client onto the CRM, look at the actual related_to on Firas's calls (not just the count), and reconcile what "leads" means with Amit. Outcome is a recorded root cause: CRM-linkage, definition gap, or a real tracker bug.

**Acceptance criteria:**
- The `(blank)` vs real-lead split of Firas's calls for 2026-06-29 is known (query A below).
- We know whether the tracker's distinct-related_to equals what Amit calls "leads".
- A one-line root cause is recorded on DEV-5013 (and which TASK 2 path applies).

### Subtasks

- [ ] **SUB 1.1:** Get a client onto the CRM.
      Description: confirm the current egress IP first (`curl -s https://api.ipify.org`, it rotates; was 87.68.185.25), then ask Yasha/Vlad to add `<that-ip>/32` to the GCP firewall on panda_db (34.38.141.12). Then ping Claude to run the queries (read-only `avi_lior`). Alternative: anyone already on the VNet/allowlisted runs queries A+B.
      Estimate: S
      Avenues already tried + dead-ended from a normal shell (2026-06-30, so don't re-try cold):
        (a) CRM MySQL panda_db @ 34.38.141.12 -> connect timeout (GCP firewall, VNet-only).
        (b) Call Analyzer Postgres `corp-company-postsql.postgres.database.azure.com:5432` -> connect timeout
            (Azure PG firewall; creds ARE in the `Shoval` Key Vault as `callanalyzer-pg-{host,user,password}`,
            so the moment my egress IP is allow-listed on that PG server this is the fastest path: /tmp/analyzer_probe.py
            already discovers the schema + aggregates Firas's distinct acc vs the tracker's distinct related_to).
        (c) Call Analyzer REST API `https://analyzer.corp-domain.com/api/external/calls` -> REACHABLE (HTTP 401,
            not IP-blocked) but needs the `X-API-Token`; it is NOT on the qc func apps (func-qc-telephony-prod
            has only ELEVENLABS_API_KEY) or any local env. Ask Yasha for an external API token and this works
            with no firewall change at all (params agent_extension/date_from/date_to; per-call fields acc + lead_id).
      Two viable unblocks, either alone is enough: allow-list my egress /32 on the analyzer PG server (b), OR get an
      analyzer X-API-Token (c). (a) needs the CRM firewall change and is the same blocker as before.
- [ ] **SUB 1.2:** Run the two read-only inspection queries + sample related_to.
      Description: run A and B (below) for 2026-06-29; also `SELECT related_to, call_status, time_of_call FROM panda_db.calls ... LIMIT 30` for a raw sample of Firas's rows.
- [ ] **SUB 1.3:** Reconcile the "leads" definition with Amit.
      Description: ask Amit exactly what he counts as Firas's leads (distinct accounts dialed / new leads created / customers contacted) and which vTiger screen/field shows that number. Compare to the tracker's related_to.
- [ ] **SUB 1.4:** Record the root cause + pick the TASK 2 path.
      Description: blank ≈ calls -> CRM account-tagging (path 2A); many distinct real leads but tracker shows 2 -> real undercount (path 2C); different field/entity -> definition gap (path 2B).

**Query A (decisive: where do his calls point):**
```sql
SELECT CASE WHEN related_to IS NULL OR TRIM(related_to)='' THEN '(blank)' ELSE related_to END AS lead,
       COUNT(*) AS calls
FROM panda_db.calls c JOIN panda_db.vtiger_users u ON u.id = c.user
WHERE (u.first_name LIKE '%Firas%' OR u.last_name LIKE '%Firas%')
  AND DATE(c.time_of_call) = '2026-06-29'
GROUP BY lead ORDER BY calls DESC LIMIT 50;
```

**Query B (totals side by side):**
```sql
SELECT COUNT(*) AS calls,
       COUNT(DISTINCT related_to) AS leads_as_tracker_counts,
       SUM(related_to IS NULL OR TRIM(related_to)='') AS blank_calls
FROM panda_db.calls c JOIN panda_db.vtiger_users u ON u.id = c.user
WHERE (u.first_name LIKE '%Firas%' OR u.last_name LIKE '%Firas%')
  AND DATE(c.time_of_call) = '2026-06-29';
```

---

## TASK 2: Apply the fix for whatever TASK 1 found

- **Type:** Task
- **Priority:** P1
- **Components / labels:** agent-call-tracker, DEV-5013
- **Estimate:** S-M (depends on the path)
- **Depends on:** TASK 1

**Description:**
Act on the root cause. Only one path applies; do that one.

**Acceptance criteria:**
- Firas's leads number is either corrected in the tracker or explained as a CRM-side issue with an owner, and Amit agrees it now makes sense.

### Subtasks

- [ ] **SUB 2.1 (path A, CRM-linkage):** if his calls are mostly blank related_to, either get the CRM to tag his calls with an account (Yasha/CRM owner) or add Firas to `excluded_agents` like the auto-dialer so he stops distorting the team report. No tracker-logic change.
- [ ] **SUB 2.2 (path B, definition gap):** if "leads" is a different field/table, point `config.COL_LEAD` at the right column (or add the correct metric) + a test; ship via the pipeline.
- [ ] **SUB 2.3 (path C, real undercount):** if there are many distinct real leads but the tracker shows 2, reproduce in a SQLite test (RED), fix the query/floor in repo.py, GREEN, ship.

---

Related but separate open items (not this task): corp-home SSO still needs Vlad to register `agent-call-tracker` per the Application Authorization wiki, then we set 4 app settings; and the test-gap PR program (PR-3 Testcontainers, PR-4 snapshots+frontend, PR-5 create_app de-monolith) is pending.

---

## RESOLVED: 2026-07-01 (Shoval, in office)

**Access obtained:** Office IP (199.203.90.233) had port 3306 open to panda_db. Connected via avi_lior read-only.

**Root cause (path 2C with a twist -- sentinel, not a real undercount):**
- Firas (user id 10234) made 168 calls on 2026-06-29.
- 167 of those had `related_to = 4294967295` (0xFFFFFFFF, the dialer's 32-bit "no account" sentinel).
- 1 call had a real account (10842732).
- `COUNT(DISTINCT related_to) = 2` was correct SQL but wrong semantics: the sentinel is not a lead.
- Systemic: 2602 sentinel-tagged calls across 11 agents in the prior week.

**Fix shipped:** PR #421 -> main -> run 13712 (2026-07-01, all 6 smoke checks green).
- `tracker/config.py`: `TRACKER_LEAD_SENTINELS` env var (default "4294967295").
- `tracker/repo.py`: `_real_lead_expr()` -- wraps `related_to` in CASE WHEN sentinel/blank THEN NULL ELSE value END so `COUNT(DISTINCT ...)` ignores them.
- `tests/test_lead_sentinel.py`: 3 RED tests, then GREEN.

**Post-fix live readings:** Firas 2 -> 1; Sham was already fine (100-137 real leads/day).

- [x] **SUB 1.1:** Access via office IP (199.203.90.233). Port 3306 open from that location.
- [x] **SUB 1.2:** Queries run. related_to distribution confirmed: 167 sentinel + 1 real account.
- [x] **SUB 1.3:** Definition reconciled -- "leads" = distinct contacted accounts; sentinel is not one.
- [x] **SUB 1.4:** Root cause: dialer sentinel 0xFFFFFFFF inflated COUNT(DISTINCT). Fixed via _real_lead_expr().
- [x] **SUB 2.3 (path C):** Fix in repo.py + sentinel config + 3 tests. Deployed PR #421 run 13712. Smoke passed.

## FOLLOW-UP: definition proven against the live views (2026-07-01, Adminer + pymysql)

The whole schema is a read-only VIEW layer (29 views; avi_lior sees no base tables). Proven mapping:
- **`calls.related_to` = `vtiger_account.accountid`**, NOT the `leads` table. 123/123 of Firas's distinct real dialed ids (06-23..06-30) exist in `vtiger_account.accountid`; 0/123 in `leads.leadid` or `leads.accountlink`.
- Firas has **0 rows in the `leads` view** (assigned_to=10234, all time). He is an ACCOUNT/retention caller, not a lead-gen agent.
- So the dashboard's "Leads" column actually means "distinct customer ACCOUNTS attached to his calls that day," i.e. distinct existing customers dialed. The label "Leads" is a misnomer; it is not the CRM leads pipeline.

Firas 06-29 status breakdown (live): 168 calls = 1 account-tagged (acc 10842732, BUSY) + 167 no-account placeholder. Of the 167: ANSWERED 39, NO ANSWER 67, FAILED 33, BUSY 24, VOICEMAIL 4. So the "1" is a dialer account-tagging artifact; his fair activity number that day is ~40 answered calls, not 1. 06-30 (dialer tagged accounts): 117 distinct accounts.

For Amit: settle whether "leads" means (1) distinct customers contacted (what the tracker shows, only reliable on account-tagged days) or (2) the leads pipeline (Firas has none). Either way the 06-29 "1" is the untagged auto-dialer, not Firas's effort. Open operational question: why the dialer emitted account-less calls through 06-29 then tagged accounts from 06-30.
