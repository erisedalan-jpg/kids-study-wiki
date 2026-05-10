"""测试 parse_exam_pdf.py 对 2024 新课标Ⅱ 真题的题块切分。

注意: 此测试需要本地存在 2024 年吉林新课标Ⅱ 解析卷 PDF。
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from parse_exam_pdf import parse_pdf  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
PDF = REPO / "素材" / "真题" / "吉林" / "2008-2024·（吉林）数学高考真题" / \
      "2024年高考数学试卷（新课标Ⅱ卷）（解析卷）.pdf"


@unittest.skipUnless(PDF.exists(), "需要 2024 新课标Ⅱ 解析卷 PDF")
class TestParseExamPdf(unittest.TestCase):
    def test_question_count_in_range(self):
        result = parse_pdf(PDF, subject="数学", province="吉林", year=2024)
        # 高考数学卷题数典型 19-22
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
