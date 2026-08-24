# Yasha — sentimark-rg Reader access request

**Draft message (paste-ready).** Casual, Hebrew/English mix, bottom-line. Trim further if too long.

---

**Option A — short, in Hebrew (preferred for Slack/WhatsApp)**

יאשה, אני עושה consolidation על הAI workloads תחת stsentimarkv2 וsentimark-env לפי מה שאמרנו.
האזור שלי ב-AZAI_group כבר על plan אחד וכל הAI data כבר על stsentimarkv2.
חסר לי Reader על sentimark-rg כדי לראות מה רץ שם (func-marketing-newsletter על EP1, func-market-reports-prod, ועוד) ולתכנן איך מעבירים ל-sentimark-env.
לא נוגע, רק קורא. ה-UPN: shoval.be@i-sdd.com

---

**Option B — short, in English (for Teams/email if more formal)**

Yasha — running the AI-storage consolidation onto stsentimarkv2 + sentimark-env per our earlier convo.
AZAI_group side is done: one ASP, one canonical storage account, AI containers moved.
I need Reader on sentimark-rg to see func-marketing-newsletter (EP1), func-market-reports-prod, and the rest — read-only, no changes. Once I can see it I'll write up the EP1 → Container Apps plan for your review before any move.
UPN: shoval.be@i-sdd.com

---

**Exact role assignment command (for him to run)**

```bash
az role assignment create \
  --assignee f71d0e70-5b5c-484e-a683-e3b98685cc91 \
  --role "Reader" \
  --scope /subscriptions/08b0ac81-a17e-421c-8c1b-41b59ee758a3/resourceGroups/sentimark-rg
```

If he wants stricter (function-app-only):
```bash
az role assignment create \
  --assignee f71d0e70-5b5c-484e-a683-e3b98685cc91 \
  --role "Website Contributor" \
  --scope /subscriptions/08b0ac81-a17e-421c-8c1b-41b59ee758a3/resourceGroups/sentimark-rg
```

(Reader is enough for planning. Don't need Contributor for the survey phase.)

---

**Optional follow-up if he asks "what for":**

1. Map every Function App + Web App + Container App in sentimark-rg → its current SKU and plan
2. Identify which ones are dormant vs active
3. Cost the EP1 surface vs equivalent Container Apps consumption
4. Propose the lift-and-shift batches with rollback per workload
5. No touch until he OKs each batch

He already asked 2026-05-06 to lift func-marketing-newsletter off EP1; this is the prep work.
