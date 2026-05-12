"""测试题号 bbox 定位 + 截图生成。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exam_screenshot import find_question_anchors, find_answer_anchors  # noqa: E402


class TestFindAnchors(unittest.TestCase):
    def test_question_anchor_basic(self):
        """words 含 '1.' '集合' 应识别 qno=1 的 anchor。"""
        # words: list[(x0, y0, x1, y1, text, block_no, line_no, word_no)]
        words = [
            (10, 100, 20, 110, "1.", 0, 0, 0),
            (25, 100, 50, 110, "集合", 0, 0, 1),
        ]
        anchors = find_question_anchors(words, expected_max_qno=23)
        self.assertEqual(anchors[1]["y0"], 100)

    def test_question_anchor_rejects_decimal(self):
        """'0.04' 不应被识别为题号 '0.'"""
        words = [
            (10, 100, 30, 110, "0.04", 0, 0, 0),
        ]
        anchors = find_question_anchors(words, expected_max_qno=23)
        self.assertEqual(anchors, {})

    def test_question_anchor_increment_only(self):
        """题号必须递增（从 1 开始），跳号丢弃。"""
        words = [
            (10, 100, 20, 110, "1.", 0, 0, 0),
            (10, 200, 30, 210, "5.", 0, 1, 0),  # 跳号
            (10, 300, 20, 310, "2.", 0, 2, 0),
        ]
        anchors = find_question_anchors(words, expected_max_qno=23)
        self.assertIn(1, anchors)
        self.assertIn(2, anchors)
        self.assertNotIn(5, anchors)

    def test_answer_anchor_detects_bracket(self):
        """'【答案】' 或 '【 答 案 】' 都应识别为 answer anchor。"""
        words = [
            (10, 100, 50, 110, "【答案】", 0, 0, 0),
            (10, 200, 60, 210, "【 答 案 】", 0, 1, 0),
        ]
        anchors = find_answer_anchors(words)
        self.assertEqual(len(anchors), 2)
        self.assertEqual(anchors[0]["y0"], 100)


from unittest.mock import MagicMock


class TestRegionsAndRender(unittest.TestCase):
    def _make_words(self, items):
        """items: list[(x0,y0,x1,y1,text)]"""
        return [(x[0], x[1], x[2], x[3], x[4], 0, i, 0) for i, x in enumerate(items)]

    def test_compute_question_regions_single_page(self):
        """同页 Q1: 题号→answer 之间是题面；answer→Q2 之间是解析。"""
        from exam_screenshot import compute_regions  # noqa
        words = self._make_words([
            (10, 100, 20, 110, "1."),
            (25, 100, 80, 110, "集合A=..."),
            (10, 200, 50, 210, "【答案】"),
            (10, 300, 50, 310, "解析内容"),
            (10, 400, 20, 410, "2."),
        ])
        q_anchors = find_question_anchors(words, 5)
        a_anchors = find_answer_anchors(words)
        regions = compute_regions(q_anchors, a_anchors, page_height=600)
        # Q1 题面: y=100→200 (answer 起)
        self.assertEqual(regions[1]["q"]["y0"], 100)
        self.assertAlmostEqual(regions[1]["q"]["y1"], 200, delta=5)
        # Q1 解析: y=200→400 (Q2 起)
        self.assertEqual(regions[1]["a"]["y0"], 200)
        self.assertAlmostEqual(regions[1]["a"]["y1"], 400, delta=5)

    def test_compute_question_regions_no_answer_uses_next_q(self):
        """如果没找到 answer anchor（罕见），题面延伸到下一题号。"""
        from exam_screenshot import compute_regions
        words = self._make_words([
            (10, 100, 20, 110, "1."),
            (10, 400, 20, 410, "2."),
        ])
        q_anchors = find_question_anchors(words, 5)
        a_anchors = find_answer_anchors(words)
        regions = compute_regions(q_anchors, a_anchors, page_height=600)
        self.assertAlmostEqual(regions[1]["q"]["y1"], 400, delta=5)
        self.assertIsNone(regions[1]["a"])


if __name__ == "__main__":
    unittest.main()
