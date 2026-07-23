# Mock Prohibition Policy

**Scope:** Global - all projects

## Forbidden

```python
# NO mocking services, DBs, file systems, network
@patch('siu.clients.apify_client.ApifyClient')  # WRONG
@patch('siu.storage.SQLiteStore')  # WRONG
vi.mock('@remotion/renderer')  # WRONG
```

## Correct

```python
# Use recorded fixtures or real components
@vcr.use_cassette('fixtures/apify_sa.yaml')  # VCR.py
nock('https://api.example.com').get('/').replyWithFile(200, 'fixtures/response.json')  # nock
store = SQLiteStore(':memory:')  # Real in-memory DB
```

## Allowed

- Platform stubs (global.figma - unavailable in Node.js)
- Time control (freeze_time, vi.setSystemTime)
- Recorded fixtures from REAL APIs

## Tools

**Python:** VCR.py | **JavaScript:** nock, Polly.js

## Rationale

Mocks hide integration bugs, drift from production, test the mock not the code.

**Enforcement:** `~/.codex/skills/cleanup-crew/detect.sh` scans for violations
