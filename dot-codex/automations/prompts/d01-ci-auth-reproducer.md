# D1. CI Auth Reproducer

Schedule: Weekdays 08:00 (before work)
Repo root: all repos under `/home/shovalbe/projects/` with `azure-pipelines.yml`
Mode: read + ADO Bug if breakage detected

For each repo with `azure-pipelines.yml`:

1. Parse the YAML for every step that touches:
   - `az login` / `AzureCLI@2` (auth)
   - service connection name (e.g., `managecorpairegistry`, `U-BTech - CSP`)
   - Key Vault name (e.g., `kv-seekapa-apps`, `shoval-key-vault`)
   - secret variable name (e.g., `FOUNDRY-API-KEY`)
   - token audience / endpoint (Foundry, Responses API, KV REST)

2. For each, run a *dry-run reproducer*:
   - `az login --service-principal` (using the documented SP if available)
   - `az keyvault secret show --name <secret> --vault-name <vault> -o tsv > /dev/null`
   - For Foundry endpoints: hit the documented base URL with a low-cost GET (HEAD if supported).

3. If any reproducer fails, file an ADO Bug:

```bash
~/.claude/bin/work-item.sh create --type Bug \
  --title "CI auth pre-fail: <repo> <step>" \
  --tags "ci-auth,preventive"
```

Body must include:
- which step would break (file:line)
- what command failed and stderr (with secrets redacted)
- link to the last `fix(ci)` commit that touched that step (`git log -1 --pretty=format:"%H %s" -- <file>`)
- pointer to memory file `~/.claude/projects/-home-shovalbe/memory/lesson_azure_kv_auth_pattern.md`

4. Output a daily summary at `~/.claude/docs/CI_AUTH_HEALTH_<DATE>.md` with green/yellow/red per repo and per auth class.

Auth: `az login` is assumed available on the runner. If not, write `auth-needs-refresh` in the report and exit 0 — never retry.

Evidence cited from history: SHAs `a85e63dc`, `33b26297`, `306ea6ad`, `e2f2225e`, `bff6ee0`, `ef936791` — six `fix(ci)` auth commits in 60 days. This catches the next one before it merges.
