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


class TestRenderMd(unittest.TestCase):
    def test_render_md_has_static_blocks(self):
        import gen_kaodian_review as g
        info = {"父主题": "复数", "真题数": 1, "题位": [("选择", 1)],
                "难度分布": {"易": 1}, "年份跨度": (2024, 2024),
                "真题": [{"_bare": "2024-A-01", "年份": "2024", "难度": "易",
                          "摘要": "求模"}]}
        md = g.render_md("数学", "复数", info, llm_body="## 知识精要\n模长公式",
                         weight=12, concept_link="[[330-复数概念|复数]]")
        self.assertIn("考点: 复数", md)            # frontmatter
        self.assertIn("## 考点定位", md)
        self.assertIn("## 知识精要", md)           # LLM 段嵌入
        self.assertIn("## 全部真题清单", md)
        self.assertIn("[[2024-A-01", md)           # 真题链接
        self.assertIn("## 关联", md)
        self.assertIn("[[330-复数概念|复数]]", md)


class TestResolveConcept(unittest.TestCase):
    def test_resolve_concept_uses_alias_lookup(self):
        import gen_kaodian_review as g
        alias = {"余弦定理": "126-定理"}
        link, weight = g.resolve_concept("余弦定理", alias, weights={"126-定理": 87})
        self.assertEqual(link, "[[126-定理|余弦定理]]")
        self.assertEqual(weight, 87)

    def test_resolve_concept_missing(self):
        import gen_kaodian_review as g
        link, weight = g.resolve_concept("无词条考点", {}, weights={})
        self.assertEqual(link, "")
        self.assertEqual(weight, 0)


class TestParseKaodian(unittest.TestCase):
    def test_parses_string_list(self):
        import gen_kaodian_review as g
        self.assertEqual(g._parse_kaodian("[复数, 模长, 代数运算]"), ["复数", "模长", "代数运算"])
    def test_passthrough_real_list(self):
        import gen_kaodian_review as g
        self.assertEqual(g._parse_kaodian(["复数", "模长"]), ["复数", "模长"])
    def test_chinese_comma_and_empty(self):
        import gen_kaodian_review as g
        self.assertEqual(g._parse_kaodian("复数，模长"), ["复数", "模长"])
        self.assertEqual(g._parse_kaodian(""), [])
        self.assertEqual(g._parse_kaodian(None), [])


class TestBodyComplete(unittest.TestCase):
    def test_complete(self):
        import gen_kaodian_review as g
        b = "## 知识精要\nx\n## 解题方法与套路\nx\n## 高频易错\nx\n## 代表题精讲\nx"
        self.assertTrue(g.body_is_complete(b))

    def test_empty(self):
        import gen_kaodian_review as g
        self.assertFalse(g.body_is_complete("   "))

    def test_missing_block(self):
        import gen_kaodian_review as g
        self.assertFalse(g.body_is_complete("## 知识精要\nx\n## 高频易错\nx"))


class TestBodyClean(unittest.TestCase):
    def test_clean_body_passes(self):
        import gen_kaodian_review as g
        body = "## 知识精要\nx\n## 解题方法与套路\nx\n## 高频易错\nx\n## 代表题精讲\n解法：步骤1，步骤2。"
        self.assertTrue(g.body_is_clean(body))

    def test_long_line_fails(self):
        import gen_kaodian_review as g
        long_line = "A" * 701
        body = f"## 代表题精讲\n{long_line}\n## 知识精要\nx"
        self.assertFalse(g.body_is_clean(body))

    def test_two_leak_markers_fails(self):
        import gen_kaodian_review as g
        body = "## 代表题精讲\n让我重新考虑一下这道题，等等，好像不对。"
        self.assertFalse(g.body_is_clean(body))

    def test_single_leak_marker_passes(self):
        import gen_kaodian_review as g
        # one occurrence is below threshold (2), should still pass
        body = "## 代表题精讲\n让我重新整理一下思路。"
        self.assertTrue(g.body_is_clean(body))

    def test_leaked_body_rejected_by_generate_one(self):
        import gen_kaodian_review as g
        # body passes body_is_complete but fails body_is_clean
        long_line = "X" * 701
        body = (
            "## 知识精要\nx\n## 解题方法与套路\nx\n## 高频易错\nx\n"
            f"## 代表题精讲\n{long_line}"
        )
        info = {
            "父主题": "复数", "真题数": 1, "题位": [("选择", 1)],
            "难度分布": {"易": 1}, "年份跨度": (2024, 2024),
            "真题": [{"_bare": "2024-A-01", "年份": "2024", "难度": "易",
                      "摘要": "求模", "题干文本": "求|z|", "解析文本": "解：..."}],
        }
        class R:
            text = body
        kp, md, st = g._generate_one("数学", "复数", info, {}, {}, lambda p: R())
        self.assertIsNone(md)
        self.assertIn("泄漏", st)


class TestGenerateOne(unittest.TestCase):
    def _fake(self, text):
        class R:
            pass
        r = R()
        r.text = text
        return lambda p: r

    def _info(self):
        return {
            "父主题": "复数", "真题数": 1, "题位": [("选择", 1)],
            "难度分布": {"易": 1}, "年份跨度": (2024, 2024),
            "真题": [{"_bare": "2024-A-01", "年份": "2024", "难度": "易",
                      "摘要": "求模", "题干文本": "求|z|", "解析文本": "解：..."}],
        }

    def test_complete_returns_md(self):
        import gen_kaodian_review as g
        body = "## 知识精要\nx\n## 解题方法与套路\nx\n## 高频易错\nx\n## 代表题精讲\nx"
        kp, md, st = g._generate_one("数学", "复数", self._info(), {}, {}, self._fake(body))
        self.assertEqual(st, "ok")
        self.assertIsNotNone(md)
        self.assertIn("## 知识精要", md)

    def test_empty_body_returns_none(self):
        import gen_kaodian_review as g
        kp, md, st = g._generate_one("数学", "复数", self._info(), {}, {}, self._fake("  "))
        self.assertIsNone(md)
        self.assertIn("空", st)

    def test_call_exception_returns_none(self):
        import gen_kaodian_review as g
        def boom(p):
            raise RuntimeError("net")
        kp, md, st = g._generate_one("数学", "复数", self._info(), {}, {}, boom)
        self.assertIsNone(md)
        self.assertIn("失败", st)


if __name__ == "__main__":
    unittest.main()
