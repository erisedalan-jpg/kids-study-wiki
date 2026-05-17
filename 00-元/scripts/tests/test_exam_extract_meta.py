"""测试 markitdown 元数据抽取。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exam_extract_meta import (  # noqa: E402
    extract_answer,
    extract_solution_text,
    split_by_answer_tag,
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


class TestSplitByAnswerTag(unittest.TestCase):
    """北京卷等版式适配降级：按【答案】序号直映射。"""

    def test_maps_answer_order_to_expected_qnos(self):
        # 公式碎片化致题号不可切，但【答案】顺序 = 题号顺序
        md = """碎\n片\n1.乱码题面【答案】A\n【解析】略\n更多碎片\n【答案】C\n【解析】略2\n【答案】B\n【解析】略3"""
        chunks = split_by_answer_tag(md, [1, 2, 3])
        self.assertEqual(list(chunks.keys()), [1, 2, 3])
        self.assertEqual(extract_answer(chunks[1]), "A")
        self.assertEqual(extract_answer(chunks[2]), "C")
        self.assertEqual(extract_answer(chunks[3]), "B")

    def test_returns_empty_on_count_mismatch(self):
        # 【答案】数 != expected_qnos 数 → 不安全，放弃映射
        md = "【答案】A\n【答案】B\n"
        self.assertEqual(split_by_answer_tag(md, [1, 2, 3]), {})


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

    def test_beijing_fill_formula_fragment(self):
        # 北京理科卷: 公式答案被 PyMuPDF 拆成多行碎片+私有区字形码;
        # 跨行正则 + 去字形码 + 折叠空白 -> 还原可读串(不退化单字符)
        NL = chr(10)
        PUA = chr(0xF028)   # PDF 私有区括号字形
        RC = chr(0xFFFD)    # replacement char
        chunk = ("题面" + NL + "【答案】" + PUA + "-1,1" + PUA + NL
                 + "或" + NL + "x" + NL + "=" + NL + "2" + RC + NL
                 + "【解析】【分析】略")
        r = extract_answer(chunk)
        self.assertNotIn(PUA, r)
        self.assertNotIn(RC, r)
        self.assertIn("-1,1", r)
        self.assertGreater(len(r), 1)



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
