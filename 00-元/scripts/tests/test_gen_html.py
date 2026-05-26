import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestThresholdText(unittest.TestCase):
    def setUp(self):
        import gen_html
        self.gh = gen_html

    def test_default_threshold_is_3(self):
        self.assertEqual(self.gh.DEFAULT_THRESHOLD, 3)

    def test_home_text_uses_threshold(self):
        page = self.gh.gen_home({"数学": 1, "物理": 0, "化学": 0, "生物": 0}, 1, threshold=3)
        self.assertIn("weight ≥ 3", page)
        self.assertNotIn("weight ≥ 10", page)


if __name__ == "__main__":
    unittest.main()
