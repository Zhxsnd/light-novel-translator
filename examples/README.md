# Example

A keyless demo of the prompt pipeline. Both files here are **original text written for this
repository**, so no published work is involved and you can copy them freely.

| File | What it is |
|---|---|
| `sample-source.txt` | A short original Japanese passage, in the register of an 異世界 light novel |
| `sample-glossary.json` | The locked glossary for it |

## Run it with no API key

```bash
# 1. split the passage into a chunk
python scripts/chunk_source.py --input examples/sample-source.txt --out-dir chunks

# 2. print the exact request the translator would send — this calls nothing
python scripts/translate_chunks.py \
  --chunks-dir chunks --glossary examples/sample-glossary.json \
  --style-samples references/style-samples.md --dry-run
```

Step 2 needs no endpoint and spends nothing. What it prints is the product: the locked
glossary and the style rules sit in the system prompt, and the passage sits in the user
message. Everything else in this repository is plumbing around that one request.

`--dry-run` prints the first chunk that still needs translating. Delete `out/` and re-run to
see another one.

## What the passage is built to trip up

| In the source | What to check in the output |
|---|---|
| 僕 / 俺 / 私, three different speakers | Stay distinguishable. 俺 must not read like the narrator's 僕 |
| ユウキくん / リナさん | One honourific policy applied everywhere, not kept in one line and dropped in the next |
| 魔剣, スキル | A fixed rendering for the whole book, never a synonym of the moment |
| 『フレイムバースト』 | A katakana skill name — transliterated or translated, but identically at every appearance |
| 第一章　森の入口 | A chapter heading, not prose. It survives as structure, not as a translated sentence |

## The failure this sample cannot show you

Name drift is what actually ruins a long book: 悠纪 in chapter 1 becomes 优希 by chapter 40,
because each chunk was translated in isolation. A passage this short leaves no room for that
to happen — you need a whole book and three spot-read chunks at the end. The method is in
`references/eval.md`.

## An illustrative comparison

The two renderings below are **hand-written illustration, not model output**. They point at
where the choices differ; they are not a measured result. Run the commands above for real
output.

The opening of the sample:

```
　「ユウキくん、本当に行くの？」
　リナさんが心配そうに僕の袖を引いた。その手は少し震えていた。
　「ああ、行くよ」
```

The failure mode is not a bad sentence, it is an unmade decision: with no policy to follow,
each line is settled on its own, keeping the Japanese くん here and dissolving さん into
nothing there.

```
「悠纪君，真的要去吗？」
莉娜担心地拽了拽我的袖子。那只手在微微发抖。
「嗯，去。」
```

The same passage under one locked policy — `さん` localised, `くん` dropped between peers,
both quoted from `sample-glossary.json`:

```
「悠纪，真的要去吗？」
莉娜小姐担心地拽了拽我的袖子。那只手在微微发抖。
「嗯，要去。」
```

Either choice is defensible on its own. The problem is a book that renders the same
relationship four different ways by chapter 12.
