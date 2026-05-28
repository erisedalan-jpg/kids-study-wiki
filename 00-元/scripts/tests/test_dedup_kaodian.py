import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestSimilarity(unittest.TestCase):
    def setUp(self):
        import dedup_kaodian as d
        self.d = d

    def test_bigram_jaccard(self):
        self.assertAlmostEqual(self.d.s_bigram("交集运算", "交集运算"), 1.0)
        self.assertEqual(self.d.s_bigram("集合", "数列"), 0.0)

    def test_char_jaccard(self):
        self.assertEqual(self.d.s_jaccard("集合", "数列"), 0.0)
        self.assertGreater(self.d.s_jaccard("交集", "交集运算"), 0.4)

    def test_edit(self):
        self.assertAlmostEqual(self.d.s_edit("交集", "交集"), 1.0)
        self.assertLess(self.d.s_edit("集合", "数列"), 0.3)

    def test_name_similarity_high_for_synonyms(self):
        self.assertGreaterEqual(self.d.name_similarity("交集", "交集运算"), 0.85)
        self.assertGreaterEqual(self.d.name_similarity("集合的交集运算", "交集运算"), 0.85)
        self.assertGreaterEqual(self.d.name_similarity("函数单调性", "函数的单调性"), 0.85)

    def test_name_similarity_low_for_distinct(self):
        self.assertLess(self.d.name_similarity("集合", "数列"), 0.3)
        self.assertLess(self.d.name_similarity("复数", "导数"), 0.5)

    def test_empty_strings(self):
        self.assertEqual(self.d.name_similarity("", ""), 0.0)
        self.assertEqual(self.d.name_similarity("", "交集"), 0.0)
        self.assertEqual(self.d.name_similarity("交集", ""), 0.0)

    def test_single_char_identical(self):
        self.assertEqual(self.d.name_similarity("点", "点"), 1.0)

    def test_strip_tail_no_overflow(self):
        self.assertEqual(self.d._strip_tail("运算"), "运算")
        self.assertEqual(self.d._strip_tail("交集运算"), "交集")

    def test_denoise_removes_noise(self):
        self.assertEqual(self.d._denoise("函数的单调性"), "函数单调性")


class TestContrast(unittest.TestCase):
    def setUp(self):
        import dedup_kaodian as d
        self.d = d
        self.groups = [{"乘法", "除法"}, {"正弦", "余弦"}, {"平行", "垂直"},
                       {"交集", "并集", "补集"}]

    def test_redline_pairs_are_contrast(self):
        self.assertTrue(self.d.is_contrast_pair("复数乘法", "复数除法", self.groups))
        self.assertTrue(self.d.is_contrast_pair("正弦定理", "余弦定理", self.groups))
        self.assertTrue(self.d.is_contrast_pair("线面平行", "线面垂直", self.groups))
        self.assertTrue(self.d.is_contrast_pair("交集运算", "并集运算", self.groups))

    def test_contrast_is_symmetric(self):
        self.assertTrue(self.d.is_contrast_pair("余弦定理", "正弦定理", self.groups))

    def test_synonyms_are_not_contrast(self):
        self.assertFalse(self.d.is_contrast_pair("交集", "交集运算", self.groups))
        self.assertFalse(self.d.is_contrast_pair("函数单调性", "函数的单调性", self.groups))

    def test_load_contrast_groups_real_file(self):
        g = self.d.load_contrast_groups("数学")
        self.assertTrue(any({"正弦", "余弦"} <= grp for grp in g))
        self.assertTrue(all(isinstance(grp, set) for grp in g))


class TestLoaders(unittest.TestCase):
    def setUp(self):
        import dedup_kaodian as d
        self.d = d

    def test_stats_from_rows_normalizes_and_counts(self):
        # 行内考点为字符串；经 normalize 归一后按规范名计真题数
        rows = [
            {"考点": "[交集, 集合的交集]", "年份": "2020", "题型": "选择", "题号": "1", "难度": "易"},
            {"考点": "交集运算", "年份": "2019", "题型": "选择", "题号": "2", "难度": "易"},
        ]
        normalize = {"交集": "交集运算", "集合的交集": "交集运算", "交集运算": "交集运算"}
        group = {"交集运算": "集合"}
        stats = self.d.stats_from_rows(rows, normalize, group)
        self.assertEqual(stats["交集运算"]["真题数"], 2)
        self.assertEqual(stats["交集运算"]["父主题"], "集合")

    def test_load_canonical_names_real_math(self):
        names = self.d.load_canonical_names("数学")
        self.assertIn("交集运算", names)
        self.assertIsInstance(names, set)
        self.assertGreater(len(names), 50)

    def test_load_parent_map_real_math(self):
        pm = self.d.load_parent_map("数学")
        self.assertIn("复数", pm)

    def test_load_canonical_names_unknown_subject_raises(self):
        with self.assertRaises(SystemExit):
            self.d.load_canonical_names("音乐")


if __name__ == "__main__":
    unittest.main()
