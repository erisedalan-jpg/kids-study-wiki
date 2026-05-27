import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestBuildPrompt(unittest.TestCase):
    def setUp(self):
        import gen_kaodian_review as g
        self.g = g

    def test_build_prompt_fills_template_and_marks_reps(self):
        info = {
            "父主题": "复数", "真题数": 2, "年份跨度": (2010, 2024),
            "真题": [
                {"_bare": "2024-A-01", "年份": "2024", "题干文本": "求|z|",
                 "解析文本": "解：|z|=√2"},
                {"_bare": "2010-A-02", "年份": "2010", "题干文本": "复数运算",
                 "解析文本": "解：..."},
            ],
        }
        p = self.g.build_prompt("数学", "复数", info, rep_n=1)
        self.assertIn("## 代表题精讲", p)
        self.assertIn("复数", p)
        self.assertIn("【代表题】", p)            # 近年第一题被标代表题
        self.assertIn("2024-A-01", p)
        self.assertNotIn("\\(", p)                 # 模板无 LaTeX 圆括号定界符


if __name__ == "__main__":
    unittest.main()
