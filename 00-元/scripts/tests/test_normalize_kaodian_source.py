import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestNormalizeSource(unittest.TestCase):
    def setUp(self):
        import normalize_kaodian_source as m
        self.m = m

    def test_map_tags_dedup_preserves_order(self):
        m = {"交集": "交集运算", "集合的交集运算": "交集运算"}
        self.assertEqual(self.m.map_tags(["交集", "集合的交集运算", "并集"], m),
                         ["交集运算", "并集"])

    def test_map_tags_passthrough_unmapped(self):
        self.assertEqual(self.m.map_tags(["复数除法", "复数乘法"], {}),
                         ["复数除法", "复数乘法"])

    def test_rewrite_changes_only_kaodian_line(self):
        text = ("---\n"
                "title: 2010-理-01\n"
                "考点: [集合的表示法, 复数除法]\n"
                "难度: 易\n"
                "---\n\n正文 考点: 不应被改\n")
        cmap = {"集合的表示法": "集合表示法"}
        new, before, after = self.m.rewrite_text(text, cmap)
        self.assertEqual(before, ["集合的表示法", "复数除法"])
        self.assertEqual(after, ["集合表示法", "复数除法"])
        self.assertIn("考点: [集合表示法, 复数除法]", new)
        self.assertIn("title: 2010-理-01", new)
        self.assertIn("难度: 易", new)
        self.assertIn("正文 考点: 不应被改", new)

    def test_rewrite_noop_when_no_change(self):
        text = "---\ntitle: x\n考点: [复数除法]\n---\n"
        new, before, after = self.m.rewrite_text(text, {})
        self.assertEqual(before, after)
        self.assertEqual(new, text)

    def test_rewrite_single_value(self):
        text = "---\n考点: 集合的表示法\n---\n"
        new, before, after = self.m.rewrite_text(text, {"集合的表示法": "集合表示法"})
        self.assertEqual(after, ["集合表示法"])
        self.assertIn("考点: [集合表示法]", new)


if __name__ == "__main__":
    unittest.main()
