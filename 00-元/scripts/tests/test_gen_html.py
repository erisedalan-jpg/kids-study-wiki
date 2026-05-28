import sys
import tempfile
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


class TestReviewReferencedExamStems(unittest.TestCase):
    """Unit tests for review_referenced_exam_stems helper (dead-link fix)."""

    def setUp(self):
        import gen_html
        self.gh = gen_html

    def _make_review_dir(self, tmp: Path, subject: str, files: dict[str, str]) -> None:
        """Create 复习/{subject}/*.md files under tmp/复习/{subject}/."""
        d = tmp / "复习" / subject
        d.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            (d / name).write_text(content, encoding="utf-8")

    def test_returns_matching_stems(self):
        """Stems referenced by [[X]] in review pages that exist in exam_stems are returned."""
        import gen_html
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            self._make_review_dir(tmp, "数学", {
                "一元二次不等式.md": (
                    "## 全部真题清单\n\n"
                    "- [[2019-理-01]]（2019 · 易）\n"
                    "- [[2016-理-02]]（2016 · 易）\n"
                    "- [[2099-理-99]]（不存在的题）\n"
                ),
            })
            exam_stems = {"2019-理-01", "2016-理-02", "2018-理-05"}
            # Temporarily patch REPO_ROOT
            orig_root = gen_html.REPO_ROOT
            try:
                gen_html.REPO_ROOT = tmp
                result = gen_html.review_referenced_exam_stems("数学", exam_stems)
            finally:
                gen_html.REPO_ROOT = orig_root
        self.assertEqual(result, {"2019-理-01", "2016-理-02"})

    def test_ignores_non_exam_stems(self):
        """Wikilinks that are NOT in exam_stems are not returned."""
        import gen_html
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            self._make_review_dir(tmp, "数学", {
                "考点.md": "[[词条链接|显示]] [[不是真题]]",
            })
            exam_stems = {"2022-理-01"}
            orig_root = gen_html.REPO_ROOT
            try:
                gen_html.REPO_ROOT = tmp
                result = gen_html.review_referenced_exam_stems("数学", exam_stems)
            finally:
                gen_html.REPO_ROOT = orig_root
        self.assertEqual(result, set())

    def test_handles_pipe_alias_wikilinks(self):
        """[[stem|display]] form: only the stem part (before |) is extracted."""
        import gen_html
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            self._make_review_dir(tmp, "物理", {
                "牛顿第二定律.md": "[[2021-理-03|第3题]]",
            })
            exam_stems = {"2021-理-03"}
            orig_root = gen_html.REPO_ROOT
            try:
                gen_html.REPO_ROOT = tmp
                result = gen_html.review_referenced_exam_stems("物理", exam_stems)
            finally:
                gen_html.REPO_ROOT = orig_root
        self.assertEqual(result, {"2021-理-03"})

    def test_missing_review_dir_returns_empty(self):
        """If 复习/{subject} does not exist, return empty set without error."""
        import gen_html
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            orig_root = gen_html.REPO_ROOT
            try:
                gen_html.REPO_ROOT = tmp
                result = gen_html.review_referenced_exam_stems("数学", {"2020-理-01"})
            finally:
                gen_html.REPO_ROOT = orig_root
        self.assertEqual(result, set())

    def test_multiple_review_files(self):
        """Stems from multiple review .md files in the same subject dir are unioned."""
        import gen_html
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            self._make_review_dir(tmp, "化学", {
                "氧化还原.md": "[[2018-理-04]]\n[[2017-理-07]]",
                "酸碱盐.md": "[[2018-理-04]]\n[[2016-理-09]]",
            })
            exam_stems = {"2018-理-04", "2017-理-07", "2016-理-09"}
            orig_root = gen_html.REPO_ROOT
            try:
                gen_html.REPO_ROOT = tmp
                result = gen_html.review_referenced_exam_stems("化学", exam_stems)
            finally:
                gen_html.REPO_ROOT = orig_root
        self.assertEqual(result, {"2018-理-04", "2017-理-07", "2016-理-09"})


