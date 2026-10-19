#!/usr/bin/env python3
"""Translate Japanese light-novel chunks with any OpenAI-compatible chat endpoint.

Reads per-chunk text files, sends each one together with a locked glossary and the
light-novel style rules, and writes one output file per input chunk. Re-running skips
chunks whose output already exists and is non-empty, so an interrupted run resumes.

Only the standard library is used, so there is nothing to pip install.

Examples:
    export LNT_BASE_URL=http://127.0.0.1:8080/v1   # a local SakuraLLM server
    export LNT_MODEL=sakura
    python translate_chunks.py --chunks-dir chunks --glossary glossary.json --out-dir out

    python translate_chunks.py --chunks-dir chunks --dry-run   # print prompts, call nothing
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib import error, request

SUFFIXES = {".txt", ".md", ".ja", ".text"}

STYLE_RULES = """\
Light-novel style rules:
- Preserve each character's first-person pronoun (私/僕/俺/あたし/わたくし). Give every speaker
  a consistent, distinguishable voice. Never flatten them all to one word.
- Preserve speech quirks, dialect and catchphrases. Do not neutralise them.
- Honourifics さん/くん/ちゃん: keep the Japanese form when the relationship depends on it,
  otherwise render it naturally. Be consistent throughout.
- Ruby (ルビ) glosses are authorial intent. Keep them only when they carry meaning.
- Onomatopoeia and interjections are translated by feeling, not word for word.
- Reproduce paragraph breaks and line breaks exactly as in the source.
- Output the translation only. No notes, no explanations, no romanisation, no original text."""

SYSTEM_PROMPT = """\
You are a literary translator specialising in Japanese light novels and web novels.
Translate the user's text into {target}. The result must read like a published Chinese
light novel: natural, colloquial, and faithful to each character's voice.

{glossary_block}

