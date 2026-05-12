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


if __name__ == "__main__":
    unittest.main()
