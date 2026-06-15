#!/usr/bin/env python3
"""
generate-indexes.py — reference implementation of the OPG-L 0.6 Index &
Bundle Data-Format Addendum 1.0 (see _Processes/opg-l-index-bundle-addendum.md).

Inputs (authored):
  indexes/categories/<id>.json   the taxonomy skeleton (index-native nodes)
  primitives/**/*.json           OPG-L records; each may carry properties.taxonomy
  indexes/bundles/*.json          authored bundles (validated, not regenerated)

Outputs (derived — a query cache; never hand-edit):
  indexes/manifest.json            format_version + language set + shards
  indexes/resolve/<lang>.json      cross-lingual lookup (denormalized entries)
  indexes/taxonomy/<lang>.json     rendered tree (skeleton + attached primitives)
  indexes/catalog/<lang>.json      thin list/card/facet rows (no manifest fetch)
  indexes/catalog/bundles/<lang>.json  thin bundle list rows
    (catalog contract: docs/internal/design-commons-catalog-index.md §1)

The Go port lives in opg-core/cmd/commons-reindex/.
"""

import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

MOCK_ROOT = Path(__file__).resolve().parent.parent
PRIMITIVES_DIR = MOCK_ROOT / "primitives"
INDEXES_DIR = MOCK_ROOT / "indexes"
CATEGORIES_DIR = INDEXES_DIR / "categories"
RESOLVE_DIR = INDEXES_DIR / "resolve"
TAXONOMY_DIR = INDEXES_DIR / "taxonomy"
BUNDLES_DIR = INDEXES_DIR / "bundles"
CATALOG_DIR = INDEXES_DIR / "catalog"
MANIFEST_PATH = INDEXES_DIR / "manifest.json"

FORMAT_VERSION = "1.0"
DEFAULT_LANG = "en"


# ---------------------------------------------------------------- normalization

def normalize_key(s: str) -> str:
    """Resolution-index key contract (addendum §A.6).

    NFC -> Unicode full case fold (CaseFolding.txt) -> NFC -> whitespace-collapse
    -> trim. Case folding (not locale lower()) is what makes the key
    cross-implementation deterministic; the second NFC reconciles fold-expansion.
    Pinned byte-for-byte by fixtures/normalization-vectors.json.
    """
    nfc = unicodedata.normalize("NFC", s)
    folded = nfc.casefold()
    refolded = unicodedata.normalize("NFC", folded)
    return " ".join(refolded.split())


# ---------------------------------------------------------------------- loading

def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_categories() -> dict[str, dict]:
    """{id: category}. Each category is its own file."""
    cats: dict[str, dict] = {}
    if not CATEGORIES_DIR.exists():
        return cats
    for path in sorted(CATEGORIES_DIR.glob("*.json")):
        c = load_json(path)
        cats[c["id"]] = c
    return cats


def walk_primitives() -> list[dict]:
    """[{primitive, path}]."""
    results = []
    for path in sorted(PRIMITIVES_DIR.rglob("*.json")):
        results.append(
            {"primitive": load_json(path), "path": path.relative_to(MOCK_ROOT).as_posix()}
        )
    return results


def observed_languages(categories: dict[str, dict], corpus: list[dict]) -> list[str]:
    langs: set[str] = set()
    for c in categories.values():
        langs.update(c.get("names", {}).keys())
    for item in corpus:
        langs.update(item["primitive"].get("properties", {}).get("names", {}).keys())
    return sorted(langs)


def load_bundles() -> dict[str, dict]:
    """{filename: bundle}. Authored bundle records (validated, not regenerated)."""
    bundles: dict[str, dict] = {}
    if not BUNDLES_DIR.exists():
        return bundles
    for bp in sorted(BUNDLES_DIR.glob("*.json")):
        bundles[bp.name] = load_json(bp)
    return bundles


def localized(names_map: dict, top_name, fallback_id: str, lang: str) -> str:
    """Localized display name: active lang -> default (en) -> top_name/id."""
    if names_map.get(lang):
        return names_map[lang][0]
    if names_map.get(DEFAULT_LANG):
        return names_map[DEFAULT_LANG][0]
    return top_name or fallback_id


_MD_IMG = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_MD_CHIP = re.compile(r"\[\[[^\]:]+:([^\]]+)\]\]")
_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")


def desc_snippet(md: str, limit: int = 200) -> str:
    """Plaintext, markdown-stripped, truncated snippet for the catalog list path
    (matches the frontend card preview, which renders plaintext). Strips images,
    [[Type:slug]] chips (-> prettified slug), [text](url) links (-> text),
    headers, blockquotes, and emphasis/code marks; collapses whitespace; truncates
    on a word boundary near `limit`."""
    if not md:
        return ""
    s = _MD_IMG.sub(r"\1", md)
    s = _MD_CHIP.sub(lambda m: m.group(1).replace("-", " ").replace("_", " "), s)
    s = _MD_LINK.sub(r"\1", s)
    s = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", s)   # ATX headers
    s = re.sub(r"(?m)^\s{0,3}>\s?", "", s)        # blockquotes
    s = re.sub(r"[*_`]+", "", s)                   # emphasis / inline code
    s = " ".join(s.split())
    if len(s) > limit:
        s = s[:limit].rsplit(" ", 1)[0] + "…"
    return s


