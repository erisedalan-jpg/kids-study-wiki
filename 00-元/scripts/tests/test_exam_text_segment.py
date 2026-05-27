import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestSegment(unittest.TestCase):
    def setUp(self):
        import exam_text_segment as s
        self.s = s

    def test_segments_question_and_solution(self):
        page = (
            "1．设集合 A={1,2}，则 A 的子集个数为（ ）\n"
            "A．2  B．3  C．4  D．8\n"
            "【答案】C\n"
            "【解析】子集个数为 2^n=4。\n"
            "2．复数 z=1+i 的模为（ ）\n"
            "【答案】B\n"
        )
        out = self.s.segment_by_qno(page, 1)
        self.assertIn("子集个数", out["题干"])
        self.assertNotIn("复数 z", out["题干"])      # 不串入下一题
        self.assertIn("2^n=4", out["解析"])
        self.assertNotIn("【答案】", out["题干"])     # 答案/解析归入解析段

    def test_missing_qno_returns_fallback(self):
        page = "无编号锚点的整页文本"
        out = self.s.segment_by_qno(page, 7)
        self.assertEqual(out["题干"], "")
        self.assertEqual(out["解析"].strip(), "无编号锚点的整页文本")
        self.assertTrue(out["fallback"])


if __name__ == "__main__":
    unittest.main()
