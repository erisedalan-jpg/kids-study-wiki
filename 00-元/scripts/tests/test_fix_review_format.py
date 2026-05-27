import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestFixReviewFormat(unittest.TestCase):
    def setUp(self):
        import fix_review_format as f
        self.f = f

    def test_inline_and_display_delims(self):
        self.assertEqual(self.f.fix_text(r"模长 \(|z|\) 与 \[x^2\]"), "模长 $|z|$ 与 $$x^2$$")

    def test_line_spacing_not_converted(self):
        # \[3pt] 是行距命令，不应转成 $$
        self.assertIn(r"\[3pt]", self.f.fix_text(r"\[3pt]"))

    def test_strips_code_fences(self):
        md = "前\n```\n内容\n```python\n更多\n```\n后"
        out = self.f.fix_text(md)
        self.assertNotIn("```", out)
        self.assertIn("内容", out)
        self.assertIn("更多", out)
        self.assertIn("前", out); self.assertIn("后", out)

    def test_idempotent(self):
        md = r"\(a\) 与 \[b\] 与 ```\n代码\n```"
        once = self.f.fix_text(md)
        self.assertEqual(once, self.f.fix_text(once))

    def test_clean_unchanged(self):
        md = "已是 $x$ 与 $$y$$，无围栏。"
        self.assertEqual(self.f.fix_text(md), md)


if __name__ == "__main__":
    unittest.main()
