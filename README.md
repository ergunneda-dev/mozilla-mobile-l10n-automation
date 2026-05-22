# Mozilla mobile l10n automation

> Placeable consistency audits for Mozilla's mobile localization repositories — Firefox for Android (Fenix) and Firefox for iOS. Two Python scripts, same three-category framework as my [desktop Firefox project](https://github.com/ergunneda-dev/mozilla-l10n-automation), applied to `strings.xml` and XLIFF.

May 2026 · [scripts](./scripts) · sample data for smoke-testing

---

## What's in here

| Path | Purpose |
|---|---|
| [`scripts/check_placeables_android.py`](./scripts/check_placeables_android.py) | Walks `mozilla-l10n/android-l10n`, pairs `values/strings.xml` with `values-<locale>/strings.xml`, reports placeable mismatches |
| [`scripts/check_placeables_ios.py`](./scripts/check_placeables_ios.py) | Walks `mozilla-l10n/firefoxios-l10n`, parses XLIFF, compares `<source>` and `<target>` placeables per `<trans-unit>` |
| [`sample-data/`](./sample-data) | Tiny fixtures with intentional bugs for smoke-testing both scripts without cloning the real repos |

## Why this exists

Mozilla's mobile l10n lives in two active GitHub repos under the `mozilla-l10n` org, both wired to Pontoon and managed by the same L10n team that owns the desktop Firefox repo:

- **[`mozilla-l10n/android-l10n`](https://github.com/mozilla-l10n/android-l10n)** — cross-product Android strings (Fenix, Focus, others). 211k translated strings across 142 locale teams as of May 2026.
- **[`mozilla-l10n/firefoxios-l10n`](https://github.com/mozilla-l10n/firefoxios-l10n)** — Firefox for iOS strings. XLIFF 1.2 format, ~100 locales.

Both share Pontoon as the translator-facing tool. Different file formats — Android XML on one side, OASIS XLIFF on the other — but the *kinds of findings* an audit surfaces are the same. The point of this repo is to apply the same disciplines I used on the desktop side and show they transfer.

The disciplines:

1. **Parse, don't regex.** Both formats are XML with structure; `xml.etree.ElementTree` reads them properly. Regex on raw text would mangle `<xliff:g>` wrappers in Android and `<trans-unit>` boundaries in XLIFF.
2. **Read-only audits.** No script in this repo mutates source files. Even the smoke-test fixtures are checked in unchanged.
3. **Distinguish findings.** Not every divergence is a bug. The same three-category framework from my desktop project applies here:
    - **Category 1 — Deliberate simplifications.** A locale dropped a placeable on purpose because their language doesn't need it.
    - **Category 2 — Latent runtime UI bugs.** Translation is missing a placeable the app passes at runtime. The user sees a sentence with a hole in it.
    - **Category 3 — Stale references.** Translation references a variable that no longer exists in the source. Doesn't crash on most platforms, but should be tidied.

## How the placeable formats differ

| Concept | Fluent (desktop) | Android `strings.xml` | iOS XLIFF 1.2 |
|---|---|---|---|
| Object/string placeable | `{ $name }` | `%s`, `%1$s` | `%@`, `%1$@` |
| Integer placeable | `{ $count }` | `%d`, `%1$d` | `%d`, `%lld`, `%1$d` |
| Wrapped for translator | (selector branches) | `<xliff:g id="...">%s</xliff:g>` | inline `<source>` text |
| Term reference | `-brand-name` | (no equivalent) | (no equivalent) |
| Source / translation pairing | separate files | sibling dirs (`values/` vs `values-<locale>/`) | `<source>` and `<target>` inside same `<trans-unit>` |

Each format's quirks matter:

- **Android uses `r` prefix for region variants.** `zh-CN` is `values-zh-rCN`. `pt-BR` is `values-pt-rBR`. The script accepts the literal directory suffix to avoid hiding this.
- **XLIFF wraps untranslated units differently per tool.** Some Mozilla exports include empty `<target/>` for untranslated entries; others omit `<target>` entirely. The script treats both as "untranslated, skip" rather than "extra=[]".
- **iOS's `%lld` is one token, not `%ll` + `d`.** The placeable regex matches the longer pattern first so we don't truncate it.

## Run it yourself

```bash
# Clone both Mozilla l10n repos as siblings
git clone --depth=1 https://github.com/mozilla-l10n/android-l10n.git
git clone --depth=1 https://github.com/mozilla-l10n/firefoxios-l10n.git

# Android: pass the literal directory suffix
python3 scripts/check_placeables_android.py android-l10n tr

# iOS: pass the locale code
python3 scripts/check_placeables_ios.py firefoxios-l10n tr
```

Or smoke-test without cloning anything:

```bash
python3 scripts/check_placeables_android.py sample-data/android tr
python3 scripts/check_placeables_ios.py sample-data/ios tr
```

Each script exits 0 if no findings, 1 if findings exist — wire either into a per-PR check as a CI gate.

## Related Mozilla tooling

Mozilla's production l10n CI uses [`compare-locales`](https://hg.mozilla.org/l10n/compare-locales/) and Pontoon's own validation. The scripts here re-implement small slices to make the primitives explicit and to show the disciplines transfer across formats. For real production work, prefer those tools with the repos' own `l10n.toml` configs.

For Android specifically, the active workflow is documented in [Working with Strings](https://firefox-source-docs.mozilla.org/mobile/android/fenix/Working-with-Strings.html). For iOS, see the [string import/export process](https://github.com/mozilla-mobile/firefox-ios/wiki/Manual-string-import-and-export-process).

## See also

- [`ergunneda-dev/mozilla-l10n-automation`](https://github.com/ergunneda-dev/mozilla-l10n-automation) — the desktop Firefox companion to this repo. Same author, same three-category framework, Fluent (`.ftl`) instead of XML.

## License

[MIT](./LICENSE).
