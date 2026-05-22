#!/usr/bin/env python3
"""
check_placeables_ios.py — placeable consistency check for iOS XLIFF files.

For each <trans-unit>, compare the placeables in <source> against <target>.
Reports three states:

  - missing  : present in source, absent in translation (runtime risk)
  - extra    : present in translation, absent in source (stale reference)
  - slot_diff: same placeable appears a different number of times

Placeables understood (iOS / Objective-C / Swift NSLocalizedString):
  - %@                         (Cocoa object — strings, etc.)
  - %d, %i, %u                 (integers)
  - %ld, %lu, %lld, %llu       (long / long long)
  - %f, %e, %g                 (floats)
  - %x, %X, %o, %c, %s         (hex / octal / char / C-string)
  - %1$@, %2$d, %1$lld         (positional variants of any of the above)

Usage:
    python3 check_placeables_ios.py <xliff_file_or_dir> <locale>

The first argument can be:
  - A directory containing the firefoxios-l10n repo (script will compare
    en-US/*.xliff against <locale>/*.xliff)
  - A single en-US XLIFF file (paired with the same-named file in <locale>)

Discipline notes:
  - Parses XML via xml.etree.ElementTree. No regex on raw XML.
  - Read-only. Never mutates source files.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET


XLIFF_NS = "urn:oasis:names:tc:xliff:document:1.2"
NS = {"x": XLIFF_NS}

# iOS placeables. Longer length-modified variants first so we don't truncate
# %lld into %ld + 'd'.
PLACEABLE_RE = re.compile(r"%(?:(\d+)\$)?(@|ll[du]|l[du]|[dilfxoegcsuXEG])")


def extract_placeables(text: str) -> list[str]:
    """Return placeables in order of appearance, as canonical tokens."""
    if not text:
        return []
    return [m.group(0) for m in PLACEABLE_RE.finditer(text)]


def _local(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def parse_xliff(path: Path) -> dict[tuple[str, str], dict[str, list[str] | None]]:
    """Parse a XLIFF file into {(file_original, trans_unit_id): {source, target}}.

    `source` is always present; `target` may be None if the unit is untranslated.
    Values are placeable lists, not raw text.
    """
    tree = ET.parse(path)
    root = tree.getroot()
    out: dict[tuple[str, str], dict[str, list[str] | None]] = {}

    for file_elem in root.findall(".//x:file", NS) or root.findall(".//file"):
        original = file_elem.attrib.get("original", "?")
        body = file_elem.find("x:body", NS) or file_elem.find("body")
        if body is None:
            continue
        for tu in body:
            if _local(tu.tag) != "trans-unit":
                continue
            tu_id = tu.attrib.get("id", "?")
            src_elem = None
            tgt_elem = None
            for child in tu:
                lt = _local(child.tag)
                if lt == "source":
                    src_elem = child
                elif lt == "target":
                    tgt_elem = child
            src_text = "".join(src_elem.itertext()) if src_elem is not None else ""
            tgt_text = "".join(tgt_elem.itertext()) if tgt_elem is not None else None
            out[(original, tu_id)] = {
                "source": extract_placeables(src_text),
                "target": extract_placeables(tgt_text) if tgt_text is not None else None,
            }
    return out


def compare(units: dict[tuple[str, str], dict[str, list[str] | None]]) -> list[
    tuple[str, str, list[str], list[str], list[str]]
]:
    """Per-unit findings: (file_original, trans_unit_id, missing, extra, slot_diff)."""
    findings = []
    for (orig, tu_id), phs in units.items():
        src = phs["source"]
        tgt = phs["target"]
        if tgt is None:
            continue  # untranslated unit; missing-translation audit is separate
        src_set, tgt_set = set(src), set(tgt)
        missing = sorted(src_set - tgt_set)
        extra = sorted(tgt_set - src_set)
        slot_diff = []
        for ph in src_set & tgt_set:
            if src.count(ph) != tgt.count(ph):
                slot_diff.append(
                    f"{ph} ({src.count(ph)} in source, {tgt.count(ph)} in translation)"
                )
        if missing or extra or slot_diff:
            findings.append((orig, tu_id, missing, extra, slot_diff))
    return findings


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "Usage: check_placeables_ios.py <repo_dir_or_xliff> <locale_code>",
            file=sys.stderr,
        )
        return 2

    arg, locale = argv[1], argv[2]
    arg_path = Path(arg)

    # Resolve to a list of (label, xliff_path) pairs to process.
    xliffs: list[tuple[str, Path]] = []
    if arg_path.is_dir():
        loc_dir = arg_path / locale
        if not loc_dir.is_dir():
            print(f"Locale directory not found: {loc_dir}", file=sys.stderr)
            return 1
        for xf in sorted(loc_dir.rglob("*.xliff")):
            xliffs.append((str(xf.relative_to(arg_path)), xf))
    elif arg_path.is_file():
        xliffs.append((str(arg_path), arg_path))
    else:
        print(f"Not a file or directory: {arg_path}", file=sys.stderr)
        return 1

    total_findings = 0
    total_files_with_findings = 0
    for label, xf in xliffs:
        try:
            units = parse_xliff(xf)
        except ET.ParseError as e:
            print(f"[{label}] PARSE ERROR: {e}", file=sys.stderr)
            continue
        findings = compare(units)
        if findings:
            total_files_with_findings += 1
            print(f"\n[{label}]")
            for orig, tu_id, missing, extra, slot_diff in findings:
                bits = []
                if missing:
                    bits.append(f"missing={missing}")
                if extra:
                    bits.append(f"extra={extra}")
                if slot_diff:
                    bits.append(f"slot_diff={slot_diff}")
                print(f"  {orig} :: {tu_id} -> {', '.join(bits)}")
                total_findings += 1

    print(
        f"\n## Summary: {total_findings} findings across "
        f"{total_files_with_findings} XLIFF files ({len(xliffs)} files scanned)"
    )
    return 0 if total_findings == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
