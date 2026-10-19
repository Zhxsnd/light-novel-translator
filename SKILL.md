---
name: light-novel-translator
description: Translate Japanese light novel raws into Chinese with a locked character/skill glossary. Use when asked to translate 生肉, なろう or カクヨム novels, or light novel EPUB/TXT.
---

# Light Novel Translator

Translate Japanese light novels (ラノベ and web novels) into Chinese while keeping
character names, honourifics, skill names, and narration voice consistent across the
whole book.

## Non-negotiables

- Never translate a whole book in one pass. Chunk it and carry only a bounded context.
- Never skip Step 2. A glossary the user has confirmed is the single biggest quality lever.
- Never invent explanations, footnotes, or content that is not in the source.
- Never commit a third-party fan translation into this repository, not even as a style
  sample. `references/style-samples.md` states what may legally be used.
- Never publish or redistribute a translation of a work you have no rights to. Both
  なろう and カクヨム forbid unauthorised public distribution of translations.

## Workflow

### 1. Ingest

Normalise the source into per-chapter plain text.

| Source | How |
|---|---|
| なろう / カクヨム URL | `narou.rs` or `narou.rb` to download as EPUB, then unzip and read the XHTML in spine order |
| Existing EPUB | Unzip and read XHTML in spine order. Do not trust the order of the TOC file |
| TXT / Markdown | Split on chapter headings (`第N話`, `第N章`, `#`, `##`) |
| Scanned PDF | OCR first (MinerU or Marker). Never send page images to the translator |

Drop ruby noise, navigation links, and author afterwords before translating. Keep the
illustration files so they can be reinserted on export.

### 2. Pre-scan and lock the glossary — STOP AND ASK

This pass extracts, it does not translate prose.

1. Start from the genre baseline in `references/glossary-base.md`. It fixes the system and
   item vocabulary that recurs across every 異世界 work — スキル, ギルド, レベル and the rest.
   Skip this step for a work outside that genre.
2. Extract every recurring proper noun: character names, nicknames, skill and magic
   names, organisations, places, titles, and recurring honourifics.
3. Propose one rendering each. If a Japanese-Chinese parallel corpus is available, run
   `scripts/mine_glossary.py` first — it proposes renderings from co-occurrence with the
   published translation, which beats guessing from the Japanese alone. Its output is a
   candidate list, not a finished glossary.
4. Write `glossary.json` as a flat source-to-target map:

```json
{
  "ユウキ": "悠纪",
  "魔剣": "魔剑",
  "さん": "（保留）"
}
```

5. Stop and show the glossary to the user. Do not start translating until they confirm
   or correct it. Flag ambiguous names instead of guessing them.

### 3. Chunk

Run `scripts/chunk_source.py`. It splits on chapter headings (`第N話`, `第N章`, markdown
`#`), breaks oversized chapters at blank-line boundaries, never cuts mid-line, strips ruby
unless `--keep-ruby` is given, and writes a manifest with each chunk's size and SHA-256.

```bash
python scripts/chunk_source.py --input raws/novel.txt --out-dir chunks --max-chars 3500
```

3500 characters is the sweet spot in practice: long enough to hold a whole scene, short
enough that one failed request is cheap to retry.

### 4. Translate

Run `scripts/translate_chunks.py`. Every request carries the locked glossary, the style
rules, the most relevant style samples, and the tail of the previous chunk as read-only
context. It resumes from whatever is already on disk.

```bash
python scripts/translate_chunks.py \
  --chunks-dir chunks --glossary glossary.json --out-dir out --parallel 4 \
  --style-samples references/style-samples.md --samples-per-chunk 4 --context-chars 300
```

- `--context-chars` (default 300) prepends the tail of the *previous source* chunk so
  pronouns and referents carry across the boundary. It is the previous source, never the
  previous translation, which is what keeps a parallel run deterministic. Set `0` to disable.
