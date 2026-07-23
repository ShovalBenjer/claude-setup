---
name: answer-question
description: Research-only mode. Read files, search code, web search. No code changes, no verify gate, no forge loop.
effort: low
---

## Purpose

Answer a question about the codebase, architecture, technology, or design decisions.
This skill bypasses the forge loop -- no TDD, no verification gate, no /reflect.

## Allowed

- Read, Grep, Glob (file search and content search)
- Bash (read-only: `git log`, `git diff`, `git show`, `ls`, `wc`)
- WebSearch, WebFetch, Context7 (external research)
- Task with Explore subagent (codebase exploration)

## Forbidden

- Write, Edit (no code changes)
- Bash (no write commands, no builds, no deploys)
- No forge loop phases
- No verify gate
- No /reflect or Codex review

## Output Format

Answer with citations:
- File references: `path/to/file.py:42`
- Code snippets: inline with line numbers
- External sources: markdown links

## When to Exit

If the answer reveals that code changes are needed, state what needs changing and return to default mode (forge loop activates automatically).
