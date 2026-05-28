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


if __name__ == "__main__":
    unittest.main()
