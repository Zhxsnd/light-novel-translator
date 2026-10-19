#!/usr/bin/env python3
"""Assemble translated light-novel chunks into a finished book.

Walks the source chunk directory in order, pairs every chunk with its translation in the
translated directory, and writes a plain-text, bilingual, or EPUB 3 file. A missing
translation aborts the run and is listed, so nothing ships half-translated. The EPUB is
built by hand with zipfile; after writing it, the script reopens the archive and checks
that the mimetype entry comes first, uncompressed, and that every XHTML document parses.

Only the standard library is used, so there is nothing to pip install.

Examples:
    python export_book.py --chunks-dir chunks --translated-dir out --out book.epub
    python export_book.py --chunks-dir chunks --translated-dir out --out book.txt \\
        --format bilingual
    python export_book.py --chunks-dir chunks --translated-dir out --out book.epub \\
        --title "転生王子" --author "Author Name" --cover cover.png
"""

from __future__ import annotations

import argparse
import html
import re
import sys
import uuid
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SUFFIXES = {".txt", ".md", ".ja", ".text"}

IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}

PARAGRAPH_BREAK = re.compile(r"\n\s*\n")

STYLE_CSS = """\
body {
  font-family: serif;
  line-height: 1.8;
  margin: 0 1em;
}
p {
  margin: 0.4em 0;
  text-indent: 2em;
}
h1 {
  font-size: 1.4em;
  margin: 0.6em 0;
  text-align: center;
}
"""


def collect_chunks(chunks_dir: Path) -> list[Path]:
    if not chunks_dir.is_dir():
        raise SystemExit(f"chunks directory not found: {chunks_dir}")
    files = sorted(
        p for p in chunks_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUFFIXES
    )
    if not files:
        raise SystemExit(f"no chunk files ({', '.join(sorted(SUFFIXES))}) in {chunks_dir}")
    return files


def split_paragraphs(text: str) -> list[str]:
    """Split on blank lines. A paragraph keeps its internal line breaks."""
    return [block.strip() for block in PARAGRAPH_BREAK.split(text.strip()) if block.strip()]


def load_chunks(chunks_dir: Path, translated_dir: Path) -> list[tuple[Path, list[str], list[str]]]:
    """Return (chunk, source paragraphs, translated paragraphs) in reading order.

    Every chunk must have a non-empty '<stem>.txt' beside it in the translated directory;
    the whole run stops and lists the gaps rather than producing a partial book.
    """
    if not translated_dir.is_dir():
        raise SystemExit(f"translated directory not found: {translated_dir}")

    loaded: list[tuple[Path, list[str], list[str]]] = []
    missing: list[str] = []
    for chunk in collect_chunks(chunks_dir):
        translated = translated_dir / f"{chunk.stem}.txt"
        if not translated.exists() or translated.stat().st_size == 0:
            missing.append(f"{chunk.name} (expected {translated.name})")
            continue
        loaded.append((
            chunk,
            split_paragraphs(chunk.read_text(encoding="utf-8")),
            split_paragraphs(translated.read_text(encoding="utf-8")),
        ))

    if missing:
        for item in missing:
            print(f"missing translation: {item}", file=sys.stderr)
        raise SystemExit(f"{len(missing)} chunk(s) have no translation; export aborted")
    return loaded


def write_txt(chunks: list[tuple[Path, list[str], list[str]]], out: Path) -> None:
    """Translation only, paragraphs separated by a blank line."""
    body = "\n\n".join(
        paragraph for _, _, translated in chunks for paragraph in translated
    )
    out.write_text(body + "\n", encoding="utf-8")


def write_bilingual(chunks: list[tuple[Path, list[str], list[str]]], out: Path) -> None:
    """Source paragraph then its translation. Uneven paragraph counts fall back to blocks."""
    parts: list[str] = []
    for chunk, source, translated in chunks:
        if len(source) == len(translated):
            for japanese, chinese in zip(source, translated):
                parts.append(f"{japanese}\n\n{chinese}")
        else:
            parts.append(
                f"[{chunk.stem}] 源文 {len(source)} 段与译文 {len(translated)} 段无法逐段对齐，"
                "本块回退为整块对照。"
            )
            parts.append("--- 日文 ---\n\n" + "\n\n".join(source))
            parts.append("--- 译文 ---\n\n" + "\n\n".join(translated))
    out.write_text("\n\n".join(parts) + "\n", encoding="utf-8")


