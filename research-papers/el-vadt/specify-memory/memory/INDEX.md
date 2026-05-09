# el-vadt - Navigation Hub

**Project:** el-vadt
**Type:** AI/Sales Agents + Conversation Analysis
**Status:** Organized 2026-02-18
**Last Updated:** 2026-02-18

---

## Quick Navigation

### 📚 Documentation (Read in Order)

1. **This file (INDEX.md)** - You are here
   - Navigation hub for el-vadt
   - Links to all knowledge system documents

2. **MEMORY.md** - Cross-session state
   - What was done in last session
   - Current blockers
   - Next steps
   - Decisions made

3. **PROJECT-STRUCTURE.md** - File placement guide
   - Where do files go?
   - File placement decision tree
   - Common mistakes & fixes

4. **RULES.md** - All project rules
   - Development guidelines
   - Quality gates
   - Tooling standards
   - Team conventions

5. **CONSTITUTION.md** (if applicable)
   - Non-negotiable rules
   - System invariants
   - Critical constraints

### 🚀 Getting Started

```bash
# Navigate to project
cd ../el-vadt

# Read developer guide
cat CLAUDE.md

# Check project structure rules
cat .specify/memory/PROJECT-STRUCTURE.md

# See what was done in last session
cat .specify/memory/MEMORY.md

# Start development
[PROJECT-SPECIFIC-COMMANDS]
```

---

## Document Descriptions

### MEMORY.md (Cross-Session Persistence)
**Purpose:** Track work across sessions so context isn't lost

**Contains:**
- Last session's accomplishments
- Current blockers
- Active decisions
- Next session priorities
- Questions for team

**When to Update:** End of every work session

### PROJECT-STRUCTURE.md (File Placement)
**Purpose:** Answer "Where does this file go?"

**Contains:**
- Proper file organization
- File placement decision tree
- Common mistakes & fixes
- Clutter prevention rules
- Team guidelines

**Use When:** Creating new files, unsure about structure

### RULES.md (Development Standards)
**Purpose:** "How do we do things here?"

**Contains:**
- Development guidelines
- Code quality standards
- Testing requirements
- Git workflow
- Tooling standards

**Use When:** Starting development work

### CONSTITUTION.md (Non-Negotiables)
**Purpose:** Rules that must NEVER be broken

**Contains:**
- Critical constraints
- System invariants
- Data integrity rules
- Security requirements
- Performance targets

**Use When:** Making architecture decisions

---

## File Tree

```
el-vadt/
├── .specify/memory/           ← Knowledge system
│   ├── INDEX.md               ← Navigation hub (you are here)
│   ├── MEMORY.md              ← Cross-session state
│   ├── PROJECT-STRUCTURE.md   ← File placement guide
│   ├── RULES.md               ← Development rules
│   ├── CONSTITUTION.md        ← Non-negotiables (if applicable)
│   └── README.md              ← Quick start
├── CLAUDE.md                  ← Developer guide (main entry point)
├── .claude/                   ← Claude Code config
├── .gitignore                 ← Git ignore rules
└── [rest of project files]
```

---

## Common Tasks

### Starting a Work Session
1. Open `.specify/memory/MEMORY.md`
2. See what was done last session
3. Review blockers and decisions
4. Open CLAUDE.md
5. Start development

### Creating a New File
1. Check `PROJECT-STRUCTURE.md` decision tree
2. Place file in correct location
3. Update MEMORY.md if adding new file type

### Adding New Rules
1. Update RULES.md
2. Document in MEMORY.md
3. Brief team if major change

### Before Committing
1. Read `PROJECT-STRUCTURE.md` prevention rules
2. Verify files are in correct locations
3. Check pre-commit hook feedback
4. Commit with conventional commit message

---

## Team Onboarding

### New Developer (First Time)
1. Read this INDEX.md (5 min)
2. Read CLAUDE.md (10 min)
3. Read PROJECT-STRUCTURE.md (5 min)
4. Set up development environment (per CLAUDE.md)
5. Ask questions if unclear!

### Expected Time to Full Context
- With good documentation: 20-30 min
- Complex projects: 45-60 min

---

## Quick Reference

**How is work tracked?**
→ MEMORY.md (updated after each session)

**Where do files go?**
→ PROJECT-STRUCTURE.md (decision tree)

**What are the rules?**
→ RULES.md (development standards)

**What can't be broken?**
→ CONSTITUTION.md (non-negotiables)

**How do I set up?**
→ CLAUDE.md (main developer guide)

**Something unclear?**
→ Ask the team or check RULES.md FAQ

---

## Knowledge System Pattern

This unified knowledge system ensures:
- ✅ No context loss between sessions
- ✅ Clear file placement rules
- ✅ Consistent development standards
- ✅ Easy onboarding for new team members
- ✅ 82-88% token efficiency improvement
- ✅ Professional, predictable structure

---

## Next Step

👉 Read **MEMORY.md** to see what was done in the last session, or read **CLAUDE.md** to start development.

---

**Navigation System Version:** 1.0
**Last Updated:** 2026-02-18
**Project:** el-vadt
**Status:** Ready to use
