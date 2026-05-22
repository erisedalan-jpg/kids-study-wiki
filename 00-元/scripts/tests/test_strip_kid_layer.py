import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestStripKidSection(unittest.TestCase):
    def setUp(self):
        from strip_kid_layer import strip_kid_section
        self.strip = strip_kid_section

    def test_removes_kid_section_keeps_others(self):
        text = (
            "# 加法\n\n## 🧒 给 3-6 岁（共读版）\n\n两个苹果合起来。\n\n"
            "## 📚 给 6-12 岁（自读版）\n\n加法是合并。\n\n"
            "## 🎓 给 12+（进阶版）\n\n加法群。\n"
        )
        out, changed = self.strip(text)
        self.assertTrue(changed)
        self.assertNotIn("🧒", out)
        self.assertNotIn("两个苹果", out)
        self.assertIn("## 📚 给 6-12 岁（自读版）", out)
        self.assertIn("加法是合并", out)
        self.assertIn("## 🎓 给 12+（进阶版）", out)

    def test_no_kid_section_unchanged(self):
        text = "# 加法\n\n## 📚 给 6-12 岁（自读版）\n\n加法是合并。\n"
        out, changed = self.strip(text)
        self.assertFalse(changed)
        self.assertEqual(out, text)

    def test_kid_section_bounded_by_hr(self):
        text = (
            "# X\n\n## 🧒 给 3-6 岁（共读版）\n\n童语。\n\n---\n\n## 🌐 中英对照\n"
        )
        out, changed = self.strip(text)
        self.assertTrue(changed)
        self.assertNotIn("童语", out)
        self.assertIn("## 🌐 中英对照", out)
        self.assertIn("---", out)


if __name__ == "__main__":
    unittest.main()
