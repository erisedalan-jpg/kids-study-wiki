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
        q = {"qno": 1, "solution_text": "M 与 N 的交集计算过程，含集合的并集和交集运算"}
        result = enrich_question(q)
        self.assertEqual(result["summary"], "考集合运算")
        self.assertEqual(result["tags"], ["集合的运算", "并集"])
        self.assertEqual(result["difficulty"], "易")

    @patch("exam_enrich.call")
    def test_enrich_retries_on_parse_error(self, mock_call):
        """第一次解析失败 → retry t=0.5 max=600；第二次成功。"""
        from exam_enrich import LLMError  # noqa
        # 第一次返回空（触发 parse_error），第二次返回正常
        mock_call.side_effect = [
            MagicMock(text="", model="deepseek-v4-pro"),
            MagicMock(text="考点摘要\n概念A, 概念B\n中", model="deepseek-v4-pro"),
        ]
        q = {"qno": 1, "solution_text": "M 与 N 的交集运算 集合 元素 包含关系 求解过程"}
        result = enrich_question(q)
        self.assertEqual(mock_call.call_count, 2)
        # 第二次调用 temperature 应为 0.5
        second_call_kwargs = mock_call.call_args_list[1].kwargs
        self.assertEqual(second_call_kwargs.get("temperature"), 0.5)
        self.assertEqual(second_call_kwargs.get("max_tokens"), 600)
        # 最终成功
        self.assertEqual(result["tags"], ["概念A", "概念B"])

    @patch("exam_enrich.call")
    def test_enrich_returns_parse_error_on_llm_error(self, mock_call):
        """LLMError 直接返回 parse_error（不 retry）。"""
        from exam_enrich import LLMError
        mock_call.side_effect = LLMError("429 rate limit")
        q = {"qno": 1, "solution_text": "M 与 N 的交集运算 集合 元素 包含关系 求解过程"}
        result = enrich_question(q)
        # LLMError 不应触发 retry
        self.assertEqual(mock_call.call_count, 1)
        self.assertIn("parse_error", result)
        self.assertIn("429", result["parse_error"])


if __name__ == "__main__":
    unittest.main()