# ------------------------------------------------------------------- validation

def validate_skeleton(categories: dict[str, dict]) -> list[str]:
    """specializes/related targets resolve; specializes forms a forest (no cycle)."""
    errors: list[str] = []
    for cid, c in categories.items():
        parent = c.get("specializes")
        if parent is not None and parent not in categories:
            errors.append(f"category {cid}: specializes-parent '{parent}' not found")
        for r in c.get("related", []):
            if r not in categories:
                errors.append(f"category {cid}: related target '{r}' not found")
    # Forest / cycle detection over specializes.
    for cid in categories:
        seen: set[str] = set()
        cur = cid
        while cur in categories and categories[cur].get("specializes") is not None:
            cur = categories[cur]["specializes"]
            if cur in seen or cur == cid:
                errors.append(f"specializes cycle detected through {cid}")
                break
            seen.add(cur)
    return errors


def validate_membership(categories: dict[str, dict], corpus: list[dict]) -> list[str]:
    errors: list[str] = []
    for item in corpus:
        p = item["primitive"]
        tax = p.get("properties", {}).get("taxonomy")
        if tax is not None and tax not in categories:
            errors.append(f"{p['slug']}: properties.taxonomy '{tax}' is not a known category")
    return errors


def validate_bundles(corpus: list[dict]) -> list[str]:
    errors: list[str] = []
    if not BUNDLES_DIR.exists():
        return errors
    primitive_hashes = {i["primitive"]["content_hash"] for i in corpus}

    bundles: dict[str, dict] = {}
    for bp in sorted(BUNDLES_DIR.glob("*.json")):
        bundles[bp.name] = load_json(bp)
    bundle_hashes = {b.get("content_hash") for b in bundles.values()}

    for name, b in bundles.items():
        if b.get("record_class") != "bundle":
            errors.append(f"{name}: record_class != 'bundle'")
        if b.get("state") not in ("open", "closed"):
            errors.append(f"{name}: state must be 'open' or 'closed'")
        for i, it in enumerate(b.get("items", [])):
            rc = it.get("record_class", "primitive")
            h = it.get("hash")
            if rc == "primitive":
                if h not in primitive_hashes:
                    errors.append(f"{name}: item[{i}] pins unknown primitive {h} ({it.get('slug')})")
            elif rc == "bundle":
                if h not in bundle_hashes:
                    errors.append(f"{name}: item[{i}] nests unknown bundle {h} ({it.get('slug')})")
            else:
                errors.append(f"{name}: item[{i}] has unknown record_class '{rc}'")
        # successors[] is append-only + advisory; targets may be future/external (not checked).
    return errors


# ----------------------------------------------------------------------- resolve

def build_resolve(categories: dict[str, dict], corpus: list[dict]) -> dict[str, dict]:
    """{lang: {key: [entry, ...]}}. Denormalized, self-sufficient entries."""
    by_lang: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))

    def add(names_map: dict, lang_seen_key, make_entry):
        for lang, name_list in names_map.items():
            seen: set[str] = set()
            for i, name in enumerate(name_list):
                key = normalize_key(name)
                if not key or key in seen:  # skip empty + de-dup within record+lang
                    continue
                seen.add(key)
                by_lang[lang][key].append(make_entry(lang, name, i == 0))

    for cid, c in categories.items():
        add(c.get("names", {}), None, lambda lang, name, canon, cid=cid: {
            "ref": f"categories/{cid}", "class": "category", "kind": None,
            "name": name, "lang": lang, "canonical": canon,
        })
    for item in corpus:
        p = item["primitive"]
        names = p.get("properties", {}).get("names", {})
        add(names, None, lambda lang, name, canon, item=item, p=p: {
            "ref": item["path"], "class": "primitive", "kind": p["kind"],
            "name": name, "lang": lang, "canonical": canon,
        })

    out: dict[str, dict] = {}
    for lang in sorted(by_lang):
        entries: dict[str, list] = {}
        for key in sorted(by_lang[lang]):
            lst = sorted(
                by_lang[lang][key],
                key=lambda e: (e["ref"], e["lang"], not e["canonical"], e["name"]),
            )
            entries[key] = lst
        out[lang] = {"format_version": FORMAT_VERSION, "entries": entries}
    return out


# ---------------------------------------------------------------------- taxonomy