def build_container_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<container version="1.0" '
        'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
        '  <rootfiles>\n'
        '    <rootfile full-path="OEBPS/content.opf" '
        'media-type="application/oebps-package+xml"/>\n'
        '  </rootfiles>\n'
        '</container>\n'
    )


def build_opf(chunks: list[tuple[Path, list[str], list[str]]], title: str, author: str,
              lang: str, modified: str, identifier: str,
              cover_name: str, cover_media: str) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
        'unique-identifier="book-id">',
        '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">',
        f'    <dc:identifier id="book-id">{identifier}</dc:identifier>',
        f'    <dc:title>{html.escape(title, quote=False)}</dc:title>',
        f'    <dc:language>{html.escape(lang, quote=False)}</dc:language>',
    ]
    if author:
        lines.append(f'    <dc:creator>{html.escape(author, quote=False)}</dc:creator>')
    lines += [
        f'    <meta property="dcterms:modified">{modified}</meta>',
        '  </metadata>',
        '  <manifest>',
        '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" '
        'properties="nav"/>',
        '    <item id="style" href="style.css" media-type="text/css"/>',
    ]
    if cover_name:
        lines.append(
            f'    <item id="cover-image" href="{cover_name}" media-type="{cover_media}" '
            'properties="cover-image"/>'
        )
        lines.append('    <item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>')
    for index in range(1, len(chunks) + 1):
        lines.append(
            f'    <item id="chunk{index:04d}" href="chunk{index:04d}.xhtml" '
            'media-type="application/xhtml+xml"/>'
        )
    lines += ['  </manifest>', '  <spine>']
    if cover_name:
        lines.append('    <itemref idref="cover"/>')
    for index in range(1, len(chunks) + 1):
        lines.append(f'    <itemref idref="chunk{index:04d}"/>')
    lines += ['  </spine>', '</package>', '']
    return "\n".join(lines)


def build_nav_xhtml(title: str, lang: str, count: int) -> str:
    items = "\n".join(
        f'      <li><a href="chunk{index:04d}.xhtml">第 {index} 章</a></li>'
        for index in range(1, count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE html>\n'
        f'<html xmlns="http://www.w3.org/1999/xhtml" '
        f'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{lang}" lang="{lang}">\n'
        '  <head>\n'
        '    <meta charset="utf-8"/>\n'
        f'    <title>{html.escape(title, quote=False)}</title>\n'
        '  </head>\n'
        '  <body>\n'
        '    <nav epub:type="toc" id="toc">\n'
        '      <h1>目录</h1>\n'
        '      <ol>\n'
        f'{items}\n'
        '      </ol>\n'
        '    </nav>\n'
        '  </body>\n'
        '</html>\n'
    )


def build_chunk_xhtml(index: int, paragraphs: list[str], lang: str) -> str:
    body = "\n".join(f'    <p>{html.escape(p, quote=False)}</p>' for p in paragraphs)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE html>\n'
        f'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{lang}" lang="{lang}">\n'
        '  <head>\n'
        '    <meta charset="utf-8"/>\n'
        f'    <title>第 {index} 章</title>\n'
        '    <link rel="stylesheet" type="text/css" href="style.css"/>\n'
        '  </head>\n'
        '  <body>\n'
        f'{body}\n'
        '  </body>\n'
        '</html>\n'
    )


def build_cover_xhtml(title: str, lang: str, cover_name: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE html>\n'
        f'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{lang}" lang="{lang}">\n'
        '  <head>\n'
        '    <meta charset="utf-8"/>\n'
        f'    <title>{html.escape(title, quote=False)}</title>\n'
        '  </head>\n'
        '  <body>\n'
        f'    <img src="{cover_name}" alt="cover"/>\n'
        '  </body>\n'
        '</html>\n'
    )


