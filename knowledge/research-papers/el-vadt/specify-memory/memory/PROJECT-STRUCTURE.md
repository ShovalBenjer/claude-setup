# el-vadt - File Placement Guide

**Project:** el-vadt
**Type:** AI/Sales Agents + Conversation Analysis
**Last Updated:** 2026-02-18
**Version:** 1.0

---

## Quick Decision Tree

```
📁 What type of file is this?

├─ SOURCE CODE?
│  └─ YES → [project-specific-code-dir]/ ✅
│
├─ TEST FILE?
│  └─ YES → tests/ ✅
│
├─ DOCUMENTATION?
│  ├─ YES + Image/screenshot?
│  │  └─ YES → docs/assets/screenshots/ ✅
│  │  └─ NO  → docs/ ✅
│  └─ NO
│
├─ CONFIGURATION?
│  └─ YES → .github/, .claude/, .kilocode/ ✅
│
├─ SPECIFICATION?
│  └─ YES → specs/ ✅
│
├─ BUILD OUTPUT?
│  └─ YES → dist/, build/, out/ ✅ (ignored by git)
│
├─ TEST CACHE/DATA?
│  └─ YES → .pytest_cache, .hypothesis, playwright-report/ ✅ (ignored)
│
├─ RUNTIME DATA?
│  └─ YES → data/ ✅ (ignored by git)
│
└─ TEMP/DEBUG?
   └─ YES → /tmp/ or DELETE ✅ (not in repo)

UNSURE? → See full guide below
```

---

## Directory Structure

```
el-vadt/
├── .specify/
│   └── memory/                    ← Knowledge system (you are reading)
│       ├── INDEX.md               ← Navigation
│       ├── MEMORY.md              ← Cross-session state
│       ├── PROJECT-STRUCTURE.md   ← This file
│       ├── RULES.md               ← Development rules
│       └── README.md              ← Quick start
│
├── [source-code-dir]/             ← Primary source code
│   └── [Project-specific structure]
│
├── tests/                         ← All test files
│   ├── unit/                      ← Unit tests
│   ├── integration/               ← Integration tests
│   └── e2e/                       ← End-to-end tests
│
├── docs/                          ← Documentation (committed)
│   ├── README.md                  ← Project overview
│   └── assets/                    ← Images for docs (committed)
│       └── screenshots/
│
├── .github/                       ← GitHub configuration
│   └── workflows/                 ← CI/CD workflows
│
├── .claude/                       ← Claude Code config
│   └── rules/                     ← Development rules (legacy, migrated to .specify/)
│
├── dist/ or build/ or out/        ← Build output (ignored)
│
├── data/                          ← Runtime data (ignored)
│   ├── databases/
│   ├── runs/
│   └── cache/
│
├── .pytest_cache/                 ← Pytest cache (ignored)
├── .hypothesis/                   ← Hypothesis data (ignored)
├── htmlcov/                       ← Coverage reports (ignored)
│
├── CLAUDE.md                      ← Main developer guide
├── .gitignore                     ← Git ignore rules
└── package.json or pyproject.toml ← Project config
```

---

## File Placement Rules

### ✅ Source Code (ALWAYS COMMIT)

**Location:** `[source-code-dir]/`

**Examples:**
- Python: `src/`, `lib/`
- JavaScript: `src/`, `lib/`
- [Project-specific]: `[your-structure]/`

**Rules:**
- Organized by module or feature
- Follow language conventions
- Include type hints/JSDoc

---

### ✅ Tests (ALWAYS COMMIT)

**Location:** `tests/`

**Structure:**
```
tests/
├── unit/              ← Pure function tests (no IO)
├── integration/       ← Pipeline/module tests
├── e2e/              ← End-to-end tests
└── [test-type]/      ← Custom test categories
```

**Rules:**
- Mirror source structure for unit tests
- >90% coverage required
- Descriptive test names

---

### ✅ Documentation (ALWAYS COMMIT)

**For Project Docs:**
```
docs/
├── README.md                    ← Overview
├── [feature]/
│   └── README.md               ← Feature docs
└── assets/
    └── screenshots/            ← UI screenshots
        └── [feature-name].png  ← For docs only!
```

**Rules:**
- Only commit docs/ images if used in README or docs
- Link images from docs/ in markdown
- Keep docs/ clean and organized

---

### ✅ Configuration (ALWAYS COMMIT)

**GitHub Configuration:**
```
.github/
├── workflows/
│   ├── ci.yml          ← Continuous integration
│   ├── tests.yml       ← Test runner
│   └── [workflow].yml
└── [config files]
```

**Claude Code Configuration:**
```
.claude/
├── rules/              ← Development rules (being migrated)
└── mcp.json           ← MCP server config (if applicable)
```

**Project Configuration:**
- `pyproject.toml` or `package.json`
- `[framework].config.json`
- `.env.example` (NEVER `.env`)

---

### ✅ Specifications (ALWAYS COMMIT)

**Location:** `specs/`

**Examples:**
```
specs/
├── 001-feature-name/
│   ├── spec.md
│   └── examples/
└── [spec-number]-[name]/
```

---

### ❌ Build Output (NEVER COMMIT)

**Locations:** `dist/`, `build/`, `out/`, `.next/`, `__pycache__/`

**Ignored automatically by `.gitignore`**

**Examples:**
- Compiled JavaScript
- Bundled assets
- Generated files
- Build artifacts

---

### ❌ Test Caches & Reports (NEVER COMMIT)

