#!/usr/bin/env python3
"""
check_placeables_android.py — placeable consistency check for Android strings.xml.

Designed for the layout used by mozilla-l10n/android-l10n, where en-US source
and translations are sibling directories:

    <repo>/<product>/.../res/values/strings.xml         (en-US source)
    <repo>/<product>/.../res/values-<locale>/strings.xml  (translation)

For each <string>, <plurals>, and <string-array> entry, compare placeables in
en-US against the target locale. Reports three states:

  - missing  : present in source, absent in translation (runtime risk)
  - extra    : present in translation, absent in source (stale reference)
  - slot_diff: same placeable appears a different number of times

Placeables understood:
  - printf-style: %s, %d, %i, %f, %x, %o, %e, %g, %c
  - positional:   %1$s, %2$d, ...
  - xliff:g wrapped: <xliff:g id="username" example="John">%s</xliff:g>

Usage:
    python3 check_placeables_android.py <repo_root> <android_locale>

Note: Android uses 'r' prefix for region variants. Pass the literal directory
suffix, e.g. 'tr', 'de', 'zh-rCN', 'pt-rBR'.

Discipline notes:
  - Parses XML via xml.etree.ElementTree (stdlib). No regex on raw XML.
  - Read-only. Never mutates source files.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET


POSITIONAL_RE = re.compile(r"%(\d+)\$([sdifxoegcaA])")
SIMPLE_RE = re.compile(r"%([sdifxoegcaA])")


def extract_placeables(text: str) -> list[str]:
    if not text:
        return []
    tokens: list[tuple[int, str]] = []
    for m in POSITIONAL_RE.finditer(text):
        tokens.append((m.start(), m.group(0)))
    masked = POSITIONAL_RE.sub(lambda m: " " * len(m.group(0)), text)
    for m in SIMPLE_RE.finditer(masked):
        tokens.append((m.start(), m.group(0)))
    tokens.sort()
    return [tok for _, tok in tokens]


def _entry_text(elem: ET.Element) -> str:
    """Flatten an Android resource element's text + child <xliff:g> wrappers."""
    parts: list[str] = []
    if elem.text:
        parts.append(elem.text)
    for child in elem:
        if child.text:
            parts.append(child.text)
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def parse_entries(path: Path) -> dict[str, list[str]]:
    """Return {entry_id: [placeables]} for one strings.xml file.

    Plurals and string-arrays decompose into one logical entry per item.
    """
    tree = ET.parse(path)
    root = tree.getroot()
    out: dict[str, list[str]] = {}

    for elem in root:
        name = elem.attrib.get("name")
        if not name:
            continue
        tag = elem.tag.split("}", 1)[-1]
        if tag == "string":
            out[name] = extract_placeables(_entry_text(elem))
        elif tag == "plurals":
            for item in elem.findall("item"):
                q = item.attrib.get("quantity", "?")
                out[f"{name}#{q}"] = extract_placeables(_entry_text(item))
        elif tag == "string-array":
            for i, item in enumerate(elem.findall("item")):
                out[f"{name}#{i}"] = extract_placeables(_entry_text(item))

    return out


def find_source_files(repo_root: Path) -> list[Path]:
    """All `values/strings.xml` files (en-US source) under the repo root.

    We rely on the Android convention: source strings live in 'values/', not
    'values-<locale>/'. We exclude anything with a hyphen-suffix.
    """
    sources: list[Path] = []
    for xml in repo_root.rglob("strings.xml"):
        parent = xml.parent.name
        if parent == "values":
            sources.append(xml)
    return sorted(sources)


def paired_target(source: Path, locale: str) -> Path:
    """Given a values/strings.xml path, return values-<locale>/strings.xml."""
    return source.parent.parent / f"values-{locale}" / "strings.xml"


def compare_entries(
    src: dict[str, list[str]], tgt: dict[str, list[str]]
) -> list[tuple[str, list[str], list[str], list[str]]]:
    findings = []
    for entry_id, src_phs in src.items():
        if entry_id not in tgt:
            continue  # untranslated entries are a separate audit
        tgt_phs = tgt[entry_id]
        src_set, tgt_set = set(src_phs), set(tgt_phs)
        missing = sorted(src_set - tgt_set)
        extra = sorted(tgt_set - src_set)
        slot_diff = []
        for ph in src_set & tgt_set:
            if src_phs.count(ph) != tgt_phs.count(ph):
                slot_diff.append(
                    f"{ph} ({src_phs.count(ph)} in source, {tgt_phs.count(ph)} in translation)"
                )
        if missing or extra or slot_diff:
            findings.append((entry_id, missing, extra, slot_diff))
    return findings


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "Usage: check_placeables_android.py <repo_root> <android_locale>",
            file=sys.stderr,
        )
        print(
            "Locale uses Android directory suffix (e.g. 'tr', 'de', 'zh-rCN').",
            file=sys.stderr,
        )
        return 2

    repo_root = Path(argv[1])
    locale = argv[2]

    sources = find_source_files(repo_root)
    if not sources:
        print(f"No values/strings.xml found under {repo_root}", file=sys.stderr)
        return 1

    paired: list[tuple[Path, Path]] = []
    for src in sources:
        tgt = paired_target(src, locale)
        if tgt.is_file():
            paired.append((src, tgt))

    if not paired:
        print(
            f"No translations found for locale '{locale}'. "
            f"Try 'tr' / 'de' / 'zh-rCN' (Android uses 'r' prefix for regions).",
            file=sys.stderr,
        )
        return 1

    total_findings = 0
    total_files_with_findings = 0
    for src, tgt in paired:
        try:
            src_entries = parse_entries(src)
            tgt_entries = parse_entries(tgt)
        except ET.ParseError as e:
            print(f"[{tgt.relative_to(repo_root)}] PARSE ERROR: {e}", file=sys.stderr)
            continue

        findings = compare_entries(src_entries, tgt_entries)
        if findings:
            total_files_with_findings += 1
            print(f"\n[{tgt.relative_to(repo_root)}]")
            for entry_id, missing, extra, slot_diff in findings:
                bits = []
                if missing:
                    bits.append(f"missing={missing}")
                if extra:
                    bits.append(f"extra={extra}")
                if slot_diff:
                    bits.append(f"slot_diff={slot_diff}")
                print(f"  {entry_id} -> {', '.join(bits)}")
                total_findings += 1

    print(
        f"\n## Summary: {total_findings} findings across "
        f"{total_files_with_findings} files ({len(paired)} files compared, "
        f"{len(sources)} sources scanned)"
    )
    return 0 if total_findings == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
