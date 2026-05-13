"""测试索引聚合 + 反链回填。"""
import sys
import unittest
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exam_index import build_freq_table, build_gap_list, BACKLINK_START, BACKLINK_END  # noqa: E402


class TestFreqTable(unittest.TestCase):
    def test_count_tags(self):
        atoms = [
            {"考点": ["集合的运算", "并集"], "题号": 1, "卷别": "全国乙", "文理": "文"},
            {"考点": ["集合的运算", "交集"], "题号": 2, "卷别": "全国乙", "文理": "文"},
            {"考点": ["函数最值"], "题号": 5, "卷别": "全国乙", "文理": "文"},
        ]
        freq = build_freq_table(atoms)
        self.assertEqual(freq["集合的运算"], 2)
        self.assertEqual(freq["并集"], 1)
        self.assertEqual(freq["函数最值"], 1)


class TestGapList(unittest.TestCase):
    def test_gap_detection(self):
        atoms = [
            {"考点": ["集合的运算", "未知概念"], "题号": 1, "卷别": "全国乙", "文理": "文"},
        ]
        existing = {"集合的运算"}  # lexicon
        gaps = build_gap_list(atoms, existing)
        self.assertIn("未知概念", gaps)
        self.assertNotIn("集合的运算", gaps)


class TestBacklinkMarkers(unittest.TestCase):
    def test_markers_defined(self):
        self.assertEqual(BACKLINK_START, "<!-- exam-backlinks-start -->")
        self.assertEqual(BACKLINK_END, "<!-- exam-backlinks-end -->")


if __name__ == "__main__":
    unittest.main()
