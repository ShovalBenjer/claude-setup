"""Oracle for tools/intent/resources.py.

The ledger's whole value rests on one property: the same resource, however it was
spelled, is one id. If normalization is wrong the ledger still looks healthy, still
verifies, still prints rows, and quietly answers "what did we conclude about this repo"
with a fraction of the truth. That failure is silent, so most of this file is about
normalization rather than about the chain.

The second property is that the ledger can report its own coverage. A list of URLs that
cannot say how many were ever reasoned about is a record of exposure wearing the word
coverage, which is the same shape as a gate that cannot fail.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES_PATH = ROOT / "tools" / "intent" / "resources.py"


def _load(path: Path):
    spec = importlib.util.spec_from_file_location("resources_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


res = _load(RES_PATH)

ZAP = "https://github.com/google-research/zapbench"


class NormalizationTests(unittest.TestCase):
    def test_one_repository_spelled_six_ways_is_one_id(self) -> None:
        forms = [
            ZAP,
            "http://github.com/google-research/zapbench",
            "https://www.github.com/google-research/zapbench/",
            "github.com/google-research/zapbench.git",
            "https://github.com/google-research/zapbench/tree/main/README.md",
            "google-research/zapbench",
        ]
        ids = {res.resource_id(res.normalize(f)) for f in forms}
        self.assertEqual(len(ids), 1, f"split into {len(ids)} ids: {ids}")

    def test_a_path_inside_a_repo_collapses_to_the_repo(self) -> None:
        """A file and a line anchor are locations inside one resource."""
        self.assertEqual(
            res.normalize("https://github.com/google-research/zapbench/blob/main/x.py#L42"),
            "github.com/google-research/zapbench",
        )

    def test_two_pages_on_one_domain_stay_two_resources(self) -> None:
        """The repo collapse must not generalise: arxiv/2401 and arxiv/2402 differ."""
        self.assertNotEqual(
            res.normalize("https://arxiv.org/abs/2401.00001"),
            res.normalize("https://arxiv.org/abs/2402.00002"),
        )

    def test_tracking_parameters_do_not_split_a_resource(self) -> None:
        self.assertEqual(
            res.normalize("https://example.com/paper?utm_source=x&id=7&fbclid=abc"),
            res.normalize("https://example.com/paper?id=7"),
        )

    def test_a_meaningful_query_parameter_is_kept(self) -> None:
        self.assertNotEqual(
            res.normalize("https://openreview.net/forum?id=oCHsDpyawq"),
            res.normalize("https://openreview.net/forum?id=different"),
        )

    def test_the_fragment_never_creates_a_new_resource(self) -> None:
        self.assertEqual(
            res.normalize("https://example.com/doc#intro"),
            res.normalize("https://example.com/doc#conclusion"),
        )

    def test_a_domain_that_looks_like_owner_slash_repo_is_not_one(self) -> None:
        """`example.com/thing` has a dot in the first segment, so it is a host."""
        self.assertEqual(res.normalize("example.com/thing"), "example.com/thing")

    def test_the_id_is_reproducible_from_the_url_alone(self) -> None:
        self.assertEqual(res.resource_id(res.normalize(ZAP)),
                         res.resource_id(res.normalize(ZAP)))
        self.assertTrue(res.resource_id("x").startswith("RES-"))
        self.assertEqual(len(res.resource_id("x")), 16)

    def test_an_empty_key_is_rejected_rather_than_hashed(self) -> None:
        self.assertEqual(res.normalize("   "), "")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                res.append(url="  ", path=Path(tmp) / "l.jsonl")


class NoteContractTests(unittest.TestCase):
    def test_a_note_must_point_at_an_artifact(self) -> None:
        """A conclusion with nowhere to read it is the thing this ledger replaces."""
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                res.append(url=ZAP, kind="note", verdict="adopt",
                           path=Path(tmp) / "l.jsonl")

    def test_a_note_must_carry_a_known_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                res.append(url=ZAP, kind="note", verdict="sort-of-good",
                           note_ref="docs/x.md", path=Path(tmp) / "l.jsonl")

    def test_an_unknown_kind_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                res.append(url=ZAP, kind="pondered", path=Path(tmp) / "l.jsonl")

    def test_a_sighting_needs_no_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            row = res.append(url=ZAP, path=Path(tmp) / "l.jsonl")
            self.assertEqual(row["kind"], "seen")
            self.assertEqual(row["verdict"], "")


class LedgerTests(unittest.TestCase):
    def test_a_note_attaches_to_the_same_id_as_its_sighting(self) -> None:
        """Written in different spellings, which is the realistic case."""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "l.jsonl"
            seen = res.append(url="google-research/zapbench", path=p)
            note = res.append(url=ZAP + "/tree/main", kind="note", verdict="reference",
                              note_ref="docs/analysis/zapbench.md", path=p)
            self.assertEqual(seen["id"], note["id"])
            self.assertEqual(len(res.lookup(ZAP, path=p)), 2)

    def test_lookup_finds_a_resource_by_any_spelling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "l.jsonl"
            res.append(url=ZAP, path=p)
            self.assertEqual(len(res.lookup("github.com/Google-Research/ZapBench", path=p)), 1)

    def test_the_chain_verifies_and_detects_an_edit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "l.jsonl"
            res.append(url=ZAP, path=p)
            res.append(url="https://arxiv.org/abs/2401.1", path=p)
            self.assertEqual(res.verify(p), [])

            rows = res.read_rows(p)
            rows[0]["verdict"] = "adopt"
            p.write_text("\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n",
                         encoding="utf-8")
            self.assertTrue(res.verify(p))

    def test_the_note_pointer_is_covered_by_the_hash(self) -> None:
        """Repointing a conclusion at a different document must not go unnoticed."""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "l.jsonl"
            row = res.append(url=ZAP, kind="note", verdict="adopt",
                             note_ref="docs/real.md", path=p)
            self.assertTrue(res.row_altered(dict(row, note_ref="docs/other.md")))

    def test_coverage_reports_what_was_never_reasoned_about(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "l.jsonl"
            res.append(url=ZAP, path=p)
            res.append(url="https://arxiv.org/abs/2401.1", path=p)
            res.append(url="https://arxiv.org/abs/2402.2", path=p)
            res.append(url=ZAP, kind="note", verdict="reference",
                       note_ref="docs/a.md", path=p)

            cov = res.coverage(p)
            self.assertEqual(cov["resources"], 3)
            self.assertEqual(cov["noted"], 1)
            self.assertEqual(cov["coverage_pct"], 33.3)
            self.assertEqual(len(cov["unnoted"]), 2)

    def test_coverage_on_an_empty_ledger_is_zero_not_a_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(res.coverage(Path(tmp) / "nothing.jsonl")["coverage_pct"], 0.0)

    def test_concurrent_writers_neither_lose_rows_nor_fork(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "l.jsonl"
            writers = 20
            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(
                    lambda i: res.append(url=f"https://example.com/paper/{i}", path=p),
                    range(writers),
                ))
            self.assertEqual(len(res.read_rows(p)), writers)
            self.assertEqual(res.verify(p), [], "the chain forked")


class BatchTests(unittest.TestCase):
    """append_many exists because the per-row path is quadratic over a backfill.

    Batching is only safe if the batch chains internally and fails whole. Both are
    asserted, because a batch that half-writes is worse than a slow loop: the retry
    duplicates whatever landed.
    """

    def test_a_batch_chains_internally_and_to_what_was_there(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "l.jsonl"
            first = res.append(url="https://example.net/seed", path=p)
            rows = res.append_many(
                [{"url": f"https://example.net/p/{i}", "source": "docs/x.md"}
                 for i in range(50)], path=p)

            self.assertEqual(rows[0]["prev"], res.row_id(first))
            for a, b in zip(rows, rows[1:]):
                self.assertEqual(b["prev"], res.row_id(a))
            self.assertEqual(len(res.read_rows(p)), 51)
            self.assertEqual(res.verify(p), [])

    def test_a_malformed_item_writes_nothing_at_all(self) -> None:
        """Validation runs before the lock, so a bad item cannot leave a partial run."""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "l.jsonl"
            good = [{"url": f"https://example.net/{i}"} for i in range(5)]
            with self.assertRaises(ValueError):
                res.append_many(good + [{"url": "https://example.net/x", "kind": "note"}],
                                path=p)
            self.assertEqual(res.read_rows(p), [], "a rejected batch left rows behind")

    def test_an_empty_batch_is_a_no_op(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "l.jsonl"
            self.assertEqual(res.append_many([], path=p), [])
            self.assertFalse(p.exists())

    def test_a_batch_and_a_single_append_produce_the_same_chain(self) -> None:
        """The fast path must not be a different format from the slow one."""
        with tempfile.TemporaryDirectory() as tmp:
            one, many = Path(tmp) / "a.jsonl", Path(tmp) / "b.jsonl"
            urls = [f"https://example.net/{i}" for i in range(6)]
            for u in urls:
                res.append(url=u, ts="2026-07-29T00:00:00Z", path=one)
            res.append_many([{"url": u, "ts": "2026-07-29T00:00:00Z"} for u in urls],
                            path=many)
            self.assertEqual([r["hash"] for r in res.read_rows(one)],
                             [r["hash"] for r in res.read_rows(many)])


if __name__ == "__main__":
    unittest.main()
