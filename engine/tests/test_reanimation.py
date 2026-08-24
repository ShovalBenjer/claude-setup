"""Reanimation pipeline: the offline stages hold their contract.

Stage 2 (persona.py) calls a hosted lane and is NOT exercised here; these cover the
stages that must be correct without a network: masking roundtrip, the fingerprint
math, and extraction shape. The lane router has its own live smoke, run by hand.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(*argv):
    return subprocess.run([sys.executable, *argv], cwd=ROOT,
                          capture_output=True, text=True)


def test_mask_roundtrip_is_reversible():
    r = run("tools/reanimation/mask.py")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "roundtrip ok" in r.stdout


def test_mask_tokenizes_the_structured_pii():
    sys.path.insert(0, str(ROOT / "tools" / "reanimation"))
    import mask
    v = mask.Vault()
    masked = v.mask("ping 052-1234567 or a@b.com")
    assert "052-1234567" not in masked and "a@b.com" not in masked
    assert v.unmask(masked) == "ping 052-1234567 or a@b.com"
    # a stable token: same value masks to the same token
    v2 = mask.Vault()
    m1 = v2.mask("a@b.com and a@b.com")
    assert m1.count("<EMAIL_1>") == 2


def test_fingerprint_over_a_tiny_corpus(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    rows = [{"ts": "1", "text": "בוקר טוב מה קורה", "direction": "unknown"},
            {"ts": "2", "text": "hello there friend", "direction": "unknown"},
            {"ts": "3", "text": "בוקר טוב שוב", "direction": "unknown"}]
    corpus.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows),
                      encoding="utf-8")
    (tmp_path / "meta.json").write_text('{"contact": "test"}', encoding="utf-8")
    r = run("tools/reanimation/fingerprint.py", str(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    fp = json.loads((tmp_path / "fingerprint.json").read_text())
    assert fp["messages"] == 3
    assert fp["direction_known"] is False
    assert 0 < fp["script_mix"]["hebrew_ratio"] < 1  # mixed corpus
    assert "בוקר" in fp["top_words"]


def test_fingerprint_empty_corpus_does_not_crash(tmp_path):
    (tmp_path / "corpus.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "meta.json").write_text("{}", encoding="utf-8")
    r = run("tools/reanimation/fingerprint.py", str(tmp_path))
    assert r.returncode == 0
    assert json.loads((tmp_path / "fingerprint.json").read_text())["messages"] == 0
