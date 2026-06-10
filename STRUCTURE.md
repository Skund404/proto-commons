# Proto-Commons structure & organization conventions

How the corpus is arranged. **Any domain added later follows the same logic** —
leatherwork and produce are arranged identically, and the next domain must be too.

## 1. One flat file per record, per kind

Every primitive lives at exactly:

```
primitives/<kind>/<slug>.json        # kind ∈ tools materials techniques workflows projects events
```

**No domain or category sub-folders.** There is one flat directory per kind; a
record's domain and category are properties of the *record*, not of its path.

> History: the produce corpus was originally nested under
> `materials/produce/{fruits,vegetables}/` while leatherwork sat flat in
> `materials/`. That asymmetry was removed on 2026-06-10 by flattening produce —
> a pure move, see §4.

## 2. Domain = the record's first tag (`tags[0]`)

Every record opens with its **domain tag** (`leatherwork`, `produce`, …), then its
discriminators + taxonomy id, de-duplicated:

```jsonc
"tags": ["produce", "fruit", "pome-fruit"]       // domain, then narrower
"tags": ["leatherwork", "leather", "bridle-leather"]
```

Domain is **not** a folder and **not** a taxonomy root — it is a tag. Browse and
filter surfaces (e.g. HideSync's commons structure rail: *domain → kind →
category*) key off `tags[0]`. A new domain is introduced simply by using a new
first tag; nothing in the directory layout changes.

## 3. Taxonomy = a per-domain *is-a* forest

Categories (`indexes/categories/<id>.json`) form a forest via `specializes` — a
category is a **narrower kind of** its parent. Each domain contributes its own
trees:

```
produce:      pome-fruit < fruit          allium < vegetable
leatherwork:  bridle-leather < leather    cutting-knife < cutting-tool
```

A primitive declares its **leaf** category via `properties.taxonomy`; membership
in the ancestors is derived.

**Do not create a domain "root" category that materials/tools specialize.**
`specializes` means *is-a*: `fruit` is a kind of produce (fine), but `leather` is
**not** a kind of "leatherwork" — it's a material *used in* it. Domain grouping is
the job of `tags[0]` (§2), not of `specializes`. Keep the taxonomy a clean is-a
forest; let tags carry the domain.

## 4. Reorganize by moving files, never by editing bodies (hash safety)

A record's `content_hash` (RFC-8785 canonical JSON + SHA-256) is over the record
**body** — slug, kind, properties, tags, relationships — **not** its file path. So:

- **Moving a file is hash-neutral.** Relocating `primitives/.../apple.json` does
  not change its hash; only the derived `indexes/resolve` + `indexes/taxonomy`
  paths update (regenerated, never hand-edited).
- **Editing a body churns hashes.** Changing tags/taxonomy/fields changes the
  `content_hash`, which re-pins every bundle item and relationship that targets
  the record. Avoid it during a structural reorg.
- **Watch inbound `relationships[].target.path`.** Records referenced by path
  (e.g. leatherwork, whose records cite each other) **cannot** be relocated
  without re-pinning the referrers — so that churns hashes. Produce had *zero*
  inbound path refs and no relationships of its own, which is why it flattened
  churn-free. Prefer flattening the deviating domain into the canonical layout
  over relocating one that carries path references.

## Pipeline for any structural change

```
move/edit files
  → commons mint --mock <repo>          # stamps content_hash, re-pins bundle items
  → python scripts/generate-indexes.py  # rebuild manifest + resolve/ + taxonomy/, validate
  → commons mint --check                # confirm byte-canonical (expect "clean")
  → commit
```
