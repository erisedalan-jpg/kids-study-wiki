import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestThresholdText(unittest.TestCase):
    def setUp(self):
        import gen_html
        self.gh = gen_html

    def test_default_threshold_is_3(self):
        self.assertEqual(self.gh.DEFAULT_THRESHOLD, 3)

    def test_home_text_uses_threshold(self):
        page = self.gh.gen_home({"数学": 1, "物理": 0, "化学": 0, "生物": 0}, 1, threshold=3)
        self.assertIn("weight ≥ 3", page)
        self.assertNotIn("weight ≥ 10", page)


class TestReviewHooks(unittest.TestCase):
    def setUp(self):
        import gen_html
        self.gh = gen_html

    def test_render_page_injects_review_js(self):
        p0 = self.gh.render_page("t", "<p>x</p>", depth=0)
        self.assertIn('src="./vendor/review.js"', p0)
        p2 = self.gh.render_page("t", "<p>x</p>", depth=2)
        self.assertIn('src="../../vendor/review.js"', p2)
        self.assertIn("defer", p0)

    def test_atom_page_has_mark_hook(self):
        from pathlib import Path
        fm = {"title": "加法", "weight": "12", "学科": "数学", "学段": "[小学]",
              "主题": "[数与运算]", "吉林反链": "5", "学习路径出现": "0",
              "aliases": "[加法]", "英文术语": "addition"}
        page = self.gh.gen_atom_page(Path("016-加法.md"), fm, "正文", lambda *a, **k: "")
        self.assertIn('class="review-mark"', page)
        self.assertIn('data-stem="016-加法"', page)

    def test_subject_index_has_progress_filter_and_datastem(self):
        from pathlib import Path
        atoms = [(Path("016-加法.md"), {"title": "加法", "吉林反链": "5"}, 12)]
        page = self.gh.gen_subject_index("数学", atoms, {"gold": 50, "red": 20})
        self.assertIn('id="review-progress"', page)
        self.assertIn('data-subject="数学"', page)
        self.assertIn('id="review-filter"', page)
        self.assertIn('id="review-search"', page)
        self.assertIn('data-stem="016-加法"', page)
        self.assertNotIn("function filterEntries", page)

    def test_home_has_review_io(self):
        page = self.gh.gen_home({"数学": 1, "物理": 0, "化学": 0, "生物": 0}, 1, threshold=3)
        self.assertIn('id="review-io"', page)


if __name__ == "__main__":
    unittest.main()