class TestBuildReviewIndexHtml(unittest.TestCase):
    """Tests for the pure helper build_review_index_html."""

    def setUp(self):
        import gen_html
        self.gh = gen_html

    def _make_entries(self):
        return [
            {"考点": "二次函数", "父主题": "函数", "weight": 8, "真题数": 5, "stem": "二次函数"},
            {"考点": "指数函数", "父主题": "函数", "weight": 6, "真题数": 3, "stem": "指数函数"},
            {"考点": "一元二次不等式", "父主题": "不等式", "weight": 19, "真题数": 6, "stem": "一元二次不等式"},
            {"考点": "均值不等式", "父主题": "不等式", "weight": 12, "真题数": 4, "stem": "均值不等式"},
        ]

    def test_groups_by_parent_topic(self):
        """HTML should contain both 父主题 names as headings."""
        html_out = self.gh.build_review_index_html("数学", self._make_entries())
        self.assertIn("函数", html_out)
        self.assertIn("不等式", html_out)

    def test_links_to_stem_html(self):
        """Each 考点 should have a link to <stem>.html in the same dir."""
        html_out = self.gh.build_review_index_html("数学", self._make_entries())
        self.assertIn('href="二次函数.html"', html_out)
        self.assertIn('href="一元二次不等式.html"', html_out)

    def test_weight_and_count_in_label(self):
        """Labels should include weight and 真题数."""
        html_out = self.gh.build_review_index_html("数学", self._make_entries())
        self.assertIn("weight 8", html_out)
        self.assertIn("5题", html_out)

    def test_parent_topic_ordering_by_total_weight(self):
        """父主题 with higher total weight comes first (不等式 31 > 函数 14)."""
        html_out = self.gh.build_review_index_html("数学", self._make_entries())
        pos_inequality = html_out.find("不等式")
        pos_function = html_out.find("函数")
        self.assertLess(pos_inequality, pos_function,
                        "不等式 (total weight 31) should precede 函数 (total weight 14)")

    def test_within_group_ordering_by_weight_desc(self):
        """Within a 父主题, higher-weight 考点 should appear before lower-weight."""
        html_out = self.gh.build_review_index_html("数学", self._make_entries())
        pos_quadratic = html_out.find("一元二次不等式")
        pos_mean = html_out.find("均值不等式")
        self.assertLess(pos_quadratic, pos_mean,
                        "一元二次不等式 (weight 19) should precede 均值不等式 (weight 12)")

    def test_defaults_for_missing_weight_and_count(self):
        """Entries without weight/真题数 should not crash; default to 0."""
        entries = [{"考点": "X", "父主题": "A", "stem": "X"}]
        html_out = self.gh.build_review_index_html("数学", entries)
        self.assertIn("X.html", html_out)
        self.assertIn("weight 0", html_out)

    def test_uncategorised_fallback(self):
        """Entries without 父主题 should go under '（未分类）' group."""
        entries = [{"考点": "孤儿考点", "stem": "孤儿考点", "weight": 3, "真题数": 1}]
        html_out = self.gh.build_review_index_html("数学", entries)
        self.assertIn("未分类", html_out)


class TestHomepageReviewLinks(unittest.TestCase):
    """Tests that gen_home includes links to per-subject review index pages."""

    def setUp(self):
        import gen_html
        self.gh = gen_html

    def _default_stats(self):
        return {"数学": 10, "物理": 8, "化学": 7, "生物": 6}

    def test_home_links_to_each_subject_review_index(self):
        """index.html must contain links for all 4 subjects' review indexes."""
        page = self.gh.gen_home(self._default_stats(), 31)
        for subject in self.gh.SUBJECTS:
            expected = f"review/{subject}/index.html"
            self.assertIn(expected, page,
                          msg=f"Homepage should link to {expected}")

    def test_home_links_to_math_review_index(self):
        """Explicit check for the 数学 link (regression guard)."""
        page = self.gh.gen_home(self._default_stats(), 31)
        self.assertIn("review/数学/index.html", page)


if __name__ == "__main__":
    unittest.main()
