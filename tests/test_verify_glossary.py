#!/usr/bin/env python3
"""Tests for scripts/verify_glossary.py.

Run from the repository root:

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import verify_glossary as vg  # noqa: E402

BASE_GLOSSARY = {
    "ユウキ": "悠纪",
    "リナ": "莉娜",
    "魔剣": "魔剑",
    "さん": "（保留）",
}


class VerifyGlossaryTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    # -- helpers ---------------------------------------------------------

    def write(self, subdir: str, name: str, text: str) -> Path:
        directory = self.root / subdir
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / name
        path.write_text(text, encoding="utf-8")
        return path

    def run_main(self, argv: list[str]) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            code = vg.main(argv)
        return code, out.getvalue()

    def run_case(self, translated: dict[str, str],
                 chunks: dict[str, str] | None = None,
                 glossary: dict[str, str] | None = None,
                 extra: list[str] | None = None) -> tuple[int, str]:
        for name, text in (chunks or {}).items():
            self.write("chunks", name, text)
        for name, text in translated.items():
            self.write("out", name, text)
        glossary_path = self.root / "glossary.json"
        glossary_path.write_text(
            json.dumps(glossary if glossary is not None else BASE_GLOSSARY,
                       ensure_ascii=False),
            encoding="utf-8",
        )
        argv = ["--translated-dir", str(self.root / "out"),
                "--glossary", str(glossary_path)] + (extra or [])
        if chunks is not None:
            argv += ["--chunks-dir", str(self.root / "chunks")]
        return self.run_main(argv)

    # -- cases -----------------------------------------------------------

    def test_01_clean_translation_exits_zero(self) -> None:
        code, out = self.run_case(
            chunks={"chunk0001.txt": "　「ユウキくん、行くの？」"},
            translated={"chunk0001.txt": "「悠纪君，要去吗？」"},
        )
        self.assertEqual(0, code)
        self.assertIn("violations: 0", out)
        self.assertIn("suspects: 0", out)

    def test_02_kana_remnant_is_a_violation(self) -> None:
        code, out = self.run_case(
            translated={"chunk0001.txt": "莉娜看着「ユウキ」的背影。"},
        )
        self.assertEqual(1, code)
        self.assertIn("chunk0001.txt", out)
        self.assertIn("C1", out)
        self.assertIn("ユウキ", out)

    def test_03_kept_honourific_is_whitelisted(self) -> None:
        code, out = self.run_case(
            translated={"chunk0001.txt": "莉娜さん笑了笑。"},
        )
        self.assertEqual(0, code)
        self.assertNotIn("C1", out)

    def test_04_identity_target_is_whitelisted(self) -> None:
        code, out = self.run_case(
            glossary={"アリス": "アリス"},
            translated={"chunk0001.txt": "アリス站在门口。"},
        )
        self.assertEqual(0, code)

    def test_05_honourific_tell_is_a_suspect(self) -> None:
        code, out = self.run_case(
            translated={"chunk0001.txt": "悠纪桑微笑着接过剑。"},
        )
        self.assertEqual(0, code)  # suspects alone do not fail
        self.assertIn("C2", out)
        self.assertIn("悠纪桑", out)

    def test_06_strict_fails_on_suspects(self) -> None:
        code, _ = self.run_case(
            translated={"chunk0001.txt": "悠纪桑微笑着接过剑。"},
            extra=["--strict"],
        )
        self.assertEqual(1, code)

    def test_07_pronoun_flattening_is_a_suspect(self) -> None:
        code, out = self.run_case(
            chunks={"chunk0001.txt": "　「僕も行く」\n\n　「俺が行く」"},
            translated={"chunk0001.txt": "「我也去。」\n\n「我去。」"},
        )
        self.assertEqual(0, code)
        self.assertIn("C3", out)

    def test_08_single_source_pronoun_is_not_flagged(self) -> None:
        code, out = self.run_case(
            chunks={"chunk0001.txt": "　「僕が行く」"},
            translated={"chunk0001.txt": "「我去。」"},
        )
        self.assertEqual(0, code)
        self.assertNotIn("C3", out)

    def test_09_c3_skipped_without_chunks_dir(self) -> None:
        code, out = self.run_case(
            chunks=None,
            translated={"chunk0001.txt": "莉娜看着「ユウキ」的背影。"},
        )
        self.assertEqual(1, code)  # C1 still fires
        self.assertIn("C3", out)

    def test_10_missing_translated_dir_is_a_usage_error(self) -> None:
        glossary_path = self.root / "glossary.json"
        glossary_path.write_text("{}", encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            vg.main(["--translated-dir", str(self.root / "nope"),
                     "--glossary", str(glossary_path)])
        self.assertEqual(2, ctx.exception.code)

    def test_11_malformed_glossary_is_a_usage_error(self) -> None:
        out_dir = self.write("out", "chunk0001.txt", "正文")
        for bad in ("{not json", json.dumps({"魔剣": 3}, ensure_ascii=False)):
            path = self.root / "glossary.json"
            path.write_text(bad, encoding="utf-8")
            with self.assertRaises(SystemExit) as ctx:
                vg.main(["--translated-dir", str(out_dir.parent),
                         "--glossary", str(path)])
            self.assertEqual(2, ctx.exception.code)

    def test_12_finding_at_text_edges_does_not_crash(self) -> None:
        code, out = self.run_case(
            translated={
                "chunk0001.txt": "ユウキ朝着门口走去。",  # run at the very start
                "chunk0002.txt": "众人在暮色里喊ユウキ",  # run at the very end
            },
        )
        self.assertEqual(1, code)
        self.assertEqual(2, out.count("C1"))

    def test_13_multi_chunk_report_is_exact(self) -> None:
        code, out = self.run_case(
            translated={
                "chunk0001.txt": "悠纪点了点头。",
                "chunk0002.txt": "他看向ユウキ。",  # the only violation
                "chunk0003.txt": "门打开了。",
            },
        )
        self.assertEqual(1, code)
        self.assertEqual(1, out.count("C1"))
        self.assertIn("chunk0002.txt", out)
        self.assertIn("violations: 1", out)


if __name__ == "__main__":
    unittest.main()
