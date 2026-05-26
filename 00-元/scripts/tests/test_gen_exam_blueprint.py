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

    def test_parse_kaodian_chinese_punctuation(self):
        # 中文逗号/顿号也应拆分（防 LLM/手录脏数据污染频次）
        self.assertEqual(self.g.parse_kaodian("[函数，导数]"), ["函数", "导数"])
        self.assertEqual(self.g.parse_kaodian("[向量、数量积]"), ["向量", "数量积"])
        self.assertEqual(self.g.parse_kaodian("[复数, 模长，共轭]"), ["复数", "模长", "共轭"])

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


class TestBlueprintIO(unittest.TestCase):
    def setUp(self):
        import gen_exam_blueprint as g
        self.g = g

    def test_load_normalize_missing_returns_empty(self):
        from pathlib import Path
        self.assertEqual(self.g.load_normalize(Path("/no/such/file.yaml")), {})

    def test_dump_kaodian_counts_distinct(self):
        rows = [
            {"考点": "[复数, 模长]"},
            {"考点": "[复数]"},
            {"考点": "集合"},
        ]
        d = dict(self.g.dump_kaodian(rows))
        self.assertEqual(d["复数"], 2)
        self.assertEqual(d["模长"], 1)
        self.assertEqual(d["集合"], 1)

    def test_read_rows_reads_real_exam_dir(self):
        rows = self.g.read_rows()
        self.assertGreater(len(rows), 500)
        self.assertTrue(all("年份" in r for r in rows))


class TestBlueprintHTML(unittest.TestCase):
    def setUp(self):
        import gen_exam_blueprint as g
        self.g = g
        self.agg = {
            "旧结构(08-22)": {("选择", 2): {"n": 40, "难度倾向": "易",
                "考点": [("复数运算", 12), ("共轭复数", 7)]}},
            "最新(24+)": {("选择", 1): {"n": 1, "难度倾向": "易",
                "考点": [("复数", 1), ("模长", 1)]}},
        }

    def test_render_has_three_era_headers_and_slots(self):
        page = self.g.render_html(self.agg)
        self.assertIn("旧结构(08-22)", page)
        self.assertIn("最新(24+)", page)
        self.assertIn("选择2", page)
        self.assertIn("复数运算", page)
        self.assertIn("12", page)
        self.assertIn("n=40", page)

    def test_render_has_print_css_and_katex(self):
        page = self.g.render_html(self.agg)
        self.assertIn("@media print", page)
        self.assertIn("break-inside", page)
        self.assertIn("page-break-before", page)
        self.assertIn("vendor/katex/katex.min.css", page)
        self.assertIn("vendor/style.css", page)

    def test_render_marks_thin_sample(self):
        page = self.g.render_html(self.agg)
        # n=1 slot ("最新(24+)" 选择1) must carry the thin note
        self.assertIn("（样本仅 1，规律参考）", page)
        # n=40 slot ("旧结构(08-22)" 选择2) must NOT carry the thin note
        self.assertNotIn("（样本仅 40，规律参考）", page)


if __name__ == "__main__":
    unittest.main()
