# Contributing to the Proto-Commons

Thank you for helping grow the Proto-Commons. There are two ways to contribute, designed so a GitHub account is not required to participate.

## Two paths

### Path A — Suggest (no GitHub required)

If you'd like to flag a gap, propose a primitive, send a correction, or share an "I made this" post, drop it in either community channel:

- **Discord:** *[invite forthcoming]*
- **Reddit:** *[community forthcoming]*

A maintainer will pick it up, either authoring the primitive on your behalf (with attribution preserved) or pointing you at Path B if you'd like to author it yourself. No deadlines, no formatting requirements — just describe what's missing or what you'd like to add.

### Path B — Publish via GitHub

The intended on-ramp is HideSync's **Publish to Commons** action, which builds a conforming manifest, shows a consent preview, copies the JSON to your clipboard, and opens the right "create new file" page on GitHub. *(Forthcoming — ships post-seed.)*

You can also hand-author a primitive directly:

1. Read the Proto-Commons Record Format Specification (link forthcoming).
2. Write a record at `primitives/<kind>s/<slug>.json` per the spec — a flat file
   in the plural-kind directory (e.g. `primitives/techniques/saddle-stitch.json`,
   `primitives/materials/chrome-veg-tan.json`).
3. Open a PR. An advisory CI check runs structural + content-hash validation
   (see *Validation* below). A maintainer reviews.

### Closures and bundles → `contributions/incoming/`

A single primitive PRs straight into the canonical tree above. But a **closure**
(a primitive plus its definitional dependencies) or a **bundle** (a curated set
plus its members) is one file containing a JSON **array** of records, which
can't live one-per-file under `primitives/`. HideSync's *Publish to Commons*
action ships these as a single `contributions/incoming/<slug>.json`.

A maintainer's tool then **explodes** that file into the canonical layout — each
primitive to `primitives/<kind>s/<slug>.json`, each bundle to
`indexes/bundles/<slug>.json` — and rebuilds the derived indexes. You don't
hand-place the canonical files for a closure/bundle; you drop the array in
`incoming/` and the maintainer's intake does the rest. See
[`contributions/incoming/`](contributions/incoming/README.md).

### Validation (advisory)

CI runs an **advisory** structural validator
([`scripts/validate_contributions.py`](scripts/validate_contributions.py)) over
`contributions/incoming/`, `primitives/`, and `indexes/bundles/`. It checks the
record shape the canonical tooling expects (kinds, kebab slugs, hash format,
URL-only media, bundle items) and **reports** — it never rebuilds indexes or
commits. Pre-Foundation the commons accepts messy content with no central
authority, so this gate does not block: a maintainer holds canonical write
authority, adjudicates each contribution, and runs the canonical
explosion + indexing locally. Clear validation feedback just helps you get a
contribution right before a maintainer picks it up.

## What gets published

The Proto-Commons admits **OPG-L semantic primitives only**. Specifically:

- Six primitive kinds — `tool`, `material`, `technique`, `workflow`, `project`, `event`.
- **Media references by URL only.** Embedded media (`storage_mode: copy` or `link`) is rejected at publish and stays in your local install.
- All content licensed **CC-BY-4.0**, irrevocably, publicly.

Curatorial bundles (`indexes/bundles/<slug>.json`) follow a related but distinct format; see the spec.

## Link-rot disclaimer

URL media references are accepted as a pre-Foundation tradeoff for keeping the commons lightweight. Links may break over time; we do not guarantee snapshotting or caching at this stage. A Foundation-hosted snapshot/cache policy is on the roadmap.

## Review timeline

Pre-launch there is **no review SLA**. Maintainers are pseudonymous practitioners and review PRs when capacity allows. Approved PRs merge to `main`; rejected PRs close with a maintainer comment explaining why. If your PR sits without feedback, a friendly nudge in the Discord channel is welcome.

## Code of conduct

Be useful, be specific, and be kind. Disagreements about technique, attribution, taxonomy, or scope are expected and are part of a healthy commons — keep them about the work, not the contributor. Maintainers may close threads or reject contributions that target people rather than primitives. Repeated bad-faith behaviour leads to a ban from contributing.

## License agreement

By submitting a PR to this repository, **you agree that your contribution is released under the [Creative Commons Attribution 4.0 International License](LICENSE) (CC-BY-4.0)**. This release is **irrevocable and public**. You confirm that you have the right to release the content under this license. Attribution to you (or whatever identifier you choose to use) is preserved in the record's `operators[]` or `properties.suggested_by` field, per the OPG-L spec.

If you have any questions before submitting, ask in Discord or open an issue first.
