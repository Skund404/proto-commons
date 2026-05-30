#!/usr/bin/env python3
"""
§9.9 cross-implementation normalization gate — Python reference.

Reimplements the Proto-Commons Record Format §6.3 key-normalization pipeline:

    NFC  ->  Unicode case fold  ->  NFC  ->  whitespace-collapse  ->  trim

and checks it against the shared vectors in `fixtures/normalization-vectors.json`.
This is the Python side of the cross-impl determinism gate (§9.9): the Go side
runs in commons-tool (`internal/indexer/NormalizeKey` + `normalize_test.go`)
against a byte-identical copy of the same fixture. If `str.casefold()` +
`unicodedata` ever diverges from Go's `golang.org/x/text/cases.Fold`, this fails.

`str.casefold()` is Unicode full case folding (CaseFolding.txt C+F mappings) —
NOT `str.lower()`, which is a 1:1 mapping that diverges on e.g. U+0130 and ß.

Exit 0 when every vector matches; exit 1 on any divergence. Stdlib only.
"""
from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path


def normalize_key(s: str) -> str:
    """Mirror of commons-tool's Go NormalizeKey (internal/indexer/indexer.go)."""
    nfc = unicodedata.normalize("NFC", s)
    folded = nfc.casefold()
    refolded = unicodedata.normalize("NFC", folded)
    # str.split() with no args splits on runs of (Unicode) whitespace and trims
    # the ends — the Python equivalent of Go's strings.Fields + Join(" ").
    return " ".join(refolded.split())


def code_points(s: str) -> list[str]:
    return ["%04x" % ord(ch) for ch in s]


def main() -> int:
    fixture = Path(__file__).resolve().parent.parent / "fixtures" / "normalization-vectors.json"
    data = json.loads(fixture.read_text(encoding="utf-8"))
    vectors = data["vectors"]

    failures = 0
    for v in vectors:
        got = code_points(normalize_key(v["input"]))
        want = [cp.lower() for cp in v["expected"]]
        ok = got == want
        if not ok:
            failures += 1
        print(f"  [{'ok' if ok else 'FAIL'}] {v['name']}: got {got} want {want}")

    print(f"\ntest_normalize: {len(vectors)} vector(s), {failures} failure(s)")
    if failures:
        print("§9.9 cross-impl gate FAILED — Python normalization diverged from the vectors.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
