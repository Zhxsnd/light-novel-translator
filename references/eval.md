# Measuring translation quality

"Accurate" is only a claim once it has been measured. Do this before declaring a prompt
version better than another.

## 1. Reserve a holdout

Split the source into `train` and `holdout` before tuning anything:

- Holdout = at least 10 chunks, or roughly 10% of the book.
- Never use a holdout chunk to pick glossary entries, write style samples, or adjust the prompt.
- Reuse the same holdout across every prompt version, otherwise the comparison is meaningless.

## 2. Score it

### Automatic (cheap, directional)

| Metric | Tool | Note |
|---|---|---|
| chrF | `sacrebleu` | Character n-gram F-score. The most useful automatic metric for Chinese |
| COMET | `unbabel-comet` | Learned metric, correlates better with humans, needs a GPU |
| BLEU | `sacrebleu` | Do **not** use alone for Chinese; word segmentation makes it unreliable |

Reference translations are required for both. Report chrF only when a reference exists;
otherwise fall back to the human rubric below.

### Human rubric (authoritative)

Score every holdout chunk 1–5 on five axes, blind to which prompt version produced it:

| Axis | 1 | 5 |
|---|---|---|
| Glossary consistency | names vary between chunks | every term matches the locked glossary |
| Character voice | all speakers sound identical | each speaker is recognisable from the line alone |
| 敬語 handling | flattened or literally mapped | register shifts preserved naturally |
| Fidelity | meaning added or dropped | nothing added, nothing lost |
| Fluency | reads like machine output | reads like a published light novel |

Report the mean per axis, not a single blended number — the axes fail independently.

## 3. Record the runs

Keep a table so a change can be justified later:

| Version | Model | chrF | Voice | Glossary | Notes |
|---|---|---|---|---|---|
| v1 | baseline prompt | | | | |
| v2 | + glossary | | | | |
| v3 | + retrieval examples | | | | |

## 4. Decide

- A prompt version ships only if it beats the previous one on the human rubric without
  regressing glossary consistency.
- If chrF rises but the human score does not, trust the human score.
- Re-check a delivered book by spot-reading three random chunks for glossary drift; the
  most common failure is a term that is correct in chunk 1 and different by chunk 40.
