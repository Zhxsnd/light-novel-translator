#!/usr/bin/env python3
"""Split a Japanese light-novel source file into translation-sized chunks.

Replaces the hand-made Step 3 of the skill workflow. A whole book is read, cut at the
chapter headings, and any chapter still longer than --max-chars is cut further at blank
line boundaries. No line is ever split in the middle, and no empty chunk is produced, so
every chunk can be handed to the translator as a standalone unit.

A manifest with the character count and sha256 of each chunk is written next to the
chunks, so a later re-run can tell which chunks are already finished.

Only the standard library is used, so there is nothing to pip install.

Examples:
    python chunk_source.py --input novel.txt --out-dir chunks
    python chunk_source.py --input novel.md --max-chars 2500 --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

NUMERALS = "0-9０-９一二三四五六七八九十百"

# Chapter headings: 第N話 / 第N章 / 第N節, with Arabic, full-width or kanji numerals.
CHAPTER_RE = re.compile(rf"^第[{NUMERALS}]+[話章節]")
MARKDOWN_HEADING_RE = re.compile(r"^#{1,2} ")

# Ruby glosses: 《...》, optionally with the |base《...》 pipe form Aozora Bunko uses.
RUBY_PIPE_RE = re.compile(r"[|｜]([^\s《》|｜]*?)《[^》]*》")
RUBY_RE = re.compile(r"《[^》]*》")


def strip_ruby(text: str) -> str:
    """Drop every 《...》 gloss, including the |base《...》 pipe form."""
    text = RUBY_PIPE_RE.sub(r"\1", text)
    return RUBY_RE.sub("", text)


def find_headings(lines: list[str]) -> list[int]:
    """Return the indices of chapter-heading lines, in order.

    A heading line itself starts the new chapter and is kept as its first line.
    """
    indices: list[int] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if CHAPTER_RE.match(stripped) or MARKDOWN_HEADING_RE.match(stripped):
            indices.append(index)
    return indices


def group_chapters(lines: list[str], headings: list[int]) -> list[list[str]]:
    """Split lines into per-chapter groups. Text before the first heading leads the book.

    When the file has no heading at all, the whole text is a single group.
    """
    groups: list[list[str]] = []
    if not headings:
        if any(line.strip() for line in lines):
            groups.append(lines)
        return groups

    if headings[0] > 0:
        lead = lines[: headings[0]]
        if any(line.strip() for line in lead):
            groups.append(lead)
    for position, start in enumerate(headings):
        end = headings[position + 1] if position + 1 < len(headings) else len(lines)
        groups.append(lines[start:end])
    return groups


def split_paragraphs(lines: list[str]) -> list[list[str]]:
    """Group lines into paragraphs, one per run of non-blank lines."""
    paragraphs: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.strip():
            current.append(line)
        elif current:
            paragraphs.append(current)
            current = []
    if current:
        paragraphs.append(current)
    return paragraphs


def paragraph_items(lines: list[str], max_chars: int,
                    long_lines: list[str]) -> list[tuple[bool, str]]:
    """Turn a chapter into packable items of (joins_with_single_newline, text).

    A paragraph that fits --max-chars stays one item, its lines joined by newlines. A
    paragraph that does not fit is broken into one item per line, which is still a
    line-boundary cut and never cuts a line in the middle.
    """
    items: list[tuple[bool, str]] = []
    for paragraph in split_paragraphs(lines):
        joined = "\n".join(paragraph)
        if len(joined) <= max_chars:
            items.append((False, joined))
            continue
        for offset, line in enumerate(paragraph):
            if len(line) > max_chars:
                long_lines.append(line)
            items.append((offset > 0, line))
    return items


def pack_items(items: list[tuple[bool, str]], max_chars: int) -> list[str]:
    """Greedily pack items into chunks, opening a new chunk before exceeding max_chars.

    A single item larger than --max-chars is kept whole rather than cut.
    """
    chunks: list[str] = []
    current = ""
    for contiguous, text in items:
        if not current:
            current = text
            continue
        separator = "\n" if contiguous else "\n\n"
        if len(current) + len(separator) + len(text) > max_chars:
            chunks.append(current)
            current = text
        else:
            current += separator + text
    if current:
        chunks.append(current)
    return chunks


def build_chunks(lines: list[str], max_chars: int, long_lines: list[str]) -> list[str]:
    """Cut every chapter group into chunks, preserving the order of the book."""
    chunks: list[str] = []
    for group in group_chapters(lines, find_headings(lines)):
        items = paragraph_items(group, max_chars, long_lines)
        chunks.extend(pack_items(items, max_chars))
    return [chunk.strip("\n") for chunk in chunks if chunk.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Split a Japanese light-novel source file into translation-sized chunks."
    )
    parser.add_argument("--input", required=True, type=Path,
                        help="UTF-8 source text file (.txt or .md)")
    parser.add_argument("--out-dir", type=Path, default=Path("chunks"),
                        help="directory for the chunk files (default: ./chunks)")
    parser.add_argument("--manifest", type=Path, default=Path("manifest.json"),
                        help="manifest with each chunk's size and hash (default: ./manifest.json)")
    parser.add_argument("--max-chars", type=int, default=3500,
                        help="target character limit per chunk (default: 3500)")
    parser.add_argument("--keep-ruby", action="store_true",
                        help="keep 《...》 ruby glosses instead of stripping them")
    parser.add_argument("--dry-run", action="store_true",
                        help="report the split plan, write nothing")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if not args.input.is_file():
        raise SystemExit(f"input file not found: {args.input}")
    if args.input.suffix.lower() not in {".txt", ".md"}:
        raise SystemExit(f"input must be .txt or .md, got '{args.input.suffix or '(none)'}'")
    if args.max_chars < 1:
        raise SystemExit("--max-chars must be at least 1")

    text = args.input.read_text(encoding="utf-8")
    if not args.keep_ruby:
        text = strip_ruby(text)
    lines = text.splitlines()

    chapter_count = len(find_headings(lines))
    long_lines: list[str] = []
    chunks = build_chunks(lines, args.max_chars, long_lines)
    if not chunks:
        raise SystemExit(f"{args.input} has no text to chunk")

    for line in long_lines:
        preview = line[:60] + ("..." if len(line) > 60 else "")
        print(f"warning: line of {len(line)} chars exceeds --max-chars and stays whole: "
              f"{preview}", file=sys.stderr)

    sizes = [len(chunk) for chunk in chunks]
    names = [f"chunk{index:04d}.txt" for index in range(1, len(chunks) + 1)]

    if args.dry_run:
        for name, size in zip(names, sizes):
            print(f"  {name}  {size} chars")
        print(f"chapters: {chapter_count}  would write: {len(chunks)} chunks  "
              f"chars: max {max(sizes)} / min {min(sizes)}")
        print(f"dry run: nothing written to {args.out_dir} or {args.manifest}")
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest_chunks = []
    for name, chunk, size in zip(names, chunks, sizes):
        data = (chunk + "\n").encode("utf-8")
        (args.out_dir / name).write_bytes(data)
        manifest_chunks.append({
            "name": name,
            "chars": size,
            "sha256": hashlib.sha256(data).hexdigest(),
        })

    manifest = {
        "source": str(args.input),
        "max_chars": args.max_chars,
        "chunk_count": len(manifest_chunks),
        "chunks": manifest_chunks,
    }
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"chapters: {chapter_count}  chunks: {len(chunks)}  "
          f"chars: max {max(sizes)} / min {min(sizes)}")
    print(f"chunks -> {args.out_dir}  manifest -> {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
