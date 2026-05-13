"""测试 markitdown 元数据抽取。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exam_extract_meta import (  # noqa: E402
    extract_answer,
    extract_solution_text,
    split_by_question,
)


class TestSplitByQuestion(unittest.TestCase):
    def test_split_basic(self):
        md = """前置文本
1. 第一题题面
【答案】A
【解析】xxx
2. 第二题题面
【答案】B
"""
        chunks = split_by_question(md)
        self.assertEqual(set(chunks.keys()), {1, 2})
        self.assertIn("第一题题面", chunks[1])
        self.assertIn("第二题题面", chunks[2])

    def test_split_skips_decimal_in_table(self):
        """0.04 在表格里不应被识别为题号 0."""
        md = """1. 题面
0.04 0.06
【答案】A
"""
        chunks = split_by_question(md)
        self.assertEqual(list(chunks.keys()), [1])


class TestExtractAnswer(unittest.TestCase):
    def test_simple_letter(self):
        chunk = "题面\n【答案】A\n【解析】..."
        self.assertEqual(extract_answer(chunk), "A")

    def test_spaced_bracket(self):
        chunk = "题面\n【 答 案 】B\n【解析】..."
        self.assertEqual(extract_answer(chunk), "B")

    def test_multi_choice(self):
        chunk = "题面\n【答案】ABD\n"
        self.assertEqual(extract_answer(chunk), "ABD")

    def test_truncates_long_answer(self):
        """答案字段超过 50 字符截断（防答案块整体串入）。"""
        long_text = "x" * 100
        chunk = f"题面\n【答案】{long_text}\n"
        result = extract_answer(chunk)
        self.assertLessEqual(len(result), 50)

    def test_strips_markdown_table_remnants(self):
        """markitdown 把答案塞进表格 cell 时去掉 | 和 ##。"""
        chunk = "题面\n| 【答案】 | ##0.3 |     |     |     |     |"
        self.assertEqual(extract_answer(chunk), "0.3")

    def test_strips_heading_prefix(self):
        """## 前缀是 markitdown 把数字误判为 heading 残留，需去除。"""
        chunk = "题面\n【答案】##5\n"
        self.assertEqual(extract_answer(chunk), "5")


class TestExtractSolutionText(unittest.TestCase):
    def test_captures_analysis_and_detail(self):
        chunk = "【答案】A\n【解析】\n【分析】先算...\n【详解】具体...\n"
        sol = extract_solution_text(chunk)
        self.assertIn("先算", sol)
        self.assertIn("具体", sol)

    def test_empty_when_no_solution_marker(self):
        chunk = "题面\n【答案】A\n"
        self.assertEqual(extract_solution_text(chunk), "")


if __name__ == "__main__":
    unittest.main()
