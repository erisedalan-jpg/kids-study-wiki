"""测试 ocr_sample_check 的纯逻辑：题号窗口定位 + LLM 输出解析。"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ocr_sample_check import find_question_window, parse_llm_verdict  # noqa: E402


class TestFindQuestionWindow(unittest.TestCase):
    def test_locates_qno_in_middle(self):
        text = "前置内容\n1. 第一题题面\n2. 第二题 abc\n3. 第三题 xyz\n"
        win = find_question_window(text, qno=2, window=20)
        self.assertIn("第二题", win)
        self.assertIn("2. 第二题", win)

    def test_falls_back_to_first_1200_chars_if_qno_missing(self):
        text = "无题号的文本" * 300
        win = find_question_window(text, qno=99)
        self.assertEqual(win, text[:1200])

    def test_handles_chinese_punctuation(self):
        # 题号后是中文句号"．"
        text = "1．第一题\n2．第二题 abc\n"
        win = find_question_window(text, qno=2, window=10)
        self.assertIn("第二题", win)


class TestParseLLMVerdict(unittest.TestCase):
    def test_pass_two_lines(self):
        v = parse_llm_verdict("通过\n切分版本完整对应原文")
        self.assertFalse(v["has_issue"])
        self.assertEqual(v["issue_type"], "无")
        self.assertEqual(v["summary"], "切分版本完整对应原文")

    def test_pass_with_prefix(self):
        v = parse_llm_verdict("结论: 通过\n理由: 内容一致")
        self.assertFalse(v["has_issue"])
        self.assertEqual(v["issue_type"], "无")

    def test_formula_issue(self):
        v = parse_llm_verdict("公式乱码\nα 符号丢失，x² 变 x2")
        self.assertTrue(v["has_issue"])
        self.assertEqual(v["issue_type"], "公式乱码")

    def test_cross_contamination(self):
        v = parse_llm_verdict("跨题污染\n包含 Q3 内容")
        self.assertTrue(v["has_issue"])
        self.assertEqual(v["issue_type"], "跨题污染")

    def test_empty_returns_call_failure(self):
        v = parse_llm_verdict("")
        self.assertTrue(v["has_issue"])
        self.assertEqual(v["issue_type"], "调用失败")

    def test_whitespace_only(self):
        v = parse_llm_verdict("   \n  \n  ")
        self.assertTrue(v["has_issue"])
        self.assertEqual(v["issue_type"], "调用失败")

    def test_unknown_first_line(self):
        # LLM 跑题不输出预期关键词
        v = parse_llm_verdict("我不确定\n请重试")
        # 不在 VALID_ISSUE_TYPES → 标 has_issue=True，issue_type 保留"未识别"
        self.assertTrue(v["has_issue"])
        self.assertEqual(v["issue_type"], "未识别")


if __name__ == "__main__":
    unittest.main()
