# Data sources for Japanese-Chinese translation work

Where to get ja-zh parallel data, what each source is actually good for, and what you are
allowed to do with it afterwards.

## Two rules that override everything else

1. **Corpora never go into this repository.** The good ones run from hundreds of megabytes to
   gigabytes, and several are licensed for research use only. Mine them locally, commit only
   the derived `glossary.json`.
2. **A literary source needs both sides public domain.** A public-domain Japanese original is
   not enough: the Chinese translation must also be free of copyright, which in practice means
   the translator died more than 50 years ago (China) or 70 years ago (Japan and the EU).
   Getting this wrong is the one mistake that can actually get a repository taken down.

A glossary of term-to-term mappings is factual information and is not itself infringing. The
translated text is. That distinction is what makes this skill publishable at all.

## General corpora

| Source | ja-zh pairs | Content | Licence | Best for |
|---|---|---|---|---|
| OPUS (all ja-zh subcorpora) | ~28.4M across 28 subcorpora | mixed | varies per subcorpus — check each | the entry point; filter by subcorpus |
| CCMatrix v1 | 12,403,136 | web crawl | unstated by OPUS | volume, when nothing better exists |
| LinguaTools-WikiTitles | 1,661,274 | Wikipedia article titles | CC-BY-SA family | **proper nouns: people, places, organisations** |
| XLEnt v1.2 | 1,396,117 | dictionary and entity pairs | unconfirmed | transliteration of names |
| WikiMatrix | 267,410 | Wikipedia prose | CC-BY-SA 4.0 | **clean terminology seeds** |
| OpenSubtitles | ~1.09M | film and TV subtitles | attribution to opensubtitles.org | **dialogue register, closest to light-novel speech** |
| JParaCrawl Chinese v2.0 | 4.6M | crowdsourced bilingual sites | ⚠️ research use only, no commercial use | bulk mining |
| WCC-JC 2.0 | ~1.4M | film and anime subtitles | ⚠️ research use only, full set by email request | **spoken language; a demo ships on GitHub** |
| JPO 中日対訳コーパス | 130M | patent filings | ⚠️ ALAGIN membership, contract, no commercial use, shipped on a hard drive | nothing — wrong domain |
| ASPEC-JC | 679K train | scientific paper abstracts | ⚠️ yearly application | nothing — wrong domain |

Two downloads need no application at all:

- `huggingface.co/datasets/larryvrh/CCMatrix-v1-Ja_Zh-filtered` — 5.69M rows, filtered, plain parquet.
- `huggingface.co/datasets/Helsinki-NLP/tatoeba_mt` — test and dev splits only, CC-BY-2.0. A
  good holdout set for Step 6.

## Pick by task, not by size

| Task | Use |
|---|---|
| Glossary: names, places, skills | WikiTitles, then WikiMatrix, then CCMatrix as filler |
| Style samples | OpenSubtitles and WCC-JC 2.0 |
| Evaluation holdout | `tatoeba_mt`, or ASPEC-JC if you want a second domain |
| Literary register | 《现代日本小说集》 (1923) — public domain on both sides |

Size is not a proxy for usefulness here. WikiTitles has 1.7M pairs and is far more useful for
a glossary than CCMatrix's 12.4M. Start with the small, clean ones.

Do not run `scripts/mine_glossary.py` over a multi-million-pair corpus. Pure-Python n-gram
scanning is slow enough to be unusable at that scale, and terminology is by definition
high-frequency: the first 200,000 pairs capture essentially all of it.

## Literary sources

Light novels are narrative fiction, so literary corpora ought to be the best fit. They are
also the hardest to obtain legally.

| Source | Content | Status |
|---|---|---|
| 中日对译语料库 (CJPC), BFSU 北京日本学研究中心 | ~11.3M characters; 22 Japanese and 23 Chinese originals including 坊ちゃん, こころ, 羅生門, 雪国, ノルウェイの森, 金閣寺 | ⚠️ Content is ideal. Distribution has stopped; needs the centre's permission, and past holders may not redistribute |
| 《现代日本小说集》 (1923), translated by 鲁迅 and 周作人 | 30 stories by 15 authors | ✅ Public domain on both sides. The only literary corpus that can go into a public repository |
| Aozora Bunko 青空文庫 | Japanese public-domain originals | ✅ Japanese side only — you must supply the Chinese side |
| なろう / カクヨム author permissions | Web novels | ⚠️ No central list of translation-permitted works. Check each author's 近況ノート |
| Official Chinese light-novel editions (台湾角川, 天闻角川) | Licensed translations | ❌ Strong DRM. Stripping it and redistributing is illegal |
| Learner editions such as 宇航社《日本文学鉴赏》 | Bilingual literary editions | ⚠️ Fine for personal study, not redistributable |

The practical conclusion: **there is no legal, ready-made, literary ja-zh corpus of any useful
size.** Hand-build style samples from a handful of public-domain pairs, and treat everything
else as personal reference material you never commit.

## What to avoid

- HuggingFace `bh2821/LightNovel5000` and similar crawls of fan translations. This is exactly
  the material `references/style-samples.md` forbids. Importing it would put in your repository
  the same problem these rules exist to prevent.
- Stripping DRM from commercial e-books to build a parallel corpus.
- Committing any translated text you did not write yourself and that is not verifiably public
  domain.
