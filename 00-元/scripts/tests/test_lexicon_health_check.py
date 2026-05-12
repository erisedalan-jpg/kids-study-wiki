"""测试 lexicon_health_check 的纯逻辑：LLM 输出解析 + lexicon 比对。"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lexicon_health_check import (  # noqa: E402
    compare_to_lexicon,
    parse_llm_output,
)


class TestParseLLMOutput(unittest.TestCase):
    def test_normal_two_lines(self):
        s = "集合的运算, 并集, 子集\n完整"
        r = parse_llm_output(s)
        self.assertEqual(r["concepts"], ["集合的运算", "并集", "子集"])
        self.assertTrue(r["ocr_complete"])
        self.assertEqual(r["ocr_note"], "")

    def test_with_prefix(self):
        s = "考点: 函数最值, 单调性\n完整"
        r = parse_llm_output(s)
        self.assertEqual(r["concepts"], ["函数最值", "单调性"])

    def test_chinese_separators(self):
        s = "导数、复合函数；链式法则\n完整"
        r = parse_llm_output(s)
        self.assertEqual(r["concepts"], ["导数", "复合函数", "链式法则"])

    def test_ocr_incomplete(self):
        s = "复数\n不完整: 缺虚部表达式"
        r = parse_llm_output(s)
        self.assertFalse(r["ocr_complete"])
        self.assertEqual(r["ocr_note"], "缺虚部表达式")

    def test_empty_returns_parse_error(self):
        r = parse_llm_output("")
        self.assertEqual(r["concepts"], [])
        self.assertIn("parse_error", r)

    def test_whitespace_only(self):
        r = parse_llm_output("   \n\n  ")
        self.assertIn("parse_error", r)

    def test_no_second_line(self):
        # LLM 只输出第一行 → ocr_complete=False（保守）
        r = parse_llm_output("函数, 导数")
        self.assertEqual(r["concepts"], ["函数", "导数"])
        self.assertFalse(r["ocr_complete"])


class TestCompareToLexicon(unittest.TestCase):
    def test_all_matched(self):
        lex = {"函数": {"bare": "函数"}, "导数": {"bare": "导数"}}
        matched, gaps = compare_to_lexicon(["函数", "导数"], lex)
        self.assertEqual(matched, ["函数", "导数"])
        self.assertEqual(gaps, [])

    def test_mixed(self):
        lex = {"函数": {"bare": "函数"}}
        matched, gaps = compare_to_lexicon(["函数", "复数"], lex)
        self.assertEqual(matched, ["函数"])
        self.assertEqual(gaps, ["复数"])

    def test_alias_in_lexicon_counts_as_match(self):
        # lexicon 顶层 key 含所有 alias（与实际格式一致）
        lex = {
            "并集": {"bare": "集合的运算"},
            "union": {"bare": "集合的运算"},
            "集合的运算": {"bare": "集合的运算"},
        }
        matched, gaps = compare_to_lexicon(["并集"], lex)
        self.assertEqual(matched, ["并集"])


if __name__ == "__main__":
    unittest.main()
