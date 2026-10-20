#!/usr/bin/env python3
"""Deterministic post-translation checks for translated chunks.

Reads every translated chunk and reports three classes of defects that never
need a model to detect:

  C1 kana remnants -- kana in the Chinese output that the locked glossary does not
     whitelist, i.e. a term left untranslated, a dropped gloss, or surviving
     sentence-final kana.
  C2 machine-tells -- an honourific rendered as 桑 / 酱. Reported as suspects, not
     violations, because both characters also occur in real names.
  C3 pronoun flattening -- the source chunk uses two or more distinct first-person
     pronouns while the translation uses only 我-family ones.

Kana is whitelisted from the glossary itself: entries rendered as （保留）, entries
whose target equals the source, plus the counter glyphs ヶ / ヵ which survive in
normal Chinese text.

Exits 0 when clean, 1 when a violation is found (or, under --strict, when any
suspect is found), and 2 on usage errors such as a missing directory or a
malformed glossary.

Only the standard library is used, so there is nothing to pip install.

Examples:
    python verify_glossary.py --chunks-dir chunks --translated-dir out --glossary glossary.json
    python verify_glossary.py --translated-dir out --glossary glossary.json --strict
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SUFFIXES = {".txt", ".md", ".ja", ".text"}

# Hiragana, katakana, the prolonged-sound mark, and half-width katakana.
KANA_RE = re.compile(r"[\u3041-\u309F\u30A1-\u30FF\u30FC\uFF66-\uFF9F]+")

# A CJK character immediately followed by a tell: the さん/ちゃん-as-桑/酱 pattern.
TELL_RE = re.compile(r"([\u3400-\u9FFF])([桑酱])")

# Any kana the output may keep even when the glossary is silent: counter glyphs.
DEFAULT_ALLOWED_KANA = {"ヶ", "ヵ"}

# Ordered longest-first; all are disjoint scripts, so plain substring presence works.
JA_PRONOUNS = ("わたくし", "あたし", "わし", "僕", "俺", "私")
CN_PRONOUN_MARKERS = ("俺", "咱", "人家", "老子", "本座")

KEEP_MARK = "保留"


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def load_glossary(path: Path) -> dict[str, str]:
    """Read the flat source-to-target map, refusing anything else."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"glossary not found: {path}")
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")
    if not isinstance(data, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in data.items()
    ):
        fail(f"{path} must map source strings to target strings")
    return data


def context(text: str, start: int, end: int, width: int) -> str:
    """A one-line excerpt around [start, end), never out of bounds."""
    lo = max(0, start - width)
    hi = min(len(text), end + width)
    snippet = text[lo:hi].replace("\n", " ").strip()
    return ("..." if lo > 0 else "") + snippet + ("..." if hi < len(text) else "")


def kana_findings(name: str, text: str, allowed: set[str], width: int) -> list[tuple]:
    """C1: kana runs in the output that no whitelisted glossary key covers."""
    findings = []
    for match in KANA_RE.finditer(text):
        run = match.group(0)
        if run in DEFAULT_ALLOWED_KANA:
            continue
        if any(run in key or key in run for key in allowed):
            continue
        findings.append((
            name, "C1", "violation", f"kana remnant: {run}",
            context(text, match.start(), match.end(), width),
        ))
    return findings


def tell_findings(name: str, text: str, targets: set[str], width: int) -> list[tuple]:
    """C2: 桑/酱 right after a CJK character, unless a glossary target contains it."""
    findings = []
    for match in TELL_RE.finditer(text):
        pair = match.group(0)
        if any(pair in target for target in targets):
            continue
        start, end = match.start(2), match.end(2)
        findings.append((
            name, "C2", "suspect", f"tell: {match.group(2)}",
            context(text, start, end, width),
        ))
    return findings


def pronoun_findings(name: str, source: str, text: str) -> list[tuple]:
    """C3: source speaks with 2+ first-person pronouns, translation flattens to 我."""
    distinct = {p for p in JA_PRONOUNS if p in source}
    if len(distinct) < 2:
        return []
    if any(marker in text for marker in CN_PRONOUN_MARKERS):
        return []
    if "我" not in text:
        return []
    pronouns = "、".join(sorted(distinct))
    return [(name, "C3", "suspect", f"pronoun flattening (source: {pronouns})", "")]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check translated chunks for kana remnants, machine-tells and pronoun flattening."
    )
    parser.add_argument("--chunks-dir", type=Path, default=None,
                        help="source chunk directory, needed only for the C3 check")
    parser.add_argument("--translated-dir", type=Path, required=True,
                        help="directory of translated chunk files")
    parser.add_argument("--glossary", type=Path, required=True,
                        help="the locked glossary.json")
    parser.add_argument("--strict", action="store_true",
                        help="exit non-zero on suspects, not just violations")
    parser.add_argument("--max-context", type=int, default=20,
                        help="excerpt width around each finding (default: 20)")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if not args.translated_dir.is_dir():
        fail(f"translated directory not found: {args.translated_dir}")
    if args.chunks_dir is not None and not args.chunks_dir.is_dir():
        fail(f"chunks directory not found: {args.chunks_dir}")
    if args.max_context < 0:
        fail("--max-context must not be negative")

    glossary = load_glossary(args.glossary)

    # Kana may survive only through entries that opt out of translation.
    allowed_kana = {
        key for key, target in glossary.items()
        if KEEP_MARK in target or target == key
    } | DEFAULT_ALLOWED_KANA
    targets = set(glossary.values())

    files = sorted(
        p for p in args.translated_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUFFIXES
    )
    if not files:
        fail(f"no translated chunks found in {args.translated_dir}")

    findings: list[tuple] = []
    c3_available = args.chunks_dir is not None
    for path in files:
        text = path.read_text(encoding="utf-8")
        name = path.name
        findings.extend(kana_findings(name, text, allowed_kana, args.max_context))
        findings.extend(tell_findings(name, text, targets, args.max_context))
        if c3_available:
            source_path = args.chunks_dir / name
            if source_path.is_file():
                source = source_path.read_text(encoding="utf-8")
                findings.extend(pronoun_findings(name, source, text))

    for name, check, severity, detail, excerpt in findings:
        location = f"  {excerpt}" if excerpt else ""
        print(f"{name}  {check} {severity}  {detail}{location}")

    violations = sum(1 for f in findings if f[2] == "violation")
    suspects = sum(1 for f in findings if f[2] == "suspect")
    print(f"summary: {len(files)} chunks checked  violations: {violations}  "
          f"suspects: {suspects}")
    if not c3_available:
        print("skipped: C3 (no --chunks-dir given)")

    if violations or (args.strict and suspects):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
