"""测试 v4-pro 摘要+考点抽取。"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exam_enrich import parse_llm_output, enrich_question, SYSTEM_PROMPT  # noqa: E402


class TestParseLLMOutput(unittest.TestCase):
    def test_normal_three_lines(self):
        text = "考集合的交集运算\n集合的运算, 并集\n易"
        r = parse_llm_output(text)
        self.assertEqual(r["summary"], "考集合的交集运算")
        self.assertEqual(r["tags"], ["集合的运算", "并集"])
        self.assertEqual(r["difficulty"], "易")

    def test_chinese_separators(self):
        text = "线性规划题\n线性规划、约束条件；最值\n中"
        r = parse_llm_output(text)
        self.assertEqual(set(r["tags"]), {"线性规划", "约束条件", "最值"})

    def test_with_prefix(self):
        text = "摘要：考向量数量积\n考点：向量数量积, 向量模\n难度：难"
        r = parse_llm_output(text)
        self.assertIn("向量数量积", r["summary"])
        self.assertIn("向量数量积", r["tags"])
        self.assertEqual(r["difficulty"], "难")

    def test_empty_returns_error(self):
        r = parse_llm_output("")
        self.assertIn("parse_error", r)


class TestEnrichQuestion(unittest.TestCase):
    @patch("exam_enrich.call")
    def test_basic_enrich(self, mock_call):
        mock_call.return_value = MagicMock(
            text="考集合运算\n集合的运算, 并集\n易",
            model="deepseek-v4-pro",
        )
        q = {"qno": 1, "solution_text": "M 与 N 的交集计算..."}
        result = enrich_question(q)
        self.assertEqual(result["summary"], "考集合运算")
        self.assertEqual(result["tags"], ["集合的运算", "并集"])
        self.assertEqual(result["difficulty"], "易")


if __name__ == "__main__":
    unittest.main()
