# Android placeable audit — May 2026

> Real-data run of [`scripts/check_placeables_android.py`](./scripts/check_placeables_android.py) against [`mozilla-l10n/android-l10n`](https://github.com/mozilla-l10n/android-l10n). 25 locales scanned, 9 findings across 4 locales. This document categorizes them and flags which ones a program manager should escalate.

## Scope

- **Repo:** `mozilla-l10n/android-l10n` at `main` (cloned 2026-05-22)
- **Products in scope:** android-components (38 source files), fenix (2 source files including the `longfox` flavor), focus-android (1 source file). 41 `values/strings.xml` source files total.
- **Locales scanned:** ar, ca, cs, de, es, eu, fi, fr, he, hu, it, ja, ko, ms, nl, pl, pt-rBR, ru, sk, sv, th, tr, uk, vi, zh-rCN
- **What's checked:** every `<string>`, `<plurals>` item, and `<string-array>` item — placeables (`%s`, `%1$d`, `%lld`, etc., plus `<xliff:g>` wrappers) must match between source and translation.

## Headline

**Most locales are clean. The findings are concentrated and pattern-revealing.**

| Locale | Findings | Where |
|---|---|---|
| ar (Arabic) | 5 | 4 in Fenix Tab Groups plurals, 1 in browser menu |
| cs (Czech) | 2 | Fenix main — missing `%d` count placeholders |
| pl (Polish) | 1 | Focus Android — slot count mismatch |
| de (German) | 1 | android-components sitepermissions — `%s` vs `%1$s` type mismatch |
| All other 21 locales | 0 | — |

Nine findings against ~1,000 file comparisons. That's the audit doing its job: sparse, real, actionable.

## Findings categorized

The same three-category framework from my [desktop Firefox project](https://github.com/ergunneda-dev/mozilla-l10n-automation) applies. Each finding gets triaged into one of:

1. **Deliberate simplifications** — translator dropped a placeable on purpose because their language doesn't need the distinction. *Not bugs.*
2. **Latent runtime UI bugs** — translation is missing a placeable the app passes at runtime. User sees a sentence with a hole in it. *File as bugs.*
3. **Stale references** — translation references a variable that no longer exists in source. Doesn't crash. *Tidy on next sync.*

### Category 2 — Latent runtime UI bugs (7 of 9 findings)

The cluster worth escalating.

**Arabic, Fenix, Tab Groups feature (4 findings):**

```
tab_group_tabs_count_subtitle#one           -> missing=['%1$d']
add_to_exiting_tab_group_content_description#one -> missing=['%2$d']
share_tab_group_button_content_description#one  -> missing=['%2$d']
expanded_tab_group_header_description#one   -> missing=['%2$d']
```

All four are the `#one` plural form of recently-landed Tab Groups strings. At runtime, Firefox passes a count expecting substitution; the Arabic "one" form doesn't have the slot for it. Users with Arabic locale will see, for example, "tab in group" instead of "1 tab in group" — the number is missing entirely.

**The pattern matters more than the count:** all four findings cluster in the same feature, suggesting the Tab Groups strings landed in en-US before the Arabic team completed a full pass. Same leading-indicator behavior I observed for Japanese in the [desktop audit](https://github.com/ergunneda-dev/mozilla-l10n-automation/blob/main/placeable-audit-2026-05-20.md) — placeable findings concentrate in features that recently shipped.

**What a program manager should do:** flag to the Arabic locale team with a single bug pointing at all four entries. Don't escalate them as individual tickets — that fragments the work. Frame it as "Tab Groups plurals need a pass for ar.

**Czech, Fenix (2 findings):**

```
recently_closed_tab                              -> missing=['%d']
create_collection_save_to_collection_tab_selected -> missing=['%d']
```

Two Category 2 bugs. At runtime: "recently closed tab" instead of "5 recently closed tabs" (the `%d` is the count). Same fix pattern as Arabic: one bug, two entries, send to the cs team.

**Polish, Focus (1 finding):**

```
firstrun_shortcut_text -> slot_diff=['%1$s (2 in source, 1 in translation)']
```

The source has `%1$s` appearing **twice** in the string. The Polish translation has it **once**. At runtime, only the first substitution will appear; the second value Firefox passes will be invisible to the Polish user. This is a slot-count bug, subtler than an outright missing placeable, but the user impact is the same: missing information in the rendered UI.

### Category 1 — Probably deliberate / benign (2 of 9 findings)

**German, android-components/sitepermissions:**

```
mozac_feature_sitepermissions_storage_access_message
    -> missing=['%s'], extra=['%1$s']
```

Source uses `%s`. German uses `%1$s`. In Android, these are *semantically equivalent* when there's only one placeholder — both consume the first string argument passed via `String.format()`. So at runtime, this works fine.

But the script is right to flag it. If en-US ever adds a second `%s` (for example, becomes `"Allow %s to access %s"`), the German translation will compile fine but produce wrong output because `%1$s` is anchored to the *first* argument while the German translator may have intended a different ordering. *Flag, don't fix urgently.*

**Arabic, Fenix browser menu (1 finding):**

```
browser_menu_delete_browsing_data_on_quit
    -> missing=['%1$s'], extra=['%s']
```

Inverse of the German case: source has `%1$s`, Arabic has `%s`. Same semantic equivalence at runtime, same latent-but-not-active risk. Worth a translator nudge to standardize on the source's convention.

### Category 3 — Stale references (0 of 9 findings)

None in this audit. The android-l10n repo's sync workflow (scheduled GitHub Actions extracting strings from active branches) appears to keep stale references out — when en-US drops a variable, the locale's reference goes with it on next sync. Different mechanism from `firefox-l10n`, but effective.

## What this audit doesn't catch

Worth being explicit about, because no audit is complete:

- **Missing translations entirely** — a string in en-US but absent from the locale. That's a different audit (the desktop project's `audit_missing.py` covers it; equivalent for Android would walk the same paths and report on entry-presence rather than placeable-consistency).
- **Wrong placeable, right slot** — if the translator uses `%@` (an iOS-style token) where the source uses `%s`, the script flags it. But if the translator uses `%d` where source uses `%s`, the script *also* flags it as type mismatch. Whether that's a "bug" or "deliberate type promotion" requires looking at the actual string.
- **Stylistic placeable wrapping** — the `<xliff:g id="..." example="...">%s</xliff:g>` wrapper is metadata for translators. If a translation drops the wrapper but keeps the `%s`, the placeable still matches and the script reports clean. That's correct for runtime, but a separate stylistic-consistency check could flag the missing metadata.

## How to reproduce

```bash
git clone --depth=1 https://github.com/mozilla-l10n/android-l10n.git
python3 scripts/check_placeables_android.py android-l10n ar
python3 scripts/check_placeables_android.py android-l10n cs
python3 scripts/check_placeables_android.py android-l10n pl
python3 scripts/check_placeables_android.py android-l10n de
```

Raw outputs from this audit are in [`android-ar-findings.txt`](./android-ar-findings.txt), [`android-cs-findings.txt`](./android-cs-findings.txt), [`android-pl-findings.txt`](./android-pl-findings.txt), [`android-de-findings.txt`](./android-de-findings.txt).

## What I'd do next as program manager

1. **One bug per locale**, not one per finding. The Arabic Tab Groups cluster is a single conversation with the ar team, not four separate tickets.
2. **Add a CI gate.** The same script can run on every PR that touches a `strings.xml`, blocking placeable regressions before they merge. (My desktop project includes a [GitHub Action that does this for Fluent files](https://github.com/ergunneda-dev/mozilla-l10n-automation/blob/main/github-actions-examples/placeable-check.yml); the Android variant is mechanically the same.)
3. **Track the leading-indicator pattern.** Re-run the audit weekly; a locale's finding count spiking up is a signal that a recently-landed feature shipped en-US strings before that locale's translators finished a pass. That's *useful* information for a program manager — it tells you which locales are running behind which features.
