import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestBlueprintCore(unittest.TestCase):
    def setUp(self):
        import gen_exam_blueprint as g
        self.g = g

    def test_parse_kaodian(self):
        self.assertEqual(self.g.parse_kaodian("[复数, 模长]"), ["复数", "模长"])
        self.assertEqual(self.g.parse_kaodian("集合"), ["集合"])
        self.assertEqual(self.g.parse_kaodian(""), [])

    def test_era_of(self):
        self.assertEqual(self.g.era_of(2008), "旧结构(08-22)")
        self.assertEqual(self.g.era_of(2022), "旧结构(08-22)")
        self.assertEqual(self.g.era_of(2023), "过渡(2023)")
        self.assertEqual(self.g.era_of(2024), "最新(24+)")
        self.assertEqual(self.g.era_of(2026), "最新(24+)")
        self.assertIsNone(self.g.era_of(2007))

    def test_difficulty_mode_tie_prefers_harder(self):
        self.assertEqual(self.g.difficulty_mode(["易", "易", "中"]), "易")
        self.assertEqual(self.g.difficulty_mode(["中", "难"]), "难")
        self.assertEqual(self.g.difficulty_mode([]), "?")

    def test_canon_applies_normalize(self):
        norm = {"复数的运算": "复数运算", "复数运算": "复数运算"}
        self.assertEqual(self.g.canon("复数的运算", norm), "复数运算")
        self.assertEqual(self.g.canon("未知考点", norm), "未知考点")

    def test_aggregate_segments_and_counts(self):
        rows = [
            {"年份": "2010", "文理": "理", "题型": "选择", "题号": "2",
             "难度": "易", "考点": "[复数的运算, 共轭复数]"},
            {"年份": "2012", "文理": "理", "题型": "选择", "题号": "2",
             "难度": "易", "考点": "[复数运算]"},
            {"年份": "2011", "文理": "文", "题型": "选择", "题号": "2",
             "难度": "易", "考点": "[集合]"},
            {"年份": "2024", "文理": "不分", "题型": "选择", "题号": "1",
             "难度": "易", "考点": "[复数, 模长]"},
        ]
        norm = {"复数的运算": "复数运算", "复数运算": "复数运算"}
        agg = self.g.aggregate(rows, norm)
        old = agg["旧结构(08-22)"][("选择", 2)]
        self.assertEqual(old["n"], 2)
        kp = dict(old["考点"])
        self.assertEqual(kp["复数运算"], 2)
        self.assertEqual(kp["共轭复数"], 1)
        self.assertEqual(old["难度倾向"], "易")
        self.assertIn(("选择", 1), agg["最新(24+)"])


if __name__ == "__main__":
    unittest.main()
