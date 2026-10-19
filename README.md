# light-novel-translator

**English** | [中文](README.zh-CN.md)

An agent skill for translating Japanese light novels (ラノベ and web novels) into Chinese
with a locked glossary, so character names, skill names and each speaker's own voice stay
consistent from the first chapter to the last.

Most translation tools treat a novel as one long document. This one treats it as a book: it
locks the terminology before translating a single line, carries context across chunk
boundaries, and measures the result before calling it finished.

## Install

Any agent that loads the open skills format can use this directly, because the repository
root is the skill itself.

```bash
npx skills add Zhxsnd/light-novel-translator
```

Or install it by hand — clone the repository and copy the folder into the skills directory
of whichever agent you use:

```bash
git clone https://github.com/Zhxsnd/light-novel-translator
cp -r light-novel-translator ~/.claude/skills/     # Claude Code
cp -r light-novel-translator ~/.trae-cn/skills/    # Trae (CN)
```

Nothing is installed globally and no code runs at install time.

## Requirements

- **Python 3.9+.** Every script uses the standard library only. There is nothing to `pip install`.
- **An OpenAI-compatible chat endpoint** — a local SakuraLLM server, DeepSeek, or anything
  else that speaks `/chat/completions`.

```bash
export LNT_BASE_URL=http://127.0.0.1:8080/v1   # or https://api.deepseek.com/v1
export LNT_API_KEY=sk-...
export LNT_MODEL=sakura                        # or deepseek-chat
```

SakuraLLM (`Sakura-GalTransl-7B`) is purpose-built for Japanese-to-Chinese light novels and
Galgame text, and beats a general model on this material. Two caveats: a quantised 7B needs
roughly 6 GB of VRAM, so it will not fit on a small laptop GPU, and its licence is
CC-BY-NC-SA, which means it must not be used to sell translations.

## Try it without an API key

Two commands show you what the skill actually does — no endpoint, no spend. Both run against
the original sample passage in `examples/`.

```bash
# split the sample passage into a chunk
python scripts/chunk_source.py --input examples/sample-source.txt --out-dir chunks

# print the exact request that would be sent to the model
python scripts/translate_chunks.py \
  --chunks-dir chunks --glossary examples/sample-glossary.json \
  --style-samples references/style-samples.md --dry-run
```

The second command calls nothing. It prints the system prompt — your locked glossary and the
style rules sit at the top of it — plus the head of the user message. That prompt is the whole
product; everything else is plumbing. `examples/README.md` explains what the passage is
designed to trip up.

## Quickstart

```bash
# 1. split the raw text into chapters and scenes
python scripts/chunk_source.py --input raws/novel.txt --out-dir chunks --max-chars 3500

# 2. (optional) mine terminology from a Japanese-Chinese parallel corpus
python scripts/mine_glossary.py --pairs pairs.jsonl --glossary-out glossary.json

# 3. translate, then read the transcript and confirm glossary.json with the user
python scripts/translate_chunks.py \
  --chunks-dir chunks --glossary glossary.json --out-dir out \
  --style-samples references/style-samples.md --context-chars 300

# 4. assemble the book
python scripts/export_book.py \
  --chunks-dir chunks --translated-dir out --out book.epub \
  --format epub --title "作品名" --author "著者" --lang zh
```

Interrupted partway through step 3? Run the same command again. Finished chunks are skipped.

## How it works

1. **Ingest** — normalise an EPUB, a なろう/カクヨム download, or plain text into per-chapter text.
2. **Lock the glossary** — extract every recurring proper noun and propose a rendering. The
   skill stops here and asks the user to confirm. This step is not optional.
3. **Chunk** — split on chapters, then on scene breaks. Never mid-line.
4. **Translate** — each request carries the glossary, the style rules, the most relevant
   style samples, and the tail of the previous chunk as read-only context.
5. **Verify** — check every glossary term, and look specifically for machine-translation
   tells such as `さん` rendered as `桑` or every speaker flattened to 我.
6. **Measure** — score a held-out set before claiming a prompt version is better. See
   `references/eval.md`.
7. **Export** — EPUB 3, bilingual, or plain text.

## Files

| Path | What it is |
|---|---|
| `SKILL.md` | The skill itself: the workflow the agent follows |
| `scripts/chunk_source.py` | Splits a raw text into chunks plus a hashed manifest |
| `scripts/mine_glossary.py` | Proposes glossary entries from a parallel corpus |
| `scripts/translate_chunks.py` | Runs the translation, with resume, retry and bounded context |
| `scripts/export_book.py` | Builds EPUB 3 / bilingual / plain text |
| `references/data-sources.md` | Where to legally obtain Japanese-Chinese parallel corpora |
| `references/eval.md` | How to measure quality instead of guessing |
| `references/glossary-base.md` | Genre baseline: recurring 異世界 vocabulary, locked up front |
| `references/style-samples.md` | Japanese-Chinese reference pairs, and the rules for sourcing them |
| `examples/` | Keyless demo: an original sample passage, its glossary, and what to check |

## Legal

Translating a work you do not hold the rights to, and then publishing or redistributing it,
is infringement. Both なろう and カクヨム forbid unauthorised public distribution of
translations. Fan translations are themselves copyrighted derivative works, so they must not
be committed to this repository either — see `references/style-samples.md` for what may
legally be used as reference material.

Use this on material you have the right to translate: your own writing, public-domain works,
or works whose author has granted a translation licence.

## License

MIT. See `LICENSE`.
