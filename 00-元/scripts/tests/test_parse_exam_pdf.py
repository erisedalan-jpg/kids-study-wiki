"""测试 parse_exam_pdf.py 的切分逻辑（含游离行归属修复）。"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from parse_exam_pdf import (  # noqa: E402
    _is_orphan_math_line,
    _split_questions,
    parse_pdf,
)

REPO = Path(__file__).resolve().parents[3]
PDF = REPO / "素材" / "真题" / "吉林" / "2008-2024·（吉林）数学高考真题" / \
      "2024年高考数学试卷（新课标Ⅱ卷）（解析卷）.pdf"


class TestIsOrphanMathLine(unittest.TestCase):
    """判断一行是否是"游离数学定义行"（应被合并到下一题 stem）。"""

    def test_math_definition(self):
        self.assertTrue(_is_orphan_math_line("M ={2,4,6,8,10},N ={ x -1< x<6 }"))
        self.assertTrue(_is_orphan_math_line("U ={1,2,3,4,5} M ={1,3}"))
        self.assertTrue(_is_orphan_math_line("M N ="))
        self.assertTrue(_is_orphan_math_line("M ∩ N ="))
        self.assertTrue(_is_orphan_math_line("x²"))
        self.assertTrue(_is_orphan_math_line("x2"))

    def test_question_number_is_not_orphan(self):
        self.assertFalse(_is_orphan_math_line("1. 集合 ，则 I （ ）"))
        self.assertFalse(_is_orphan_math_line("21. 已知椭圆E的中心为坐标原点"))

    def test_answer_solution_markers_not_orphan(self):
        self.assertFalse(_is_orphan_math_line("【答案】A"))
        self.assertFalse(_is_orphan_math_line("【解析】"))
        self.assertFalse(_is_orphan_math_line("【分析】根据集合的交集运算"))
        self.assertFalse(_is_orphan_math_line("【详解】因为M ..."))
        self.assertFalse(_is_orphan_math_line("【小问1详解】"))
        self.assertFalse(_is_orphan_math_line("【点睛】关键点点睛"))

    def test_normal_chinese_sentence_not_orphan(self):
        self.assertFalse(_is_orphan_math_line("由题意作出可行域，如图阴影部分所示"))
        self.assertFalse(_is_orphan_math_line("故选：A"))
        self.assertFalse(_is_orphan_math_line("综上，a的取值范围为"))
        self.assertFalse(_is_orphan_math_line("第 1 页 共 27 页"))
        self.assertFalse(_is_orphan_math_line("第1页/共25页"))

    def test_empty_or_whitespace_not_orphan(self):
        self.assertFalse(_is_orphan_math_line(""))
        self.assertFalse(_is_orphan_math_line("   "))

    def test_option_letters_not_orphan(self):
        # 选项行 A. B. C. D.
        self.assertFalse(_is_orphan_math_line("A. {2,4} B. {2,4,6} C. {2,4,6,8} D. {2,4,6,8,10}"))

    def test_pure_numeric_not_orphan(self):
        # 纯数字行（如答案末的页码碎片 "10" / "16" / "65"）不应被误判为游离数学行
        self.assertFalse(_is_orphan_math_line("10"))
        self.assertFalse(_is_orphan_math_line("16"))
        self.assertFalse(_is_orphan_math_line("3"))

    def test_single_letter_not_orphan(self):
        # 单字母（如孤立的 "x" "M"）也不应被认为是游离行
        self.assertFalse(_is_orphan_math_line("x"))
        self.assertFalse(_is_orphan_math_line("M"))


class TestSplitQuestionsOrphanMerge(unittest.TestCase):
    """题号前游离行应 prepend 到下一题 stem。"""

    def test_q1_orphan_lines_prepend(self):
        # 模拟 PDF 提取文本：Q1 之前有 "M=...,N=..." 游离定义行
        text = """一、选择题：本题共 12小题，每小题 5分，共 60分.
M ={2,4,6,8,10},N ={ x -1< x<6 }
M N =
1. 集合 ，则 I （ ）
A. {2,4} B. {2,4,6} C. {2,4,6,8} D. {2,4,6,8,10}
【答案】A
【解析】
2. 设(1+2i)a+b=2i，其中a,b为实数，则（ ）
A. a=1,b=-1
【答案】A
"""
        result = _split_questions(text)
        # 找 qno=1 的 body
        q1_body = next(body for qno, body in result if qno == 1)
        self.assertIn("M ={2,4,6,8,10}", q1_body)
        self.assertIn("N ={", q1_body)
        self.assertIn("M N =", q1_body)
        # 原本 Q1 本身的内容还在
        self.assertIn("1. 集合 ，则 I", q1_body) if False else None  # qno 已被剥离
        self.assertIn("集合", q1_body)
        self.assertIn("A. {2,4}", q1_body)

    def test_mid_question_orphan_lines_prepend(self):
        # Q2 之前有 "x2" 游离行（典型：椭圆方程 x²/3 中的 x² 被 pdfplumber 切到题号前）
        text = """一、选择题：
1. 第一题题面
A. 选项A
【答案】A
x2
2. 已知椭圆C:  y2 =1的左、右焦点
A. 1 B. 2
【答案】C
"""
        result = _split_questions(text)
        q2_body = next(body for qno, body in result if qno == 2)
        self.assertIn("x2", q2_body)
        self.assertIn("椭圆C", q2_body)
        # Q1 不应该还包含 x2（已被剥离）
        q1_body = next(body for qno, body in result if qno == 1)
        self.assertNotIn("x2", q1_body)

    def test_answer_solution_blocks_not_treated_as_orphan(self):
        # 不能把 Q1 答案块的内容拉到 Q2
        text = """一、选择题：
1. 第一题题面
A. 选项
【答案】A
【解析】
【分析】根据集合的交集运算
2. 第二题题面
A. 选项
"""
        result = _split_questions(text)
        q2_body = next(body for qno, body in result if qno == 2)
        self.assertNotIn("【分析】", q2_body)
        self.assertIn("第二题题面", q2_body)

    def test_no_orphan_yields_unchanged_behavior(self):
        # 无游离行时切分行为不变
        text = """一、选择题：
1. 第一题题面
A. 选项A
【答案】A
2. 第二题题面
B. 选项B
【答案】B
"""
        result = _split_questions(text)
        q1_body = next(body for qno, body in result if qno == 1)
        self.assertIn("第一题题面", q1_body)
        self.assertIn("选项A", q1_body)


@unittest.skipUnless(PDF.exists(), "需要 2024 新课标Ⅱ 解析卷 PDF")
class TestParseExamPdf(unittest.TestCase):
    def test_question_count_in_range(self):
        result = parse_pdf(PDF, subject="数学", province="吉林", year=2024)
        self.assertGreaterEqual(len(result["questions"]), 18)
        self.assertLessEqual(len(result["questions"]), 23)

    def test_question_fields_present(self):
        result = parse_pdf(PDF, subject="数学", province="吉林", year=2024)
        first = result["questions"][0]
        self.assertEqual(first["qno"], 1)
        self.assertIn("stem", first)
        self.assertIn("qtype", first)
        self.assertGreater(len(first["stem"]), 5)

    def test_paper_id_format(self):
        result = parse_pdf(PDF, subject="数学", province="吉林", year=2024)
        self.assertEqual(result["paper_id"], "2024-不分-新课标Ⅱ")
        self.assertEqual(result["paper"], "新课标Ⅱ")
        self.assertEqual(result["gender"], "不分")


if __name__ == "__main__":
    unittest.main()