**Locations:**
```
.pytest_cache/          ← Pytest cache (auto-ignored)
.hypothesis/            ← Hypothesis test data (auto-ignored)
htmlcov/               ← Coverage reports (auto-ignored)
playwright-report/     ← Playwright reports (auto-ignored)
.coverage             ← Coverage data (auto-ignored)
```

**Why:** Test caches change frequently and are project-local only

---

### ❌ Runtime Data (NEVER COMMIT)

**Location:** `data/`

**Examples:**
```
data/
├── databases/         ← SQLite files, caches
├── runs/             ← Ingestion outputs, manifests
├── cache/            ← API caches, temp data
└── [runtime-type]/
```

**Also Ignored:**
- `.env` (environment variables)
- `.db` files
- `.log` files
- Temporary outputs

---

### ❌ Temporary Files (NEVER COMMIT)

**Locations:** `/tmp/`, delete after use

**Examples:**
- `.tmp` files
- `.bak` backup copies
- `.temp` temporary files
- Debug output files

**Rule:** Delete or move to `/tmp/`, never commit

---

## Common Mistakes & Fixes

### ❌ Mistake: Screenshot in root directory

```
❌ WRONG:
  my-feature-screenshot.png (in root)

✅ CORRECT:
  docs/assets/screenshots/my-feature-screenshot.png
```

**Prevention:** Pre-commit hook blocks root .png files

**Fix:**
```bash
mkdir -p docs/assets/screenshots/
mv my-feature-screenshot.png docs/assets/screenshots/
git add docs/assets/screenshots/my-feature-screenshot.png
```

---

### ❌ Mistake: .env file committed

```
❌ WRONG:
  .env (with real secrets!)

✅ CORRECT:
  .env.example (template only)
  .env (local only, in .gitignore)
```

**Prevention:** Pre-commit hook blocks .env files

**Fix:**
```bash
git rm --cached .env
echo ".env" >> .gitignore
# Rotate all secrets
```

---

### ❌ Mistake: Database file in root

```
❌ WRONG:
  project.db (in root)

✅ CORRECT:
  data/databases/project.db (ignored by git)
```

**Prevention:** Pre-commit hook blocks .db files

**Fix:**
```bash
mkdir -p data/databases/
mv project.db data/databases/
# Update config to point to new location
```

---

### ❌ Mistake: Test cache committed

```
❌ WRONG:
  .pytest_cache/ committed to git

✅ CORRECT:
  .pytest_cache/ in .gitignore (auto-ignored)
```

**Prevention:** Pre-commit hook blocks .pytest_cache/

**Fix:**
```bash
git rm -r --cached .pytest_cache/
# Will be auto-ignored on next run
```

---

### ❌ Mistake: Build outputs committed

```
❌ WRONG:
  dist/ with compiled files committed

✅ CORRECT:
  dist/ in .gitignore (auto-ignored)
```

**Prevention:** Pre-commit hook blocks dist/ commits

**Fix:**
```bash
git rm -r --cached dist/
# Will be auto-ignored on next build
```

---

## File Placement FAQ

**Q: Where do I put configuration files?**
A: `.github/` (GitHub), `.claude/` (Claude Code), root level (`pyproject.toml`, `package.json`)

**Q: Where do I put README?**
A: `docs/README.md` (if docs/ exists) or root level `README.md`

**Q: Where do I put screenshots from tests?**
A: `.pytest_cache/` or `.playwright-mcp/` (ignored, for testing only)

**Q: Where do I put UI screenshots for documentation?**
A: `docs/assets/screenshots/` (only if used in docs!)

**Q: Where do I put my test results?**
A: `htmlcov/` or `playwright-report/` (auto-ignored)

**Q: Where do I put database files?**
A: `data/databases/` (ignored, not committed)

**Q: Where do I put API responses/test data?**
A: `data/` directory (ignored, local only)

**Q: Where do I put debug logs?**
A: `/tmp/` or don't commit (auto-ignored)

**Q: Can I put anything in root?**
A: Only: CLAUDE.md, README.md, .gitignore, package.json/pyproject.toml, LICENSE

---

## Clutter Prevention

### Pre-Commit Hook Blocks:
- ❌ `*.png` in root directory
- ❌ `*.jpg` in root directory
- ❌ `.env` files
- ❌ `.tmp`, `.bak` files
- ❌ `.pytest_cache/` directory
- ❌ `.hypothesis/` directory
- ❌ `.dev-staging/` directory

### If Hook Blocks You:
1. Read the error message (it tells you where to move the file!)
2. Move file to correct location
3. Try commit again
4. If still unsure, check this guide

---

## Team Guidelines

### ✅ DO:
- Check this decision tree when unsure
- Ask before committing if not sure
- Follow the structure consistently
- Update MEMORY.md when you add file types
- Keep root directory clean

### ❌ DON'T:
- Commit test caches or build output
- Commit .env or secrets files
- Put images in root directory
- Commit runtime data
- Try to bypass pre-commit hook (it's helping you!)

---

## Verification Checklist

Before committing:

- [ ] Source code is in correct directory
- [ ] Tests are in `tests/` directory
- [ ] No `.png` files in root
- [ ] No `.env` files being committed
- [ ] No `.pytest_cache/` or `.hypothesis/`
- [ ] No build outputs (dist/, build/, etc.)
- [ ] Documentation is in docs/
- [ ] Configuration files are in .github/ or root level

---

**Version:** 1.0
**Last Updated:** 2026-02-18
**Status:** Ready to use
