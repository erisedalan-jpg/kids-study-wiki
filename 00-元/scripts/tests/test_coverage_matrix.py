import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestExtractConcepts(unittest.TestCase):
    def setUp(self):
        from coverage_matrix import extract_concepts
        self.extract = extract_concepts

    def test_pulls_link_targets_and_bold_terms(self):
        doc = (
            "# 学习路径\n\n### 阶段 1\n"
            "- 数一数 → [[001-数数|数数]] [[003-1-10|1-10]]\n"
            "- 上下前后左右 → [[015-位置|位置]] (新)\n\n"
            "## 重点知识点全单\n\n"
            "1. **凑十法**: 9+5\n"
            "2. **数位**: 个/十位\n"
        )
        got = self.extract(doc)
        self.assertIn("数数", got)
        self.assertIn("1-10", got)
        self.assertIn("位置", got)
        self.assertIn("凑十法", got)
        self.assertIn("数位", got)

    def test_dedup(self):
        doc = "- a → [[016-加法|加法]] [[016-加法|加法]]\n## 重点知识点全单\n1. **加法**: x\n"
        got = self.extract(doc)
        self.assertEqual(got.count("加法"), 1)


class TestClassify(unittest.TestCase):
    def test_gap_when_unresolved(self):
        from coverage_matrix import classify_concept
        targets = {"加法": "016-加法"}
        self.assertEqual(classify_concept("加法", targets), ("covered", "016-加法"))
        self.assertEqual(classify_concept("微积分", targets), ("GAP", ""))


if __name__ == "__main__":
    unittest.main()