{rules}"""


def load_glossary(path: Path | None) -> dict[str, str]:
    """Return a flat source -> target map. Missing or empty file means no glossary."""
    if path is None or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must contain a JSON object of source -> target strings")
    return {str(k): str(v) for k, v in data.items()}


SAMPLE_HEADING = "## Sample pairs"


def load_style_samples(text: str, source: Path) -> list[str]:
    """Return the sample blocks under the '## Sample pairs' heading.

    Everything above that heading is instructions for the person maintaining the file, so
    sending it to the model would waste context and confuse it with legal boilerplate.

    A block starts at a '### ' sub-heading and runs to the next one, so each block keeps its
    heading, its JA/ZH pair and any explanatory note together.
    """
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip().lower() == SAMPLE_HEADING.lower():
            start = index + 1
            break
    if start is None:
        raise SystemExit(
            f"{source} has no '{SAMPLE_HEADING}' heading. Style samples must sit under it."
        )

    body: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        body.append(line)

    blocks: list[list[str]] = []
    for line in body:
        if line.startswith("### ") and blocks:
            blocks.append([])
        if blocks:
            blocks[-1].append(line)
        elif line.strip():
            blocks.append([line])

    samples = [joined for joined in ("\n".join(b).strip() for b in blocks) if joined]
    if not samples:
        raise SystemExit(f"{source}: the '{SAMPLE_HEADING}' section is empty")
    return samples


def japanese_of(sample: str) -> str:
    """The JA halves of a sample block, used to score it against a chunk."""
    return " ".join(
        line.split("**JA:**", 1)[1] for line in sample.splitlines() if "**JA:**" in line
    )


def bigrams(text: str) -> set[str]:
    return {text[i:i + 2] for i in range(len(text) - 1)}


def pick_style_samples(samples: list[str], chunk: str, limit: int) -> list[str]:
    """Return the samples whose Japanese is closest to this chunk.

    Relevance is plain character-bigram overlap: crude, but it needs no embedding model, and
    it beats sending every sample once the corpus grows past a handful. Source order is kept
    so the prompt stays stable. A `limit` of 0, or one larger than the sample count, means
    send everything.
    """
    if limit <= 0 or limit >= len(samples):
        return samples
    chunk_grams = bigrams(chunk)
    ranked = sorted(
        range(len(samples)),
        key=lambda index: len(chunk_grams & bigrams(japanese_of(samples[index]))),
        reverse=True,
    )
    return [samples[index] for index in sorted(ranked[:limit])]


def build_messages(chunk: str, glossary: dict[str, str], target: str,
                   style_samples: list[str] | None = None,
                   context: str = "") -> list[dict]:
    if glossary:
        lines = "\n".join(f"{src} -> {dst}" for src, dst in glossary.items())
        block = (
            "MANDATORY GLOSSARY - use these exact renderings, never a variant:\n" + lines
        )
    else:
        block = "No glossary supplied. Keep proper nouns consistent with each other."

    rules = STYLE_RULES
    if style_samples:
        rules += (
            "\n\nReference pairs in the target register. Match their voice, honourific and "
            "pronoun choices, but never reuse their content:\n\n"
            + "\n\n".join(style_samples)
        )

    user = chunk
    if context.strip():
        user = (
            "Text immediately before this passage. It is context only: do NOT translate it, "
            "but keep pronouns, referents and tone continuous with it.\n"
            f"{context}\n\n"
            "--- translate only what follows ---\n"
            f"{chunk}"
        )

    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT.format(
                target=target, glossary_block=block, rules=rules
            ),
        },
        {"role": "user", "content": user},
    ]


def call_api(base_url: str, api_key: str, model: str, messages: list[dict],
             timeout: int, retries: int, temperature: float) -> str:
    url = base_url.rstrip("/") + "/chat/completions"
    payload = json.dumps(
        {"model": model, "messages": messages, "temperature": temperature}
    ).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key

    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            req = request.Request(url, data=payload, headers=headers, method="POST")
            with request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"].strip()
        except (error.URLError, error.HTTPError, KeyError, IndexError, ValueError) as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"API call failed after {retries} attempts: {last_error}")


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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Translate Japanese light-novel chunks via an OpenAI-compatible endpoint."
    )
    parser.add_argument("--chunks-dir", required=True, type=Path,
                        help="directory holding one file per chunk")
    parser.add_argument("--glossary", type=Path, default=Path("glossary.json"),
                        help="flat JSON map of source -> target (default: ./glossary.json)")
    parser.add_argument("--out-dir", type=Path, default=Path("out"),
                        help="directory for translations (default: ./out)")
    parser.add_argument("--target", default="Simplified Chinese",
                        help="target language (default: Simplified Chinese)")
    parser.add_argument("--base-url", default=os.environ.get("LNT_BASE_URL", ""),
                        help="endpoint root, e.g. http://127.0.0.1:8080/v1 (default: $LNT_BASE_URL)")
    parser.add_argument("--api-key", default=os.environ.get("LNT_API_KEY", ""),
                        help="bearer token (default: $LNT_API_KEY)")
    parser.add_argument("--model", default=os.environ.get("LNT_MODEL", ""),
                        help="model name (default: $LNT_MODEL)")
    parser.add_argument("--parallel", type=int, default=4,
                        help="concurrent requests (default: 4)")
    parser.add_argument("--style-samples", type=Path, default=None,
                        help="markdown file of Japanese-Chinese pairs to imitate, "
                             "e.g. references/style-samples.md")
    parser.add_argument("--samples-per-chunk", type=int, default=0,
                        help="send only the N style samples closest to each chunk "
                             "(default: 0, meaning send every sample)")
    parser.add_argument("--context-chars", type=int, default=300,
                        help="characters of the preceding chunk to send as read-only context "
                             "(default: 300, 0 disables)")
    parser.add_argument("--temperature", type=float, default=0.3)
    parser.add_argument("--timeout", type=int, default=300, help="seconds per request")
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--force", action="store_true",
                        help="re-translate chunks that already have output")
    parser.add_argument("--dry-run", action="store_true",
                        help="print what would be sent, call nothing")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    chunks = collect_chunks(args.chunks_dir)
    glossary = load_glossary(args.glossary)
    style_samples: list[str] = []
    if args.style_samples:
        if not args.style_samples.exists():
            raise SystemExit(f"style sample file not found: {args.style_samples}")
        style_samples = load_style_samples(
            args.style_samples.read_text(encoding="utf-8"), args.style_samples
        )
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"chunks: {len(chunks)}  glossary entries: {len(glossary)}  "
          f"style samples: {len(style_samples)}  context chars: {args.context_chars}  "
          f"out: {args.out_dir}")

    pending = []
    for index, path in enumerate(chunks):
        out_path = args.out_dir / f"{path.stem}.txt"
        if out_path.exists() and out_path.stat().st_size > 0 and not args.force:
            print(f"skip   {path.name}")
            continue
        source_text = path.read_text(encoding="utf-8")
        # Context comes from the preceding *source* chunk, never from its translation, so it
        # does not depend on which chunk finishes first and the run stays parallel-safe.
        context = ""
        if args.context_chars > 0 and index > 0:
            previous = chunks[index - 1].read_text(encoding="utf-8").strip()
            context = previous[-args.context_chars:]
        pending.append((path, out_path, source_text, context))

    if not pending:
        print("nothing to do")
        return 0

    if args.dry_run:
        path, _, source_text, context = pending[0]
        messages = build_messages(
            source_text, glossary, args.target,
            pick_style_samples(style_samples, source_text, args.samples_per_chunk),
            context,
        )
        print(f"\n--- system prompt ({path.name}) ---\n{messages[0]['content']}")
        print(f"\n--- user message (first 200 chars) ---\n{messages[1]['content'][:200]}")
        print(f"\nwould translate {len(pending)} chunk(s)")
        return 0

    if not args.base_url or not args.model:
        raise SystemExit("set --base-url and --model, or export LNT_BASE_URL and LNT_MODEL")

    failures = 0
    with ThreadPoolExecutor(max_workers=max(1, args.parallel)) as pool:
        futures = {
            pool.submit(
                lambda p, o, text, ctx: o.write_text(
                    call_api(
                        args.base_url, args.api_key, args.model,
                        build_messages(
                            text, glossary, args.target,
                            pick_style_samples(style_samples, text, args.samples_per_chunk),
                            ctx,
                        ),
                        args.timeout, args.retries, args.temperature,
                    ),
                    encoding="utf-8",
                ),
                path, out_path, source_text, context,
            ): path
            for path, out_path, source_text, context in pending
        }
        for future in as_completed(futures):
            path = futures[future]
            try:
                future.result()
                print(f"done   {path.name}")
            except Exception as exc:  # noqa: BLE001 - one bad chunk must not kill the run
                failures += 1
                print(f"failed {path.name}: {exc}", file=sys.stderr)

    if failures:
        print(f"{failures} chunk(s) failed; re-run to retry only those", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
