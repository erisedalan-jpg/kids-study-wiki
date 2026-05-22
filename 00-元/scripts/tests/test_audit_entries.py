import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestAuditChecks(unittest.TestCase):
    def setUp(self):
        import audit_entries as ae
        self.ae = ae

    def _good_fm(self):
        return {
            "title": "加法", "aliases": "[加法, addition, plus]",
            "学科": "数学", "学段": "[小学]", "主题": "[数与运算]",
            "状态": "已完成", "英文术语": "addition",
        }

    def test_fm_ok(self):
        self.assertEqual(self.ae.check_frontmatter(self._good_fm(), "016-加法"), [])

    def test_fm_missing_field(self):
        fm = self._good_fm(); del fm["英文术语"]
        issues = self.ae.check_frontmatter(fm, "016-加法")
        self.assertTrue(any("英文术语" in i for i in issues))

    def test_fm_bare_not_first_alias(self):
        fm = self._good_fm(); fm["aliases"] = "[addition, 加法]"
        issues = self.ae.check_frontmatter(fm, "016-加法")
        self.assertTrue(any("bare" in i for i in issues))

    def test_body_layers_skeleton(self):
        text = "## 📚 给 6-12 岁（自读版）\n\n🚧\n\n## 🎓 给 12+（进阶版）\n\n实数。\n"
        issues = self.ae.check_body_layers(text)
        self.assertTrue(any("📚" in i and "骨架" in i for i in issues))

    def test_body_kid_layer_flagged(self):
        text = "## 🧒 给 3-6 岁（共读版）\n\n童语。\n\n## 📚 给 6-12 岁（自读版）\n\n合并。\n## 🎓 给 12+（进阶版）\n\n群。\n"
        issues = self.ae.check_body_layers(text)
        self.assertTrue(any("🧒" in i for i in issues))

    def test_textbook_ref_missing(self):
        text = "## 📑 出处与参考资料\n\n- **教材**：\n- **课标**：x\n"
        issues = self.ae.check_textbook_ref(text)
        self.assertTrue(any("教材" in i for i in issues))

    def test_textbook_ref_ok(self):
        text = ("## 📑 出处与参考资料\n\n- **教材**："
                "[[素材/教材/ChinaTextbook/小学/数学/人教版/x.pdf]] 第三单元\n")
        self.assertEqual(self.ae.check_textbook_ref(text), [])

    def test_unnormalized_wikilink(self):
        text = "见 [[减法]] 与 [[017-减法|减法]]"
        issues = self.ae.check_wikilinks(text)
        self.assertTrue(any("减法" in i for i in issues))

    def test_latex_delim_flagged(self):
        text = r"公式 \(x+1\) 与 \[y\]"
        issues = self.ae.check_math_delim(text)
        self.assertTrue(len(issues) >= 1)

    def test_body_hs_single_layer_ok(self):
        text = "## 🎓 考点精讲\n\n动量守恒定律。\n"
        self.assertEqual(self.ae.check_body_layers(text, "高中"), [])

    def test_fm_missing_aliases_single_report(self):
        fm = self._good_fm(); del fm["aliases"]
        issues = self.ae.check_frontmatter(fm, "016-加法")
        self.assertEqual(sum("aliases" in i for i in issues), 1)

    def test_textbook_ref_volume_ok(self):
        text = ("## 📑 出处与参考资料\n\n- **教材**："
                "[[素材/教材/ChinaTextbook/小学/数学/人教版/x.pdf]] 第三册\n")
        self.assertEqual(self.ae.check_textbook_ref(text), [])

    def test_textbook_ref_prep_lesson_and_booktitle_ok(self):
        # 准备课《数一数》—— 非「第N单元」但有书名号/准备课，应视为有具体章节
        text = ("## 📑 出处\n\n- **教材**："
                "[[素材/教材/ChinaTextbook/小学/数学/人教版/x.pdf]] 准备课《数一数》\n")
        self.assertEqual(self.ae.check_textbook_ref(text), [])

    def test_textbook_ref_short_header_ok(self):
        # 精简标题 「## 📑 出处」 也应识别
        text = ("## 📑 出处\n\n- **教材**："
                "[[素材/教材/ChinaTextbook/初中/数学/人教版/x.pdf]] 第一章\n")
        self.assertEqual(self.ae.check_textbook_ref(text), [])

    def test_textbook_ref_no_bold_ok(self):
        # 无粗体标记 `- 教材：` 也应识别（部分批次词条用此格式）
        text = ("## 📑 出处\n\n- 教材："
                "[[素材/教材/ChinaTextbook/初中/数学/人教版/x.pdf]] 第十七章\n")
        self.assertEqual(self.ae.check_textbook_ref(text), [])


if __name__ == "__main__":
    unittest.main()
