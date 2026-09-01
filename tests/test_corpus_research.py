"""Tests for tools/corpus/research.py (research corpus DB, spec 2026-07-31)."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "corpus_research_under_test", ROOT / "tools" / "corpus" / "research.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


cr = _load()


@pytest.fixture
def fresh_db(tmp_path):
    conn = cr.connect(tmp_path / "test.db")
    cr.init_schema(conn)
    yield conn
    conn.close()


class TestSchema:
    def test_init_creates_all_tables(self, fresh_db):
        tables = {r[0] for r in fresh_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        expected = {"corpus_meta", "sources", "chunks", "citations",
                    "claim_edges", "artifacts"}
        assert expected <= tables

    def test_fts_virtual_table_exists(self, fresh_db):
        tables = {r[0] for r in fresh_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "chunks_fts" in tables

    def test_version_recorded(self, fresh_db):
        row = fresh_db.execute(
            "SELECT value FROM corpus_meta WHERE key='schema_version'"
        ).fetchone()
        assert int(row[0]) == cr.SCHEMA_VERSION

    def test_init_is_idempotent(self, tmp_path):
        conn = cr.connect(tmp_path / "idem.db")
        v1 = cr.init_schema(conn)
        v2 = cr.init_schema(conn)
        assert v1 == v2
        conn.close()


class TestNormalise:
    def test_dash_normalisation(self):
        assert cr.normalise("–test—") == "-test-"

    def test_trailing_whitespace_stripped(self):
        assert cr.normalise("hello  \n  world  ") == "hello\n  world"

    def test_nfc_normalisation(self):
        import unicodedata
        decomposed = unicodedata.normalize("NFD", "é")
        result = cr.normalise(decomposed)
        assert result == unicodedata.normalize("NFC", "é")


class TestChunker:
    LONG_SECTION = (
        "# Title\n\n"
        "Some prose here about testing the research corpus chunker which "
        "needs at least thirty words per section to avoid merging small "
        "sections into the previous chunk as specified by the minimum "
        "threshold constant.\n\n"
        "## Section Two\n\n"
        "More content with https://example.com link and additional words "
        "so that this section also exceeds the minimum chunk word count "
        "threshold and produces a separate chunk rather than being merged "
        "into the previous section.\n"
    )

    def test_splits_by_heading(self):
        chunks = cr.chunk_file(self.LONG_SECTION, "test")
        assert len(chunks) >= 2

    def test_heading_path_set(self):
        chunks = cr.chunk_file(self.LONG_SECTION, "test")
        assert chunks[0]["heading_path"] == "Title"

    def test_ordinals_sequential(self):
        chunks = cr.chunk_file(self.LONG_SECTION, "test")
        for i, ch in enumerate(chunks):
            assert ch["ordinal"] == i

    def test_kind_classification_prose(self):
        assert cr._classify_chunk("just some regular text here") == "prose"

    def test_kind_classification_code(self):
        assert cr._classify_chunk("```python\nprint(1)\n```") == "code"

    def test_kind_classification_table(self):
        assert cr._classify_chunk("| a | b | c |\n|---|---|---|") == "table"

    def test_subdivide_respects_max(self):
        big = "\n".join(" ".join(["word"] * 20) for _ in range(40))
        parts = cr._subdivide(big, max_words=400)
        assert len(parts) >= 2

    def test_small_chunk_merges_into_previous(self):
        text = (
            "# Head\n\n"
            + " ".join(["word"] * 40) + "\n\n"
            "## Sub\n\nTiny.\n"
        )
        chunks = cr.chunk_file(text, "t")
        assert len(chunks) == 1


class TestSimhash:
    LONG_A = (
        "the quick brown fox jumps over the lazy dog and keeps "
        "running through the forest until reaching a meadow where "
        "the sun shines brightly on the green grass below"
    )
    LONG_B = (
        "the quick brown fox jumps over the lazy dog and keeps "
        "running through the forest until reaching a meadow where "
        "the moon shines brightly on the green grass below"
    )
    LONG_C = (
        "quantum physics describes subatomic particles and their "
        "interactions through mathematical frameworks including "
        "wave functions probability amplitudes and field operators"
    )

    def test_similar_texts_closer(self):
        h1 = cr._simhash(self.LONG_A)
        h2 = cr._simhash(self.LONG_B)
        h3 = cr._simhash(self.LONG_C)
        assert cr._hamming(h1, h2) < cr._hamming(h1, h3)

    def test_identical_texts_zero_hamming(self):
        h = cr._simhash(self.LONG_A)
        assert cr._hamming(h, h) == 0

    def test_signed_conversion_roundtrips(self):
        for val in [0, 1, (1 << 63) - 1, (1 << 63), (1 << 64) - 1]:
            signed = cr._to_signed64(val)
            assert cr._from_signed64(signed) == val


class TestCitations:
    def test_url_extraction(self):
        cites = cr._extract_citations("See https://example.com for details")
        assert len(cites) == 1
        assert cites[0]["target_uri"] == "https://example.com"

    def test_s_tag_extraction(self):
        cites = cr._extract_citations("See [S1] and [S42] for details")
        tags = [c["tag"] for c in cites]
        assert "[S1]" in tags
        assert "[S42]" in tags

    def test_combined_extraction(self):
        cites = cr._extract_citations(
            "See https://example.com and [S1] for details")
        assert len(cites) == 2

    def test_no_citations(self):
        cites = cr._extract_citations("plain text with no references")
        assert len(cites) == 0


class TestFTS5:
    def test_search_returns_results(self, fresh_db):
        sid = cr._source_id("/test.md")
        fresh_db.execute(
            "INSERT INTO sources "
            "(source_id, canonical_uri, kind, title, license_spdx, "
            " license_verdict, license_evidence, fetched_utc, liveness, "
            " content_sha256, bytes) "
            "VALUES (?, '/test.md', 'local_md', 'Test', 'proprietary', "
            " 'vendor', 'local', ?, 'live', 'abc', 100)",
            (sid, cr._now()),
        )
        cid = cr._chunk_id("research corpus full text search query")
        fresh_db.execute(
            "INSERT INTO chunks "
            "(chunk_id, source_id, ordinal, heading_path, kind, "
            " norm_text, raw_text, word_count, norm_sha256, simhash, "
            " status, ingested_utc) "
            "VALUES (?, ?, 0, 'Test', 'prose', "
            " 'research corpus full text search query', "
            " 'research corpus full text search query', 6, ?, 0, "
            " 'accepted', ?)",
            (cid, sid, cr._sha256("research corpus full text search query"),
             cr._now()),
        )
        fresh_db.commit()

        results = cr.query(fresh_db, "research corpus")
        assert len(results) >= 1
        assert results[0]["chunk_id"] == cid

    def test_empty_query_returns_empty(self, fresh_db):
        results = cr.query(fresh_db, "nonexistent_xyzzy_term_12345")
        assert len(results) == 0


class TestDefects:
    def test_uncited_returns_list(self, fresh_db):
        result = cr.uncited_chunks(fresh_db)
        assert isinstance(result, list)

    def test_contradicted_returns_list(self, fresh_db):
        result = cr.contradicted_chunks(fresh_db)
        assert isinstance(result, list)


class TestIngest:
    def test_ingest_md_files(self, tmp_path):
        db_path = tmp_path / "corpus.db"
        conn = cr.connect(db_path)
        cr.init_schema(conn)

        md_dir = tmp_path / "research"
        md_dir.mkdir()
        (md_dir / "paper1.md").write_text(
            "# Paper One\n\n"
            "This is a long enough section about machine learning that "
            "contains a URL citation https://arxiv.org/abs/1234 and has "
            "more than thirty words so the chunker keeps it as a "
            "standalone chunk rather than merging.\n\n"
            "## Results\n\n"
            "The results section also needs enough words to be kept as "
            "a separate chunk with another citation https://doi.org/10 "
            "and sufficient content to exceed the minimum threshold.\n",
            encoding="utf-8",
        )
        (md_dir / "paper2.md").write_text(
            "# Paper Two\n\n"
            "A different paper on distributed systems covering consensus "
            "protocols and their implementations across multiple nodes "
            "in a network with Byzantine fault tolerance.\n",
            encoding="utf-8",
        )

        ledger = tmp_path / "ledger.jsonl"
        stats = cr.ingest(conn, dirs=[md_dir], ledger_path=ledger)
        assert stats["sources"] == 2
        assert stats["chunks"] >= 2
        assert stats["citations"] >= 1
        assert ledger.exists()
        conn.close()

    def test_ingest_idempotent(self, tmp_path):
        db_path = tmp_path / "corpus.db"
        conn = cr.connect(db_path)
        cr.init_schema(conn)

        md_dir = tmp_path / "research"
        md_dir.mkdir()
        (md_dir / "file.md").write_text(
            "# Topic\n\n"
            "Content about a subject with enough words to meet the "
            "minimum chunk threshold and some citation https://ex.com "
            "so the ingest has something to process.\n",
            encoding="utf-8",
        )

        cr.ingest(conn, dirs=[md_dir])
        count1 = conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
        cr.ingest(conn, dirs=[md_dir])
        count2 = conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
        assert count2 == count1
        conn.close()


class TestStatus:
    def test_returns_expected_keys(self, fresh_db):
        s = cr.status(fresh_db)
        assert "sources" in s
        assert "chunks" in s
        assert "citations" in s
        assert "schema_version" in s


class TestDedupSimhash:
    def test_dedup_supersedes_near_duplicates(self, fresh_db):
        sid = cr._source_id("/dedup-test.md")
        fresh_db.execute(
            "INSERT INTO sources "
            "(source_id, canonical_uri, kind, title, license_spdx, "
            " license_verdict, license_evidence, fetched_utc, liveness, "
            " content_sha256, bytes) "
            "VALUES (?, '/dedup-test.md', 'local_md', 'Dedup', "
            " 'proprietary', 'vendor', 'local', ?, 'live', 'abc', 100)",
            (sid, cr._now()),
        )
        base = (
            "the quick brown fox jumps over the lazy dog and keeps "
            "running through the forest until reaching a meadow where "
            "the sun shines brightly on the green grass below"
        )
        variant = (
            "the quick brown fox jumps over the lazy dog and keeps "
            "running through the forest until reaching a meadow where "
            "the moon shines brightly on the green grass below"
        )
        for i, text in enumerate([base, variant]):
            cid = cr._chunk_id(text + str(i))
            fresh_db.execute(
                "INSERT INTO chunks "
                "(chunk_id, source_id, ordinal, heading_path, kind, "
                " norm_text, raw_text, word_count, norm_sha256, simhash, "
                " status, ingested_utc) "
                "VALUES (?, ?, ?, 'Test', 'prose', ?, ?, ?, ?, ?, "
                " 'accepted', ?)",
                (cid, sid, i, text, text, len(text.split()),
                 cr._sha256(text), cr._to_signed64(cr._simhash(text)),
                 cr._now()),
            )
        fresh_db.commit()

        count = cr.dedup_simhash(fresh_db, threshold=20)
        assert count >= 1
        superseded = fresh_db.execute(
            "SELECT count(*) FROM chunks WHERE status='superseded'"
        ).fetchone()[0]
        assert superseded >= 1


class TestSelftest:
    def test_selftest_passes(self):
        assert cr.selftest() is True
