#!/usr/bin/env python3
"""Mine a light-novel glossary from a Japanese-Chinese parallel corpus.

Given sentence pairs where a Japanese source line is aligned with a published Chinese
translation, this script proposes a rendering for every recurring proper noun by finding
the Chinese n-gram that co-occurs with it and with almost nothing else.

It only produces *candidates*. A human still confirms them before any translation starts.

Read the corpus as either:
  --pairs pairs.jsonl          one {"ja": "...", "zh": "..."} object per line
  --ja-file src.txt --zh-file trans.txt     line-aligned files

Only the standard library is used.

Examples:
    python mine_glossary.py --pairs pairs.jsonl --out candidates.json
    python mine_glossary.py --ja-file ja/01.txt --zh-file zh/01.txt \
        --min-support 3 --glossary-out glossary.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

KATAKANA = re.compile(r"[\u30a1-\u30f6\u30fc]{2,}")
KANJI_RUN = re.compile(r"[\u4e00-\u9fff\u3005]{2,6}")
CJK_RUN = re.compile(r"[\u4e00-\u9fff]{2,}")

MIN_NGRAM = 2
MAX_NGRAM = 4


def load_pairs(args) -> list[tuple[str, str]]:
    if args.pairs:
        pairs = []
        for lineno, line in enumerate(args.pairs.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if "ja" not in row or "zh" not in row:
                raise SystemExit(f"{args.pairs}:{lineno} needs both 'ja' and 'zh' keys")
            pairs.append((row["ja"], row["zh"]))
    elif args.ja_file and args.zh_file:
        ja_lines = [ln for ln in args.ja_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
        zh_lines = [ln for ln in args.zh_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if len(ja_lines) != len(zh_lines):
            raise SystemExit(
                f"line-aligned input needs equal line counts, got "
                f"{len(ja_lines)} ja vs {len(zh_lines)} zh"
            )
        pairs = list(zip(ja_lines, zh_lines))
    else:
        raise SystemExit("pass either --pairs, or both --ja-file and --zh-file")

    if not pairs:
        raise SystemExit("no usable sentence pairs found")
    return pairs


def candidates_in(japanese: str) -> set[str]:
    """Proper-noun-ish spans: katakana words, and kanji compounds."""
    found = set(KATAKANA.findall(japanese))
    found.update(m for m in KANJI_RUN.findall(japanese) if len(m) >= 2)
    return found


def ngrams_in(chinese: str) -> set[str]:
    """Every Chinese n-gram of length 2..4 inside a CJK run, deduplicated per sentence."""
    grams: set[str] = set()
    for run in CJK_RUN.findall(chinese):
        length = len(run)
        for size in range(MIN_NGRAM, MAX_NGRAM + 1):
            if length < size:
                continue
            for start in range(length - size + 1):
                grams.add(run[start:start + size])
    return grams


def confidence_of(precision: float, support: int) -> str:
    if precision >= 0.8 and support >= 3:
        return "high"
    if precision >= 0.5 and support >= 2:
        return "medium"
    return "low"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Propose glossary entries from a Japanese-Chinese parallel corpus."
    )
    parser.add_argument("--pairs", type=Path, help="JSONL with ja/zh keys")
    parser.add_argument("--ja-file", type=Path, help="line-aligned Japanese file")
    parser.add_argument("--zh-file", type=Path, help="line-aligned Chinese file")
    parser.add_argument("--out", type=Path, default=Path("glossary.candidates.json"),
                        help="candidate report (default: ./glossary.candidates.json)")
    parser.add_argument("--glossary-out", type=Path,
                        help="also write a flat source -> top-pick map for review")
    parser.add_argument("--min-support", type=int, default=2,
                        help="minimum sentences a candidate must appear in (default: 2)")
    parser.add_argument("--max-ratio", type=float, default=0.75,
                        help="drop candidates appearing in more than this share of sentences (default: 0.75)")
    parser.add_argument("--top", type=int, default=3,
                        help="alternatives kept per candidate (default: 3)")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    pairs = load_pairs(args)

    appears_in: dict[str, list[str]] = defaultdict(list)
    for japanese, chinese in pairs:
        for candidate in candidates_in(japanese):
            appears_in[candidate].append(chinese)

    global_counts: Counter[str] = Counter()
    for _, chinese in pairs:
        global_counts.update(ngrams_in(chinese))

    report: dict[str, dict] = {}
    for candidate, chinese_lines in appears_in.items():
        support = len(chinese_lines)
        if support < args.min_support:
            continue
        if support > len(pairs) * args.max_ratio:
            continue  # too ubiquitous to be a proper noun

        local: Counter[str] = Counter()
        for chinese in chinese_lines:
            local.update(ngrams_in(chinese))

        scored = []
        for gram, count in local.items():
            if count < args.min_support:
                continue
            scored.append((count / global_counts[gram], count, len(gram), gram))
        scored.sort(key=lambda row: (-row[0], -row[2], -row[1]))

        picks = []
        for precision, count, _, gram in scored:
            if any(gram in kept[3] for kept in picks):
                continue  # already covered by a longer, better pick
            picks.append((precision, count, _, gram))
            if len(picks) >= args.top:
                break
        if not picks:
            continue

        report[candidate] = {
            "pick": picks[0][3],
            "confidence": confidence_of(picks[0][0], support),
            "support": support,
            "options": [
                {
                    "zh": gram,
                    "precision": round(precision, 3),
                    "sentences": count,
                }
                for precision, count, _, gram in picks
            ],
        }

    if not report:
        print("nothing passed the filters; lower --min-support or widen the corpus")
        return 0

    # An option that is already the top pick of a different candidate is almost always a
    # name that merely co-occurs with this one, not an alternative rendering. Drop those so
    # the alternatives stay readable.
    top_pick_of = {entry["pick"]: candidate for candidate, entry in report.items()}
    for candidate, entry in report.items():
        entry["options"] = [
            option for option in entry["options"]
            if option["zh"] == entry["pick"]
            or top_pick_of.get(option["zh"], candidate) == candidate
        ]

    ordered = dict(sorted(
        report.items(),
        key=lambda item: (
            {"high": 0, "medium": 1, "low": 2}[item[1]["confidence"]],
            -item[1]["support"],
        ),
    ))

    args.out.write_text(
        json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{len(ordered)} candidates -> {args.out}")

    for candidate, entry in list(ordered.items())[: args.top * 10]:
        alternatives = " | ".join(o["zh"] for o in entry["options"][1:])
        line = f"  [{entry['confidence']:>6}] {candidate} -> {entry['pick']}  ({entry['support']}x)"
        print(line + (f"   alt: {alternatives}" if alternatives else ""))

    if args.glossary_out:
        flat = {candidate: entry["pick"] for candidate, entry in ordered.items()}
        args.glossary_out.write_text(
            json.dumps(flat, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"\nflat draft -> {args.glossary_out}")
        print("Review and correct every entry before translating. Candidates only reach the "
              "draft; unconfirmed guesses will be flagged, not silently used.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
