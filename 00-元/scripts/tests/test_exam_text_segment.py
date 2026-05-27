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

    def test_old_format_markers_split(self):
        # 旧卷用 【考点】【解答】 等标记
        page = (
            "5．（5分）已知正三角形 ABC，求 z 的取值范围是（　　）\n"
            "A．（1,2）B．（0,2）C．（﹣1,2）D．（0,1）\n"
            "【考点】简单线性规划\n【分析】代入顶点求范围\n"
            "【解答】解：设 C(a,b)，得 z 范围为（0,2）．\n【点评】基础题\n"
            "6．下一题\n"
        )
        out = self.s.segment_by_qno(page, 5)
        self.assertIn("正三角形", out["题干"])
        self.assertNotIn("【考点】", out["题干"])      # 标记起归解析
        self.assertIn("【解答】", out["解析"])
        self.assertNotIn("下一题", out["解析"])         # 不串入下一题

    def test_skips_instruction_false_match(self):
        # 页内既有须知"1．答题前…"又有真题"1．设集合…"，应选含解析标记者
        page = (
            "1．答题前，先将自己的姓名、准考证号填写在答题卡上．\n"
            "2．将答案写在答题卡上．\n"
            "一、选择题\n"
            "1．设集合 A={1,2}，则子集个数为（　　）\n"
            "【答案】C\n【解析】2^n=4。\n"
            "2．复数题\n"
        )
        out = self.s.segment_by_qno(page, 1)
        self.assertIn("子集个数", out["题干"])
        self.assertNotIn("答题前", out["题干"])         # 跳过须知
        self.assertIn("2^n=4", out["解析"])


if __name__ == "__main__":
    unittest.main()
