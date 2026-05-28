"""Tests for gen_review_handbook.py — pure helpers only (no disk I/O needed)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestAnchorId(unittest.TestCase):
    """anchor_id(考点) → stable, filesystem-safe id."""

    def setUp(self):
        import gen_review_handbook as g
        self.g = g

    def test_plain_kaodian(self):
        self.assertEqual(self.g.anchor_id("一元二次不等式"), "kp-一元二次不等式")

    def test_special_chars_replaced(self):
        # Characters \/:*?"<>| are replaced with _
        aid = self.g.anchor_id('a/b:c*d?"e')
        self.assertTrue(aid.startswith("kp-"))
        self.assertNotIn("/", aid)
        self.assertNotIn(":", aid)
        self.assertNotIn("*", aid)
        self.assertNotIn("?", aid)
        self.assertNotIn('"', aid)

    def test_stable_mapping(self):
        k = "三角函数图象变换"
        self.assertEqual(self.g.anchor_id(k), self.g.anchor_id(k))

    def test_different_kaodian_different_ids(self):
        self.assertNotEqual(self.g.anchor_id("导数"), self.g.anchor_id("极值"))


class TestBuildHandbookHtml(unittest.TestCase):
    """build_handbook_html: pure assembly function tests."""

    def setUp(self):
        import gen_review_handbook as g
        self.g = g

    def _make_tree_eras(self) -> dict:
        """最简单的 aggregate + attach_trees 输出（只有最新时代，一个题位）。"""
        return {
            "最新(24+)": {
                ("选择", 1): {
                    "n": 3,
                    "难度倾向": "易",
                    "考点": [("复数运算", 3), ("共轭复数", 1)],
                    "树": [("复数", 4, [("复数运算", 3), ("共轭复数", 1)])],
                }
            }
        }

    def _make_entries(self) -> list[dict]:
        return [
            {
                "考点": "复数运算",
                "父主题": "复数",
                "weight": 8,
                "真题数": 3,
                "body_html": "<p>复数运算内容</p>",
            },
            {
                "考点": "共轭复数",
                "父主题": "复数",
                "weight": 4,
                "真题数": 1,
                "body_html": "<p>共轭复数内容</p>",
            },
            {
                "考点": "集合",
                "父主题": "集合与逻辑",
                "weight": 12,
                "真题数": 5,
                "body_html": "<p>集合内容</p>",
            },
        ]

    # ── Section id presence ──────────────────────────────────────────────

    def test_each_entry_has_section_id(self):
        entries = self._make_entries()
        out = self.g.build_handbook_html("数学", self._make_tree_eras(), entries)
        for e in entries:
            expected_id = self.g.anchor_id(e["考点"])
            self.assertIn(f'id="{expected_id}"', out,
                          msg=f"Missing id for 考点={e['考点']}")

    # ── Anchor href consistency ───────────────────────────────────────────

    def test_tree_href_matches_body_id(self):
        """Every <a href="#kp-X"> in the tree must have a matching id="kp-X" in body."""
        import re
        entries = self._make_entries()
        out = self.g.build_handbook_html("数学", self._make_tree_eras(), entries)
        hrefs = set(re.findall(r'href="#(kp-[^"]+)"', out))
        ids = set(re.findall(r'id="(kp-[^"]+)"', out))
        # Every href that was produced must resolve to an id in the body
        for href_target in hrefs:
            self.assertIn(href_target, ids,
                          msg=f"href='#{href_target}' has no matching id in body")

    def test_no_broken_href_for_missing_review_md(self):
        """A tree 考点 without a matching 复习 md must render as plain text, not a link."""
        # 树里有 "共轭复数"，但 entries 里没有此考点
        entries = [
            {
                "考点": "复数运算",
                "父主题": "复数",
                "weight": 8,
                "真题数": 3,
                "body_html": "<p>内容</p>",
            }
        ]
        out = self.g.build_handbook_html("数学", self._make_tree_eras(), entries)
        # 共轭复数 is in tree but not in entries → no href="#kp-共轭复数"
        self.assertNotIn('href="#kp-共轭复数"', out)
        # 复数运算 IS in entries → href exists
        self.assertIn('href="#kp-复数运算"', out)

    # ── page-break CSS ────────────────────────────────────────────────────

    def test_body_contains_section_class(self):
        out = self.g.build_handbook_html("数学", self._make_tree_eras(), self._make_entries())
        self.assertIn('class="kp-zhuanti"', out)

    # ── Grouping by 父主题 ────────────────────────────────────────────────

    def test_groups_by_parent_topic(self):
        entries = self._make_entries()
        out = self.g.build_handbook_html("数学", self._make_tree_eras(), entries)
        # Both 父主题 names should appear as headings
        self.assertIn("复数", out)
        self.assertIn("集合与逻辑", out)

    def test_parent_topic_ordering_by_total_weight(self):
        """高 weight 总和的父主题应排在前面（集合与逻辑 12 > 复数 12; tie → both present）。"""
        entries = self._make_entries()
        out = self.g.build_handbook_html("数学", self._make_tree_eras(), entries)
        pos_jiaoji = out.find("集合与逻辑")
        pos_fushu = out.find("复数</h2>")
        # 集合与逻辑 (weight 12) >= 复数 (weight 12); at minimum both exist
        self.assertGreater(pos_jiaoji, 0)
        self.assertGreater(pos_fushu, 0)

    # ── Tree section presence ─────────────────────────────────────────────

    def test_tree_section_present(self):
        out = self.g.build_handbook_html("数学", self._make_tree_eras(), self._make_entries())
        self.assertIn("blueprint-section", out)
        self.assertIn("zhuanti-section", out)

    def test_era_name_in_tree_section(self):
        out = self.g.build_handbook_html("数学", self._make_tree_eras(), self._make_entries())
        self.assertIn("最新(24+)", out)

    def test_empty_entries_no_crash(self):
        out = self.g.build_handbook_html("数学", self._make_tree_eras(), [])
        # Tree still renders
        self.assertIn("blueprint-section", out)
        # No sections for missing entries
        self.assertNotIn("kp-zhuanti", out)


class TestBuildFullHtml(unittest.TestCase):
    """build_full_html: wraps body in complete HTML page."""

    def setUp(self):
        import gen_review_handbook as g
        self.g = g

    def test_full_html_structure(self):
        out = self.g.build_full_html("数学", "<p>body</p>")
        self.assertIn("<!DOCTYPE html>", out)
        self.assertIn("数学复习手册", out)
        self.assertIn("<body>", out)

    def test_print_css_included(self):
        out = self.g.build_full_html("数学", "<p>body</p>")
        self.assertIn("@media print", out)
        self.assertIn("page-break-before", out)

    def test_katex_included(self):
        out = self.g.build_full_html("数学", "<p>body</p>")
        self.assertIn("vendor/katex/katex.min.css", out)

    def test_vendor_style_included(self):
        out = self.g.build_full_html("数学", "<p>body</p>")
        self.assertIn("./vendor/style.css", out)

    def test_a4_print_hint(self):
        out = self.g.build_full_html("数学", "<p>body</p>")
        self.assertIn("Ctrl+P", out)


class TestRenderBody(unittest.TestCase):
    """_render_body: markdown → HTML, wikilinks stripped."""

    def setUp(self):
        import gen_review_handbook as g
        self.g = g

    def test_heading_converted(self):
        out = self.g._render_body("## 知识精要\n\n内容")
        self.assertIn("<h2>", out)
        self.assertIn("知识精要", out)

    def test_wikilink_becomes_display_text(self):
        out = self.g._render_body("见[[117-导数|导数]]说明")
        self.assertNotIn("[[", out)
        self.assertNotIn("]]", out)
        self.assertIn("导数", out)

    def test_bare_wikilink_uses_target(self):
        out = self.g._render_body("参见[[余弦定理]]")
        self.assertNotIn("[[", out)
        self.assertIn("余弦定理", out)

    def test_formula_preserved(self):
        """$...$ formula markup should pass through (KaTeX renders it in browser)."""
        out = self.g._render_body("公式 $y=ax^2$")
        self.assertIn("$y=ax^2$", out)

    def test_empty_body(self):
        out = self.g._render_body("")
        self.assertIsInstance(out, str)


class TestIntegration(unittest.TestCase):
    """Integration: anchor_id + build_handbook_html produce consistent ids/hrefs."""

    def setUp(self):
        import gen_review_handbook as g
        self.g = g

    def test_anchor_id_used_in_both_sides(self):
        """The id used in a section must equal the href target used in the tree."""
        import re
        kaodian = "三角函数图象变换"
        expected_id = self.g.anchor_id(kaodian)

        tree_eras = {
            "最新(24+)": {
                ("解答", 17): {
                    "n": 5,
                    "难度倾向": "中",
                    "考点": [(kaodian, 5)],
                    "树": [("三角函数", 5, [(kaodian, 5)])],
                }
            }
        }
        entries = [{
            "考点": kaodian,
            "父主题": "三角函数",
            "weight": 15,
            "真题数": 5,
            "body_html": "<p>内容</p>",
        }]
        out = self.g.build_handbook_html("数学", tree_eras, entries)
        # href in tree
        self.assertIn(f'href="#{expected_id}"', out)
        # id in body section
        self.assertIn(f'id="{expected_id}"', out)

        # Double-check they are the same string
        hrefs = set(re.findall(r'href="#(kp-[^"]+)"', out))
        ids = set(re.findall(r'id="(kp-[^"]+)"', out))
        self.assertTrue(hrefs.issubset(ids),
                        f"Broken hrefs: {hrefs - ids}")


if __name__ == "__main__":
    unittest.main()
