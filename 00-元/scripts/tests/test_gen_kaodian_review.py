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


if __name__ == "__main__":
    unittest.main()
