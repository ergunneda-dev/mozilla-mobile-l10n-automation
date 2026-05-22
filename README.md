# Mozilla mobile l10n automation

> Placeable consistency audits for Mozilla's mobile localization repositories — Firefox for Android (Fenix) and Firefox for iOS. Two Python scripts, same three-category framework as my [desktop Firefox project](https://github.com/ergunneda-dev/mozilla-l10n-automation), applied to `strings.xml` and XLIFF.

May 2026 · [scripts](./scripts) · [analyses](#highlights-from-the-real-data-runs) · [live CI](./.github/workflows) · sample data for smoke-testing

---

## What's in here

| Path | Purpose |
|---|---|
| [`scripts/check_placeables_android.py`](./scripts/check_placeables_android.py) | Walks `mozilla-l10n/android-l10n`, pairs `values/strings.xml` with `values-<locale>/strings.xml`, reports placeable mismatches |
| [`scripts/check_placeables_ios.py`](./scripts/check_placeables_ios.py) | Walks `mozilla-l10n/firefoxios-l10n`, parses XLIFF, compares `<source>` and `<target>` placeables per `<trans-unit>` |
| [`.github/workflows/weekly-mobile-audit.yml`](./.github/workflows/weekly-mobile-audit.yml) | **Live CI** — runs every Monday 06:00 UTC. Clones both Mozilla repos, audits 25 locales each, commits findings to `weekly-findings/` |
| [`.github/workflows/pr-audit.yml`](./.github/workflows/pr-audit.yml) | **Live CI** — runs on every PR that touches scripts or workflows. Posts findings as a PR comment so changes can be reviewed against real-data results |
| [`weekly-findings/`](./weekly-findings) | Per-locale audit outputs committed by the weekly workflow. The slope over time is the signal — finding counts rising in a locale flag features that recently shipped |
| [`placeable-audit-android-2026-05-22.md`](./placeable-audit-android-2026-05-22.md) | Real-data analysis: 9 findings across 4 locales, categorized using the three-category framework |
| [`placeable-audit-ios-2026-05-22.md`](./placeable-audit-ios-2026-05-22.md) | Real-data analysis: 0 findings across 25 locales — and why the zero result is meaningful, not broken |
| [`android-*-findings.txt`](./android-ar-findings.txt) | Raw script output for each audited Android locale (the evidence behind the analysis) |
| [`github-actions-examples/`](./github-actions-examples) | Workflow templates designed for installation in the upstream Mozilla repos (not live on this portfolio) |
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

## Highlights from the real-data runs

**Android: 9 findings across 4 locales. iOS: 0 findings across 25.** Same audit methodology, very different result — and the contrast is the actual insight.

| Platform | Scope | Comparisons | Findings |
|---|---|---|---|
| Android | 41 source files × 25 locales | ~1,000 file pairs | **9** (ar=5, cs=2, pl=1, de=1) |
| iOS | 1 XLIFF × 25 locales | ~45,000 trans-units | **0** |

iOS is at least 4,500× cleaner per comparison unit. That isn't noise — it's a structural difference. Three independent gates catch iOS placeable bugs before they reach the audit: Apple's build-time validation, Mozilla's `firefoxios-l10n` reference-string linter, and XLIFF's `<source>`/`<target>` pairing inside each `<trans-unit>` (which lets Pontoon show translators the source placeable inline while they write the target). Android's `strings.xml` has no equivalent compile-time check, and source/translation live in separate files. Hence the findings concentrate there.

**The Arabic Tab Groups cluster is a leading indicator.** Four of the five Arabic findings are in the same recently-landed feature (Tab Groups plurals — `tab_group_tabs_count_subtitle#one` and three siblings). The pattern matches what I found in the [desktop Firefox audit](https://github.com/ergunneda-dev/mozilla-l10n-automation/blob/main/placeable-audit-2026-05-20.md) — placeable findings cluster in features that recently shipped en-US strings, before the locale team's full pass. The placeable check therefore acts as a leading indicator of which locales are running behind which features, not just a static QA tool.

**Most of the audited surface is clean.** 21 of the 25 Android locales returned 0 findings. The same locales that came up "100% complete" on the desktop side (de, ko, sv, etc.) showed clean here too. Translator communities at scale.

Full categorization and program-manager-level next steps: [Android analysis →](./placeable-audit-android-2026-05-22.md) · [iOS analysis →](./placeable-audit-ios-2026-05-22.md).

## Live CI

Two workflows actually run on this repo (not just example shapes):

- **`weekly-mobile-audit.yml`** — Monday cron. Clones `mozilla-l10n/android-l10n` and `mozilla-l10n/firefoxios-l10n` at run time, audits 25 locales on each, commits per-locale findings to `weekly-findings/YYYY-MM-DD/`. The week-over-week diff is visible as a git diff — a locale's finding count rising over time signals a feature that recently shipped new strings.
- **`pr-audit.yml`** — runs on every PR that touches `scripts/`, `.github/workflows/`, or `sample-data/`. Same clone-and-audit pattern, but posts results as a comment on the PR. Lets you change the audit code and see immediately whether it still reproduces the documented baselines.

The workflows in `github-actions-examples/` are different — those are templates for installation inside the upstream Mozilla repos themselves (`mozilla-l10n/android-l10n` and `mozilla-l10n/firefoxios-l10n`), not on this portfolio.

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
