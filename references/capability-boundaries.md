# Capability Boundaries

An honest record of what this skill covers today, what it only partially covers, and
what it deliberately does not do. Deliberate exclusions are decisions, not gaps; this
file exists so you can tell the difference before committing a long book to it.

The skill is a harness. Fluency, taste, and prose quality are the model's ceiling —
`harness + model = output`. The skill fixes *consistency and process*; it cannot make a
weak model write well.

## Covered today

| Capability | How it is guaranteed |
|---|---|
| Term consistency across the whole book | Glossary locked at Step 2, verified chunk-by-chunk at Step 5 |
| Speaker voice separation | First-person pronouns preserved per character; style rules forbid flattening to 我 |
| Interrupted runs | Resume from disk; a finished chunk is never re-translated without `--force` |
| Deterministic parallel runs | Context comes from the previous *source* chunk, never a sibling translation |
| Valid EPUB 3 output | `mimetype` first and stored, every XHTML parsed before the file is reported written |
| Source formats | なろう / カクヨム (via `narou.rs`), EPUB, TXT, Markdown, OCR'd scanned PDFs |

## Partial — works, with known degradation

- **Glossary without a parallel corpus.** Guessing renderings from Japanese alone is
  workable but weaker; `mine_glossary.py` output is a candidate list, never a finished
  glossary. Quality of Step 2 scales directly with the corpus you bring.
- **Cross-chapter narrative coherence.** Only the last 300 characters of the previous
  source chunk carry across a boundary. Plot-level foreshadowing, running gags, and
  callbacks are not tracked. A nickname coined in chapter 39 will not link back to the
  chapter-1 name unless the Step-2 pre-scan caught both forms.
- **Ruby.** Stripped by default because most 《...》 glosses are noise. Meaning-carrying
  ruby — furigana name puns, gag readings — is lost unless `--keep-ruby` and a human
  decides per case.
- **Layout fidelity.** The EPUB is a clean reading edition, not a print replica.
  Illustrations are kept and reinserted; positioning, drop caps, and vertical text are not.
- **OCR quality is upstream.** The skill never sees page images; a bad OCR pass becomes
  a bad translation pass with no way to recover at translation time.
- **Evaluation is small-sample.** The 1–5 rubric is subjective, holdouts are ~10% of the
  book, and chrF is directional only. Scores inform decisions; they do not prove quality.
- **Unmarked speakers in dense dialogue.** When the source omits quotation attribution,
  speaker identification rests on the model reading the scene.

## Deliberate exclusions — decisions, not gaps

- **No single-pass whole-book mode.** Chunking with bounded context is the architecture,
  not a limitation to be lifted. A 400-chunk single prompt would trade determinism for a
  context window.
- **No fan-translation ingestion.** Never, not even as style samples. Legal boundary,
  see `references/style-samples.md`.
- **No automatic publishing or redistribution.** The skill stops at a local file.
  なろう and カクヨム forbid unauthorised public distribution of translations.
- **No translation memory / CAT workflow.** Segments are chapters and scenes, not
  sentences; there is no per-sentence TM or re-use across books.
- **No fine-tuning.** The only levers are prompt, glossary, and style samples. If that
  ceiling is too low, change the model, not this skill.
- **No other language pairs.** Japanese to Chinese only. The chunking and export
  plumbing is language-agnostic, but the style rules, glossary baseline, and machine-tell
  checks are not.
- **Not a general document translator.** Subtitles, manga, and business documents are
  out of scope by design.

## Verify before you trust it

Run the keyless demo first — it prints the exact request the model would receive:

```bash
python scripts/chunk_source.py --input examples/sample-source.txt --out-dir chunks
python scripts/translate_chunks.py --chunks-dir chunks \
  --glossary examples/sample-glossary.json \
  --style-samples references/style-samples.md --dry-run
```

What the demo cannot show you is the failure mode that only appears at length: proper-noun
drift between chapter 1 and chapter 40. The examples README says so explicitly. For a real
book, translate one chapter, read it against the source, and only then commit the run.
