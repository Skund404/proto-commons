# `contributions/incoming/`

This is the **staging area for multi-record contributions** — closures and
bundles shipped from HideSync's *Publish to Commons* action.

A single primitive PRs straight into the canonical tree
(`primitives/<kind>s/<slug>.json`). But a **closure** (a primitive plus its
definitional dependencies) or a **bundle** (a curated set + its members) is one
file containing a JSON **array** of records — which can't live one-per-file under
`primitives/`. Those land here instead, as `contributions/incoming/<slug>.json`.

## What lands here

- A JSON array of Proto-Commons records: either a dependency **closure**
  (the root primitive followed by each definitional dependency), or a
  **bundle** record (`record_class: "bundle"`) followed by its member primitives.
- Records are in commons wire shape (the same shape `commons-export` emits).

## What happens to it

A maintainer's tool (commons-tool **intake**) reads an `incoming/<slug>.json`
file and **explodes** it into the canonical layout — each primitive to
`primitives/<kind>s/<slug>.json`, each bundle to
`indexes/bundles/<slug>.json` — then rebuilds the `resolve` / `taxonomy`
indexes. **The maintainer holds canonical write authority**: CI here is
*advisory only* (it validates and reports; it never rebuilds indexes or commits).
Once exploded, the staged file is removed.

## Don't

- Don't hand-edit the canonical `primitives/` or `indexes/` from a file dropped
  here — the maintainer's intake does that.
- Don't expect indexes to update from a PR to this folder; that's a local,
  maintainer-run step.
