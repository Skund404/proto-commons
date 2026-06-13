#!/usr/bin/env python3
"""
Advisory structural validator for Proto-Commons contributions.

Checks primitive and bundle records under `contributions/incoming/`,
`primitives/`, and `indexes/bundles/` against the structural shape the canonical
maintainer tooling (commons-tool) enforces — WITHOUT writing anything back (no
index rebuild, no commit, no canonicalization). Pre-Foundation the commons
deliberately accepts messy content (no central authority), so this gate is
*advisory*:

  - HARD errors (unparseable JSON, missing identity, wrong record class) exit
    non-zero so a contributor gets clear PR feedback.
  - Softer issues (license, hash format, non-URL media, lineage floor) are
    warnings — the maintainer's tool fixes these on canonical intake.

The maintainer adjudicates every contribution and runs the canonical
explosion + indexing locally (`commons` verify-mock / intake). This script never
mutates the repo.

Stdlib only; runs on any Python 3.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

KINDS = {"tool", "material", "technique", "workflow", "project", "event"}
ROLES = {"required", "recommended", "optional"}
SLUG_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

ROOT = pathlib.Path(__file__).resolve().parents[1]

errors: list[str] = []
warnings: list[str] = []


def err(where: str, msg: str) -> None:
    errors.append(f"{where}: {msg}")


def warn(where: str, msg: str) -> None:
    warnings.append(f"{where}: {msg}")


def is_url(s) -> bool:
    return isinstance(s, str) and (s.startswith("http://") or s.startswith("https://"))


def valid_slug(s) -> bool:
    return isinstance(s, str) and len(s) <= 64 and bool(SLUG_RE.match(s))


def validate_primitive(where: str, rec: dict) -> None:
    if rec.get("kind") not in KINDS:
        err(where, f"kind {rec.get('kind')!r} not in the six closed kinds {sorted(KINDS)}")
    if not valid_slug(rec.get("slug")):
        err(where, f"slug {rec.get('slug')!r} must be kebab-case (<=64 chars)")
    if not rec.get("name"):
        err(where, "name: required")

    ch = rec.get("content_hash")
    if ch is not None and not HASH_RE.match(str(ch)):
        warn(where, f"content_hash {ch!r} is not sha256:<64 hex> (tooling recomputes it canonically)")

    props = rec.get("properties") or {}
    if props.get("license") != "CC-BY-4.0":
        warn(where, "properties.license should be CC-BY-4.0")
    for k in ("imageUrl", "mediaRef"):
        v = props.get(k)
        if isinstance(v, str) and v and not is_url(v):
            warn(where, f"properties.{k} is not a public URL — embedded/local media is stripped on publish")
    items = props.get("mediaItems")
    if isinstance(items, list):
        for it in items:
            u = (it or {}).get("imageUrl") or (it or {}).get("url")
            if u and not is_url(u):
                warn(where, "properties.mediaItems has non-URL media — stripped on publish")

    lin = rec.get("lineage")
    if isinstance(lin, dict) and ("provenance_state" not in lin or "outcome" not in lin):
        warn(where, "lineage missing provenance_state/outcome (the lineage floor is injected by tooling)")


def validate_bundle(where: str, rec: dict) -> None:
    if not valid_slug(rec.get("slug")):
        err(where, f"bundle slug {rec.get('slug')!r} must be kebab-case")
    items = rec.get("items")
    if not isinstance(items, list) or not items:
        err(where, "bundle items: must be a non-empty array")
        return
    for i, it in enumerate(items):
        it = it or {}
        rc = it.get("record_class")
        if rc == "primitive":
            if it.get("kind") not in KINDS:
                err(where, f"items[{i}].kind {it.get('kind')!r} not in the six closed kinds")
            if not it.get("slug"):
                err(where, f"items[{i}].slug: required")
            if it.get("hash") and not HASH_RE.match(str(it["hash"])):
                warn(where, f"items[{i}].hash is not sha256:<64 hex>")
        elif rc == "bundle":
            # Nested bundle (kit-of-kits) — pinned by slug + hash, no kind.
            if not valid_slug(it.get("slug")):
                err(where, f"items[{i}].slug {it.get('slug')!r} must be kebab-case (nested bundle ref)")
            if it.get("hash") and not HASH_RE.match(str(it["hash"])):
                warn(where, f"items[{i}].hash is not sha256:<64 hex>")
        elif "target" in it:
            # HideSync authoring shape (nested target + note); the maintainer
            # intake maps it to the canonical flat item.
            warn(where, f"items[{i}] uses the authoring shape (target/note) — intake maps it to the canonical flat item")
        else:
            err(where, f"items[{i}]: needs record_class:'primitive' (+kind, slug, hash) or a target ref")
        role = it.get("role")
        if role is not None and role not in ROLES:
            warn(where, f"items[{i}].role {role!r} not in {{required, recommended, optional}}")


def validate_record(where: str, rec) -> None:
    if not isinstance(rec, dict):
        err(where, "not a JSON object")
        return
    if rec.get("record_class") == "bundle":
        validate_bundle(where, rec)
    else:
        validate_primitive(where, rec)


def validate_file(path: pathlib.Path) -> None:
    rel = path.relative_to(ROOT).as_posix()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        err(rel, f"unparseable JSON: {e}")
        return
    # A contribution file may be a single record, a closure array, or a
    # bundle-plus-members array (the HideSync ship shapes).
    if isinstance(data, list):
        for i, rec in enumerate(data):
            validate_record(f"{rel}[{i}]", rec)
    else:
        validate_record(rel, data)


def main() -> int:
    targets: list[pathlib.Path] = []
    for pat in (
        "contributions/incoming/**/*.json",
        "primitives/**/*.json",
        "indexes/bundles/**/*.json",
    ):
        targets += sorted(ROOT.glob(pat))
    if not targets:
        print("validate-contributions: no records found to validate.")
        return 0

    for p in targets:
        validate_file(p)

    for w in warnings:
        print(f"WARN   {w}")
    for e in errors:
        print(f"ERROR  {e}")
    print(
        f"\nvalidate-contributions: {len(targets)} file(s) | "
        f"{len(errors)} error(s) | {len(warnings)} warning(s)"
    )
    if errors:
        print("Advisory gate: hard errors found. A maintainer may still merge "
              "and fix on canonical intake — but please address these if you can.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