def build_taxonomy(categories: dict[str, dict], corpus: list[dict], langs: list[str]) -> dict[str, dict]:
    children_of: dict[str, list[str]] = defaultdict(list)
    roots: list[str] = []
    for cid, c in categories.items():
        parent = c.get("specializes")
        if parent is None:
            roots.append(cid)
        else:
            children_of[parent].append(cid)

    related_of: dict[str, set[str]] = defaultdict(set)
    for cid, c in categories.items():
        for r in c.get("related", []):
            related_of[cid].add(r)
            related_of[r].add(cid)  # surfaced both ways

    members_of: dict[str, list[dict]] = defaultdict(list)
    for item in corpus:
        tax = item["primitive"].get("properties", {}).get("taxonomy")
        if tax is not None:
            members_of[tax].append(item)

    def ordered_children(cid: str) -> list[str]:
        kids = children_of.get(cid, [])
        order = categories[cid].get("child_order", [])
        listed = [k for k in order if k in kids]
        rest = sorted(k for k in kids if k not in listed)
        return listed + rest  # neutral (id) order; child_order curates ahead of it

    def member_refs(cid: str, lang: str) -> list[dict]:
        out = []
        for item in sorted(members_of.get(cid, []), key=lambda i: i["primitive"]["slug"]):
            p = item["primitive"]
            names = p.get("properties", {}).get("names", {})
            out.append({
                "ref": item["path"], "slug": p["slug"], "kind": p["kind"],
                "name": localized(names, p.get("name"), p["slug"], lang),
            })
        return out

    def node(cid: str, parent: str | None, lang: str) -> dict:
        c = categories[cid]
        return {
            "id": cid,
            "name": localized(c.get("names", {}), None, cid, lang),
            "parent": parent,
            "members": member_refs(cid, lang),
            "related": sorted(related_of.get(cid, set())),
            "children": [node(k, cid, lang) for k in ordered_children(cid)],
        }

    out: dict[str, dict] = {}
    for lang in langs:
        tree = {f"category/{cid}": node(cid, None, lang) for cid in sorted(roots)}
        out[lang] = {"format_version": FORMAT_VERSION, "tree": tree}
    return out


# ------------------------------------------------------------------------ catalog
# The catalog index carries exactly what the HideSync /commons list path needs
# (card + Structure rail + facets) so it never fetches a full manifest. Contract:
# docs/internal/design-commons-catalog-index.md §1. `generated_at` is DERIVED from
# the corpus (latest `modified`), NOT a wall clock, so the file stays byte-stable
# and the --dry-run idempotency gate holds.

CATALOG_VERSION = 1


def corpus_generated_at(corpus: list[dict]) -> str:
    dates = [i["primitive"].get("modified") for i in corpus if i["primitive"].get("modified")]
    return f"{max(dates) if dates else '1970-01-01'}T00:00:00Z"


def build_catalog(corpus: list[dict], langs: list[str]) -> dict[str, dict]:
    gen_at = corpus_generated_at(corpus)
    out: dict[str, dict] = {}
    for lang in langs:
        rows = []
        for item in sorted(corpus, key=lambda i: i["primitive"]["slug"]):
            p = item["primitive"]
            names = p.get("properties", {}).get("names", {})
            tags = p.get("tags", []) or []
            row = {
                "slug": p["slug"],
                "kind": p["kind"],
                "name": localized(names, p.get("name"), p["slug"], lang),
                "domain": tags[0] if tags else None,
                "taxonomy": p.get("properties", {}).get("taxonomy"),
                "tags": tags,
                "descSnippet": desc_snippet(p.get("description", "")),
                "forks": 0,  # commons records carry no fork count
                "updated": p.get("modified"),
                "hash": p.get("content_hash"),
                "path": item["path"],
                "lineageState": (p.get("lineage") or {}).get("provenance_state"),
            }
            # Linked product image (top-level imageUrl; branded exemplars only).
            # Hotlinked URL, included only when present so other rows stay thin.
            if p.get("imageUrl"):
                row["imageUrl"] = p["imageUrl"]
            rows.append(row)
        out[lang] = {"version": CATALOG_VERSION, "generated_at": gen_at,
                     "count": len(rows), "shards": None, "records": rows}
    return out


