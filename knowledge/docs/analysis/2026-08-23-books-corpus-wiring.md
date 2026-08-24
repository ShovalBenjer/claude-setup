# docs/books wired to retrieval, 2026-08-23

Point-in-time scan. Operator ask: "ensure the books/ is connected via crabrag or custom
thing we want to do" (PT-4c886956b37b), following "i have a big corpus of books, decide
what you want to do with them" (PT-a3d2f80242eb, 08-17) and the books-ingest ask
(PT-b2d0ae9b9d6a, 08-18). All three are boxes on issue #104.

## Measured before

`docs/books`: 335 files, 475 MB, gitignored. `~/.claude/corpus/books.sqlite3`: 300 files,
4,516 chunks, last built 2026-08-19. Every one of the 35 unindexed files was a non-txt:
22 PDF, 6 epub (5 of which had a txt sibling and were fine), 4 mobi, 1 djvu, 1 partial
download, 1 extensionless. The indexer read `.txt` only; books-ingest extracted epub only.
Wigderson, Grohs and Kutyniok, Carlsson's TDA book, the MARL book, Lurie's Higher Topos
Theory, and six arXiv PDFs were on disk and unreachable by any query.

## Candidates (the /diverge row lives in docs/taste.md)

| candidate | what it is | cost here | p_conventional |
|---|---|---|---|
| CrabRAG (guoyijia22) | local RAG: FastAPI backend, Bun gateway, web UI, GraphRAG, ACLs | two long-running processes with no owner; Python plus Bun runtime; its graph features answer a question nobody has asked of this corpus | 0.6 |
| RustRAG or srag | Rust MCP server, sqlite-vec, PDF via lopdf | a new binary and an embedding model; MCP surface the sessions could call | 0.3 |
| FTS5 as-is, fix the extractor | the existing skill plus pypdf | one function, zero processes, pypdf already on the system interpreter | 0.8 |

FTS5 won on measured grounds, not on principle: the gap was extraction, not retrieval
quality, and no query has yet failed for lexical reasons. The stdlib-only correction of
2026-08-13 is honoured by writing the comparison down rather than by picking the
non-stdlib option; the falsifier is a real operator query that FTS5 cannot answer and a
vector index can. When that query appears, RustRAG or srag is the next candidate, because
it adds retrieval without adding a service.

## Done

- `build_index.py` gained `extract_pdfs`: writes `<name>.pdf.txt` beside each PDF with
  none, pypdf imported lazily, unextracted PDFs counted and printed when pypdf is absent.
  Deployed to `~/.claude/skills/books-index/` in the same turn (payload and live identical,
  checked with `diff -rq`). Run: 22 PDFs extracted, 0 failed, 14,000 pages.
- The one unextracted epub (Polars guide) has a malformed manifest that ebooklib rejects;
  extracted with a tolerant zip walk instead, 33 sections, 770 KB.
- `tools/corpus/books_check.py`: the coverage oracle. Exit 1 on an unindexed txt, a txt
  changed since indexing, or a pdf/epub without text. mobi, djvu, partial downloads are
  reported, never failed. Selftest: 8 checks. Real run after the rebuild: clean, 323 txt
  indexed, 7 unextractable reported.
- Proof query: `query.py "persistent homology barcode"` returns Carlsson chunks #37, #39,
  #62, #53, #49, a book that returned nothing an hour earlier.
- Listed in AGENTS.md beside the other upkeep commands.

## Found, not fixed

- Duplicates in the corpus: the TDA book twice, Grohs and Kutyniok three times, Resonant
  Monad twice, sagemaker-api.pdf (3,953 pages of API reference that is not a book). A
  content-hash dedup in books-ingest is the next move; it would cut roughly 1,700 pages of
  repeated text from the index.
- 4 mobi, 1 djvu, 1 `.crdownload`, 1 extensionless file stay unreadable. calibre's
  `ebook-convert` handles mobi and `djvutxt` handles djvu; neither is installed.
- The check is not in the gate. CI has no docs/books, so a gate domain would be UNCOVERED
  there by construction. It runs locally, and AGENTS.md says when.
