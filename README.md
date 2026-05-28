# Proto-Commons

A public commons of content-addressed OPG-L records — early commons content hosted on GitHub, with practitioners publishing primitives, forking primitives, and accumulating a shared graph before any Foundation-hosted infrastructure exists. The substrate is durable, audit-logged, and version-controlled; the diff model matches what OPG-L specifies natively; the choice of GitHub is deliberate signalling that openness is real even though the Foundation hasn't yet been incorporated. Seed domain is leatherworking; the format is domain-agnostic.

## Status

Pre-incorporation working commons. Migrates to Foundation-hosted commons at seed. Content addressing (RFC 8785 canonical JSON + SHA-256) makes that migration a substrate swap — record `content_hash` values are unchanged.

## Repository layout

```
primitives/
  tools/         materials/    techniques/
  workflows/     projects/     events/
indexes/
  resolve/       taxonomy/     bundles/
schema/          scripts/
LICENSE          README.md     CONTRIBUTING.md
```

- **`primitives/`** — strict OPG-L 0.6 records, six closed kinds, hash-pinned and content-addressed.
- **`indexes/resolve/`** and **`indexes/taxonomy/`** — derived JSON for navigation, regenerable from primitives.
- **`indexes/bundles/`** — curatorial groupings (starter kits) carrying `record_class: "bundle"`.
- **`schema/`** — JSON Schemas (mirrored from `opg-core`).
- **`scripts/`** — maintenance helpers.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Two paths: a no-GitHub suggestion track (Discord / Reddit) and a GitHub PR track (via HideSync's *Publish to Commons* action — forthcoming — or hand-authored JSON conforming to the record-format spec).

## Specification

The Proto-Commons Record Format Specification (Working Draft 0.1) defines the JSON shapes of primitives, bundles, and derived indexes. Specification available — link forthcoming. The format builds on **OPG-L 0.6** for primitive shape and content addressing.

## License

All content is licensed under the **Creative Commons Attribution 4.0 International License** (CC-BY-4.0). See [`LICENSE`](LICENSE). Contributions are accepted under the same license — submission is irrevocable and public.

## Acknowledgements

Powered by [OPG-L 0.6](https://github.com/) — the Open Practice Graph Language formal specification (link forthcoming).
