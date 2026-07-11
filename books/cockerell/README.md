# Bookbinding and the Care of Books (Douglas Cockerell, 1901)

Douglas Cockerell's *Bookbinding and the Care of Books* (first published 1901; this corpus is built from the scanned 1902 D. Appleton edition on the [Internet Archive](https://archive.org/details/bookbindingcareo00cockrich)) translated into typed, content-addressed OPG-L records. The book is in the public domain; the records are published under CC-BY-4.0 like everything else in this commons.

## What is here

**223 records**, one per material, technique, tool, or workflow the manual describes:

| Kind | Count |
|---|---|
| Techniques | 86 |
| Materials | 66 |
| Tools | 56 |
| Workflows | 15 |

Each record lives as a flat JSON file under [`primitives/`](../../primitives/) and carries:

- a **page-level citation** in `properties.source_ref` pointing into the Internet Archive scan (for example, *Chapter VII, p. 98*), so every record can be checked against the source;
- **typed relationships** to the other records it depends on (a sewing technique references the sewing frame it uses and the tape and thread it consumes), each pinned by content hash;
- lineage state `unasserted`: these are documentary records derived from a text, not attestations of practice. Anyone can fork a record and assert it against their own work.

## How to browse

- [`indexes/bundles/cockerell.json`](../../indexes/bundles/cockerell.json) is the master bundle for the full book.
- `indexes/bundles/cockerell-i.json` through `cockerell-xx*.json` are per-chapter bundles.
- [`metafile.json`](metafile.json) in this folder maps passages of the book text to the records they mention, chapter by chapter, so a reader of the book can jump from a phrase like "sewn on tapes" to the typed record behind it.

A sample record to start with: [`primitives/techniques/sewing-on-tapes.json`](../../primitives/techniques/sewing-on-tapes.json).

## How it was made

The translation from prose to records was machine-assisted and maintainer-reviewed, then validated against the OPG-L 0.6 schema and this repository's contribution checks. Corrections are welcome; see [`CONTRIBUTING.md`](../../CONTRIBUTING.md).
