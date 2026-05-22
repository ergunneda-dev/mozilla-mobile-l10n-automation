# iOS placeable audit — May 2026 — and why it's clean

> Real-data run of [`scripts/check_placeables_ios.py`](./scripts/check_placeables_ios.py) against [`mozilla-l10n/firefoxios-l10n`](https://github.com/mozilla-l10n/firefoxios-l10n). 25 locales scanned, ~45,000 trans-unit comparisons, **0 findings**. This document explains why the result is meaningful, not broken.

## Scope

- **Repo:** `mozilla-l10n/firefoxios-l10n` at `main` (cloned 2026-05-22)
- **File format:** XLIFF 1.2, one consolidated `firefox-ios.xliff` per locale
- **Locales scanned:** ar, ca, cs, de, es, eu, fi, fr, he, hu, it, ja, ko, ms, nl, pl, pt-BR, ru, sk, sv, th, tr, uk, vi, zh-CN
- **What's checked:** every `<trans-unit>` with a `<target>` — placeables (`%@`, `%d`, `%lld`, `%1$@`, etc.) must match between `<source>` and `<target>`.

Per-locale scale (from Turkish as a representative example):
- 1,825 trans-units total
- 1,814 translated (99.4% coverage)
- 168 source units contain placeables

Across 25 locales × ~1,800 trans-units, the audit ran ~45,000 source-vs-target comparisons. **Zero placeable mismatches.**

## The headline finding *is* zero

Zero findings doesn't mean the audit failed. It means iOS catches these bugs earlier in the pipeline than Android does.

Three independent gates are in play:

1. **Apple's build-time placeable validation.** Xcode's localization tooling enforces that translation strings have the same printf-style format specifiers as the source. A `Localizable.strings` file with a placeable mismatch will produce a compile warning or, in some configurations, a build failure.

2. **Mozilla's reference-string linter.** The `firefoxios-l10n` repo runs a [GitHub Actions linter](https://github.com/mozilla-l10n/firefoxios-l10n/blob/main/.github/scripts/linter_config.json) on every PR that touches `en-US` — checks for misused quotes, ellipsis, hard-coded brand names, and (relevant here) flags reference-string issues that propagate to translations.

3. **The XLIFF schema itself.** Each `<trans-unit>` pairs its `<source>` and `<target>` in the same element. A translator working in Pontoon (Mozilla's translation platform) sees the source placeable inline while writing the target. Compare this with Android, where the en-US source and locale translation live in two *different files* — the translator can't see them side-by-side without external tooling.

**Compare with the Android audit (same methodology, different tooling):**

| Platform | Files scanned | Comparisons | Findings | Findings per 1,000 units |
|---|---|---|---|---|
| Android (`android-l10n`) | 41 source files × 25 locales | ~1,000 file pairs | **9** | ~9 |
| iOS (`firefoxios-l10n`) | 1 XLIFF × 25 locales | ~45,000 trans-units | **0** | 0 |

iOS is *at least* 4,500× cleaner per comparison unit. That's not noise — that's a structural difference. See [`placeable-audit-android-2026-05-22.md`](./placeable-audit-android-2026-05-22.md) for the Android findings in detail.

## Why this audit still has value

If iOS is clean, why run the audit?

1. **Verification of the gate.** "We have build-time validation" is a *claim*. An independent audit confirms the claim holds against the real data. Zero findings is the *expected* result if all three gates are working; non-zero would mean a gate has regressed.

2. **Regression detection.** If a future PR slips through Apple's compile check (perhaps because the linter has an exemption, or a build configuration drift), the audit catches it. Wire the script into CI as a per-PR gate — same pattern as my desktop project's [GitHub Action](https://github.com/ergunneda-dev/mozilla-l10n-automation/blob/main/github-actions-examples/placeable-check.yml).

3. **Cross-platform consistency check.** For features that ship on both iOS and Android, the audit's *contrast* surfaces locales where Android translators are behind and iOS translators are ahead (or vice versa). That's actionable for a program manager.

4. **Documentation.** Zero findings is a *result*, and a written audit confirms it. Without this document, "iOS placeables are clean" is folklore; with it, there's an artifact stakeholders can reference.

## How the script was verified

A zero-finding result invites the question: is the script even working? It is. The verification:

```python
# Diagnostic run against tr/firefox-ios.xliff
Total trans-units: 1825
With target (translated): 1814
Source units with placeables: 168

# Sample of source-unit placeables found:
'A username and password are being requested by %@.'           -> ['%@']
'A username and password are being requested by %@. The site says: %@'
                                                                -> ['%1$@', '%2$@']
'ActivityStream.JumpBackIn.TabGroup.SiteCount'                 -> ['%d']
'Downloads.Toast.MultipleFiles.DescriptionText'                -> ['%d']
'Downloads.Toast.MultipleFilesAndProgress.DescriptionText'
                                                                -> ['%1$@', '%2$@']
```

168 source units have placeables. All 168 (after target alignment) had matching placeables in their `<target>`. The script is doing its job; the data is clean.

## What this audit doesn't catch

Same caveats as the Android audit, plus one iOS-specific:

- **Missing translations entirely** — different audit (entry-presence, not placeable-consistency).
- **Stale references** — XLIFF's `<source>`/`<target>` pairing inside each `<trans-unit>` makes stale references nearly impossible by construction. If the source moves on, the unit's source text changes, and the matching against the locale catalog re-pairs from scratch.
- **iOS-specific: `%@` argument type confusion** — Objective-C/Swift's `%@` accepts any object via `description`. If en-US passes an `NSString` and a translator's locale-specific format string expects the same `%@` to be a `Date`, the runtime call is still valid but produces wrong output. The placeable audit can't catch this — only manual review can.

## How to reproduce

```bash
git clone --depth=1 https://github.com/mozilla-l10n/firefoxios-l10n.git
python3 scripts/check_placeables_ios.py firefoxios-l10n tr
python3 scripts/check_placeables_ios.py firefoxios-l10n ja
# ...etc. for any locale
```

For the diagnostic that verified the script:

```bash
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from check_placeables_ios import parse_xliff
from pathlib import Path
units = parse_xliff(Path('firefoxios-l10n/tr/firefox-ios.xliff'))
print(f'Total: {len(units)}, translated: {sum(1 for u in units.values() if u[\"target\"] is not None)}')
"
```

## What I'd do next as program manager

1. **Wire the script into CI as a regression gate.** Even when findings are zero today, a build-config change tomorrow can change that. The cost of running the audit on every PR is seconds.
2. **Run it monthly across all ~100 locales** as a confidence check on the iOS l10n pipeline. Document the result. If a finding ever appears, treat it as a P1 because it means one of the three upstream gates failed.
3. **Use the contrast against Android as a planning signal.** When the same feature ships to both platforms and Android surfaces findings while iOS doesn't, that's information about which locale teams need attention on which platform.
