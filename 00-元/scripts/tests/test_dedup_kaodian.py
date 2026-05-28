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


if __name__ == "__main__":
    unittest.main()
