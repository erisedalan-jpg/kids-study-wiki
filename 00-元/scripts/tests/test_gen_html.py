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


class TestGenHtmlReview(unittest.TestCase):
    def setUp(self):
        import gen_html
        self.gh = gen_html

    def test_source_dirs_returns_subject_dirs(self):
        dirs = self.gh.source_dirs()
        names = [d.name for d in dirs]
        self.assertEqual(names, self.gh.SUBJECTS)

    def test_review_source_dirs_included(self):
        dirs = self.gh.review_source_dirs()
        # Each dir should be under 复习/
        for d in dirs:
            parts = d.parts
            self.assertIn("复习", parts,
                          msg=f"Expected '复习' in path parts of {d}")
        # All SUBJECTS should be covered
        names = [d.name for d in dirs]
        self.assertEqual(names, self.gh.SUBJECTS)

    def test_review_dir_included(self):
        """Confirm 复习 appears in review_source_dirs (shape the task spec checks for)."""
        dirs = self.gh.review_source_dirs()
        self.assertTrue(
            any(
                getattr(d, "name", "") == "复习"
                or str(d).replace("\\", "/").rstrip("/").endswith("复习")
                or "复习" in str(d)
                for d in dirs
            )
        )

    def test_gen_review_page_renders_html(self):
        """gen_review_page uses md_to_html + render_page pipeline and returns HTML."""
        fm = {
            "title": "二次函数",
            "考点": "二次函数",
            "父主题": "函数",
            "学科": "数学",
            "weight": "8",
            "真题数": "5",
            "状态": "草稿",
        }
        page = self.gh.gen_review_page(
            Path("二次函数.md"), fm, "## 核心内容\n\n$y=ax^2+bx+c$",
            lambda *a, **kw: ""
        )
        self.assertIn("<!DOCTYPE html>", page)
        self.assertIn("二次函数", page)
        self.assertIn("函数", page)      # 父主题
        self.assertIn("数学", page)      # 学科
        self.assertIn("review-mark", page)

    def test_review_page_depth_is_2(self):
        """review/{学科}/{stem}.html is at depth=2; vendor path uses ../../."""
        fm = {"title": "T", "考点": "T", "父主题": "P", "学科": "数学",
              "weight": "1", "真题数": "1", "状态": "草稿"}
        page = self.gh.gen_review_page(
            Path("T.md"), fm, "body", lambda *a, **kw: ""
        )
        self.assertIn("../../vendor/style.css", page)


if __name__ == "__main__":
    unittest.main()