def write_epub(chunks: list[tuple[Path, list[str], list[str]]], out: Path, title: str,
               author: str, lang: str, cover: Path | None) -> None:
    modified = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    identifier = f"urn:uuid:{uuid.uuid4()}"

    cover_name = ""
    cover_media = ""
    if cover is not None:
        if not cover.exists():
            raise SystemExit(f"cover image not found: {cover}")
        cover_media = IMAGE_TYPES.get(cover.suffix.lower(), "")
        if not cover_media:
            raise SystemExit(
                f"unsupported cover image type: {cover.suffix} "
                f"(expected one of {', '.join(sorted(IMAGE_TYPES))})"
            )
        cover_name = f"cover{cover.suffix.lower()}"

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        # The mimetype entry must be first and stored uncompressed, or readers reject the book.
        mimetype = zipfile.ZipInfo("mimetype")
        mimetype.compress_type = zipfile.ZIP_STORED
        archive.writestr(mimetype, "application/epub+zip")
        archive.writestr("META-INF/container.xml", build_container_xml())
        archive.writestr(
            "OEBPS/content.opf",
            build_opf(chunks, title, author, lang, modified, identifier, cover_name, cover_media),
        )
        archive.writestr("OEBPS/nav.xhtml", build_nav_xhtml(title, lang, len(chunks)))
        archive.writestr("OEBPS/style.css", STYLE_CSS)
        if cover_name:
            archive.writestr(f"OEBPS/{cover_name}", cover.read_bytes())
            archive.writestr("OEBPS/cover.xhtml", build_cover_xhtml(title, lang, cover_name))
        for index, (_, _, translated) in enumerate(chunks, 1):
            archive.writestr(
                f"OEBPS/chunk{index:04d}.xhtml", build_chunk_xhtml(index, translated, lang)
            )


def verify_epub(out: Path, count: int) -> None:
    """Reopen the archive and assert the structural rules an EPUB reader relies on."""
    with zipfile.ZipFile(out) as archive:
        infos = archive.infolist()
        names = archive.namelist()

        first = infos[0]
        assert first.filename == "mimetype", f"mimetype must be the first entry, got {first.filename}"
        assert first.compress_type == zipfile.ZIP_STORED, "mimetype must be stored uncompressed"

        for required in ("META-INF/container.xml", "OEBPS/content.opf", "OEBPS/nav.xhtml"):
            assert required in names, f"missing required entry: {required}"

        documents = [name for name in names if name.endswith(".xhtml")]
        for index in range(1, count + 1):
            chunk = f"OEBPS/chunk{index:04d}.xhtml"
            assert chunk in names, f"missing chunk document: {chunk}"
        assert len(documents) >= count, "fewer XHTML documents than chunks"

        for name in documents:
            ET.fromstring(archive.read(name))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assemble translated light-novel chunks into a finished book."
    )
    parser.add_argument("--chunks-dir", required=True, type=Path,
                        help="directory of Japanese source chunks produced by chunk_source.py")
    parser.add_argument("--translated-dir", required=True, type=Path,
                        help="directory holding one '<same name>.txt' per chunk")
    parser.add_argument("--out", required=True, type=Path,
                        help="output file path")
    parser.add_argument("--format", choices=("txt", "bilingual", "epub"), default="epub",
                        help="output format (default: epub)")
    parser.add_argument("--title", default="Untitled", help="book title (default: Untitled)")
    parser.add_argument("--author", default="", help="book author (default: none)")
    parser.add_argument("--lang", default="zh", help="book language (default: zh)")
    parser.add_argument("--source-lang", default="ja",
                        help="source language tag (default: ja)")
    parser.add_argument("--cover", type=Path, default=None,
                        help="cover image to embed in the EPUB")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    chunks = load_chunks(args.chunks_dir, args.translated_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)

    if args.format == "txt":
        write_txt(chunks, args.out)
    elif args.format == "bilingual":
        write_bilingual(chunks, args.out)
    else:
        write_epub(chunks, args.out, args.title, args.author, args.lang, args.cover)

    paragraphs = sum(len(translated) for _, _, translated in chunks)
    if args.format == "epub":
        verify_epub(args.out, len(chunks))
        print(f"format: epub  source: {args.source_lang}  lang: {args.lang}  "
              f"chunks: {len(chunks)}  cover: {'yes' if args.cover else 'no'}")
        print(f"verified mimetype, container.xml, content.opf, nav.xhtml and "
              f"{len(chunks)} chunk document(s)")
    else:
        print(f"format: {args.format}  chunks: {len(chunks)}  paragraphs: {paragraphs}")
    print(f"wrote {args.out} ({args.out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