- `--samples-per-chunk` (default 0) sends only the N style samples with the most character
  overlap with each chunk. `0` sends every sample, which is right for a short
  `references/style-samples.md` and wrong once the sample file grows past a handful.
- Chunks are independent and retried with exponential backoff. A finished chunk is never
  re-translated unless `--force` is passed.

### 5. Verify

- Check that every glossary term appears in the output exactly as specified.
- Check for machine-translation tells: `さん` rendered as `桑`, flattened 敬語, a single
  first-person pronoun for every speaker, dropped speech quirks.
- Re-translate only the offending chunks with `--force`.

### 6. Measure — do not skip this on a long book

Only claim one prompt version beats another once it has been scored. Method in
`references/eval.md`.

- Hold out at least 10 chunks, or about 10% of the book, and never use them for glossary
  mining or style samples.
- Score each holdout chunk 1–5 on glossary consistency, character voice, 敬語 handling,
  fidelity, and fluency. Report per axis, blind to which prompt version produced it.
- chrF is a useful directional signal; it is not a verdict on its own.
- A change ships only if it wins on the rubric without regressing glossary consistency.
- Before delivery, spot-read three random chunks for glossary drift. The usual failure is a
  name that is correct in chunk 1 and different by chunk 40.

### 7. Export

Run `scripts/export_book.py`. It walks the chunk and translation directories in order, fails
loudly when a chunk has no translation, and writes one of three formats.

```bash
python scripts/export_book.py \
  --chunks-dir chunks --translated-dir out --out book.epub \
  --format epub --title "作品名" --author "著者" --lang zh --source-lang ja
```

| `--format` | Output |
|---|---|
| `epub` | Valid EPUB 3, built with the standard library. Cover and illustrations optional |
| `bilingual` | Japanese paragraph then its translation. Good for study and proofing |
| `txt` | Translation only. Clean reading edition |

The EPUB is checked as it is written: `mimetype` is the first entry and stored uncompressed,
and every XHTML document is parsed before the file is reported as written.

## Reference corpus

A Japanese-Chinese parallel corpus is the highest-value asset this skill can have. It
supplies two things:

- **Glossary candidates** for `scripts/mine_glossary.py`.
- **Style samples** for `references/style-samples.md`, injected into every translation request.

Source it legally: your own past translations, public-domain works (Aozora Bunko originals
plus a public-domain Chinese translation), or works whose author has granted a translation
licence. Never commit a fan translation. `references/data-sources.md` lists where to find each
kind of corpus and what its licence actually permits. Mine corpora locally and commit only the
derived glossary — a term mapping is factual, translated text is not.

When no corpus exists, skip straight to Step 3. Guessing the glossary from the Japanese
alone is workable, just weaker.

## Style rules

Match the register in `references/style-samples.md` whenever that file has content.

- Preserve each character's first-person pronoun (私 / 僕 / 俺 / あたし / わたくし). Give each
  speaker a consistent, distinguishable voice; never flatten them all to 我.
- Preserve speech quirks, dialect, and catchphrases.
- 敬称 (さん / くん / ちゃん): localise when it reads naturally, keep the Japanese form when
  the relationship depends on it. Ask the user once for a global choice.
- Ruby (ルビ) glosses are authorial intent. Keep them only when they carry meaning.
- Onomatopoeia and interjections translate by feeling, not word for word.
- Reproduce paragraph and line breaks exactly as in the source.

## Configuration

`scripts/translate_chunks.py` reads an OpenAI-compatible endpoint from the environment:

| Variable | Meaning |
|---|---|
| `LNT_BASE_URL` | e.g. a local SakuraLLM server, or `https://api.deepseek.com/v1` |
| `LNT_API_KEY` | API key, if the endpoint needs one |
| `LNT_MODEL` | model name |

SakuraLLM (Sakura-GalTransl-7B) is purpose-built for Japanese-to-Chinese light novels and
Galgame text; prefer it over a general model when available. Its licence is CC-BY-NC-SA,
so it must not be used to sell translation.

## Do not use this skill for

Subtitle, manga, or business document translation.