def build_bundle_catalog(bundles: dict[str, dict], langs: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for lang in langs:
        rows = []
        for name in sorted(bundles):
            b = bundles[name]
            nm = b.get("name", {}) or {}
            dm = b.get("description", {}) or {}
            counts = Counter(it.get("role") for it in b.get("items", []) if it.get("role"))
            roles = {r: counts[r] for r in ("required", "recommended", "optional") if counts.get(r)}
            tags = b.get("tags", []) or []
            rows.append({
                "slug": b["slug"],
                "name": nm.get(lang) or nm.get(DEFAULT_LANG) or b["slug"],
                "descSnippet": desc_snippet(dm.get(lang) or dm.get(DEFAULT_LANG) or ""),
                "domain": b.get("domain") or (tags[0] if tags else None),
                "taxonomy": b.get("taxonomy"),
                "itemCount": len(b.get("items", [])),
                "state": b.get("state"),
                "roles": roles,
                "updated": b.get("modified"),  # bundles carry no date today -> null
                "hash": b.get("content_hash"),
            })
        out[lang] = {"version": CATALOG_VERSION, "count": len(rows), "bundles": rows}
    return out


def validate_catalog(categories: dict[str, dict], bundles: dict[str, dict]) -> list[str]:
    """Bundle taxonomy ids must resolve to a known category (or be null)."""
    errors: list[str] = []
    for name, b in bundles.items():
        tax = b.get("taxonomy")
        if tax is not None and tax not in categories:
            errors.append(f"{name}: bundle taxonomy '{tax}' is not a known category")
    return errors


def assert_snippets_plain(*catalogs: dict[str, dict]) -> list[str]:
    """Guard: no residual markdown link/chip syntax leaked into descSnippet."""
    errors: list[str] = []
    for cat in catalogs:
        for lang, obj in cat.items():
            for row in obj.get("records", obj.get("bundles", [])):
                s = row.get("descSnippet", "")
                if "](" in s or "[[" in s:
                    errors.append(f"catalog[{lang}] {row['slug']}: descSnippet has residual markdown")
    return errors


# -------------------------------------------------------------------------- io

def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n" pins LF on every platform — without it, text mode on Windows
    # rewrites "\n" to "\r\n", which diverges from the Go reindexer (always LF)
    # and breaks byte-for-byte index parity across implementations.
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, sort_keys=False)
        f.write("\n")


def diff(generated: dict, path: Path) -> str | None:
    if not path.exists():
        return f"{path.relative_to(MOCK_ROOT)} (missing)"
    if load_json(path) != generated:
        return str(path.relative_to(MOCK_ROOT))
    return None


def main() -> int:
    dry_run = "--dry-run" in sys.argv

    categories = load_categories()
    corpus = walk_primitives()
    bundles = load_bundles()
    print(f"Loaded {len(categories)} categories, {len(corpus)} primitives, {len(bundles)} bundles")

    errs: list[str] = []
    errs += validate_skeleton(categories)
    errs += validate_membership(categories, corpus)
    errs += validate_bundles(corpus)
    errs += validate_catalog(categories, bundles)
    if errs:
        for e in errs:
            print(f"  ERROR: {e}")
        return 1
    print("  skeleton, membership, bundles, and catalog validate")

    langs = observed_languages(categories, corpus)
    manifest = {
        "format_version": FORMAT_VERSION,
        "languages": langs,
        "shards": [{"id": "main", "path": "."}],
    }
    resolve = build_resolve(categories, corpus)
    taxonomy = build_taxonomy(categories, corpus, langs)
    catalog = build_catalog(corpus, langs)
    bundle_catalog = build_bundle_catalog(bundles, langs)
    print(f"  languages: {', '.join(langs)}")

    snip_errs = assert_snippets_plain(catalog, bundle_catalog)
    if snip_errs:
        for e in snip_errs:
            print(f"  ERROR: {e}")
        return 1

    if dry_run:
        diverged = [d for d in [diff(manifest, MANIFEST_PATH)] if d]
        for lang, obj in resolve.items():
            d = diff(obj, RESOLVE_DIR / f"{lang}.json")
            if d:
                diverged.append(d)
        for lang, obj in taxonomy.items():
            d = diff(obj, TAXONOMY_DIR / f"{lang}.json")
            if d:
                diverged.append(d)
        for lang, obj in catalog.items():
            d = diff(obj, CATALOG_DIR / f"{lang}.json")
            if d:
                diverged.append(d)
        for lang, obj in bundle_catalog.items():
            d = diff(obj, CATALOG_DIR / "bundles" / f"{lang}.json")
            if d:
                diverged.append(d)
        if diverged:
            print("  DIVERGED:")
            for d in diverged:
                print(f"    {d}")
            return 2
        print("  all derived indexes match committed versions")
        return 0

    write_json(MANIFEST_PATH, manifest)
    for lang, obj in resolve.items():
        write_json(RESOLVE_DIR / f"{lang}.json", obj)
    for lang, obj in taxonomy.items():
        write_json(TAXONOMY_DIR / f"{lang}.json", obj)
    for lang, obj in catalog.items():
        write_json(CATALOG_DIR / f"{lang}.json", obj)
    for lang, obj in bundle_catalog.items():
        write_json(CATALOG_DIR / "bundles" / f"{lang}.json", obj)
    print(f"  wrote manifest + resolve/ + taxonomy/ + catalog/ for {len(langs)} languages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
