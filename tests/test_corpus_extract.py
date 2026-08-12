"""Corpus extraction: host-independence and the two filter defects found on 2026-08-06.

The selftest inside extract.py covers its own logic. These tests pin the things
that were WRONG when the tool was first run against the real corpus, because a
selftest written after the fix cannot fail for the original reason:

  1. Harness text was IN the corpus while the operator's own slash-command
     arguments were OUT. A single injected skill-cache blob was 804,732 chars,
     96% of everything the filter later removed.
  2. session_recall.py hardcoded the Windows project slug, so on the WSL host it
     reported "no transcripts" instead of the newest one (L-2026-07-31-g).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "corpus"))
sys.path.insert(0, str(ROOT / "tools" / "recall"))

import extract  # noqa: E402
import session_recall  # noqa: E402


def write_transcript(directory: Path, name: str, events: list[dict]) -> Path:
    """Write one transcript file under a project slug and return its path."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    return path


def user(text) -> dict:
    """Build a minimal user event with the given content."""
    return {"type": "user", "sessionId": "s", "message": {"content": text}}


def test_selftest_passes():
    """The tool's own selftest must pass; CI runs it as a named step."""
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "corpus" / "extract.py"),
                        "selftest"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "0 failed" in r.stdout


def test_skill_body_injection_is_excluded(tmp_path):
    """Defect 1a: an 804k-char injected skill body was counted as corpus."""
    blob = "Base directory for this skill: /home/x/skills/deep-research\n" + ("x " * 5000)
    write_transcript(tmp_path / "proj", "a.jsonl", [user(blob), user("a real question")])
    rows, _ = extract.extract(tmp_path)
    texts = [r["text"] for r in rows]
    assert "a real question" in texts
    assert not any(t.startswith("Base directory for this skill") for t in texts)


def test_operator_words_survive_the_command_wrapper(tmp_path):
    """Defect 1b: the turn entered the corpus as raw markup, not as words.

    The old NOISE regex is anchored and listed <command-name>, but these turns
    start with <command-message>, so nothing matched and the wrapper tags were
    embedded along with the args. Pollution, not loss: the assertion is on the
    exact cleaned string, so keeping the markup fails it.
    """
    wrapped = ("<command-message>deep-research</command-message>"
               "<command-name>/deep-research</command-name>"
               "<command-args>find all related skills such as DORA</command-args>")
    write_transcript(tmp_path / "proj", "a.jsonl", [user(wrapped)])
    rows, _ = extract.extract(tmp_path)
    assert len(rows) == 1
    assert rows[0]["text"] == "/deep-research find all related skills such as DORA"


def test_attachments_excluded_by_default_and_admitted_on_request(tmp_path):
    """Attachment payloads stay out unless explicitly opted into."""
    events = [user("kept"),
              {"type": "attachment", "sessionId": "s",
               "message": {"content": "secret file body"}}]
    write_transcript(tmp_path / "proj", "a.jsonl", events)
    default_rows, skipped = extract.extract(tmp_path)
    assert [r["text"] for r in default_rows] == ["kept"]
    assert skipped["attachment"] == 1
    opted_in, _ = extract.extract(tmp_path, include_attachments=True)
    assert "secret file body" in [r["text"] for r in opted_in]


def test_every_slug_is_read_not_just_one(tmp_path):
    """Defect 2, generalised: a per-host slug must not decide what is visible."""
    write_transcript(tmp_path / "C--Users-shova-claude-setup", "w.jsonl",
                     [user("from the windows clone")])
    write_transcript(tmp_path / "-home-shov-work-repos-claude-setup", "l.jsonl",
                     [user("from the wsl clone")])
    rows, _ = extract.extract(tmp_path)
    assert {r["text"] for r in rows} == {"from the windows clone", "from the wsl clone"}
    assert {r["project"] for r in rows} == {"C--Users-shova-claude-setup",
                                            "-home-shov-work-repos-claude-setup"}


def test_identical_turns_collapse_with_an_audit_count(tmp_path):
    """The boot block repeats verbatim; collapsing it must stay visible."""
    write_transcript(tmp_path / "a", "x.jsonl", [user("same"), user("same")])
    write_transcript(tmp_path / "b", "y.jsonl", [user("same")])
    rows, _ = extract.extract(tmp_path)
    assert len(rows) == 1
    assert rows[0]["repeats"] == 3


def test_torn_final_line_does_not_abort_the_walk(tmp_path):
    """Transcripts are appended to by a live process; a partial last line is normal."""
    p = tmp_path / "proj"
    p.mkdir()
    (p / "a.jsonl").write_text(json.dumps(user("survives")) + "\n{ torn",
                               encoding="utf-8")
    rows, _ = extract.extract(tmp_path)
    assert [r["text"] for r in rows] == ["survives"]


@pytest.mark.parametrize("slug", ["C--Users-shova-claude-setup",
                                  "-mnt-c-Users-shova-claude-setup",
                                  "-home-shov-work-repos-claude-setup"])
def test_session_recall_finds_a_transcript_under_any_host_slug(tmp_path, slug):
    """Defect 2: hardcoding one slug made the tool exit 1 on the other host."""
    write_transcript(tmp_path / slug, "u.jsonl", [user("hello")])
    found = session_recall.transcripts(tmp_path)
    assert [p.parent.name for p in found] == [slug]
