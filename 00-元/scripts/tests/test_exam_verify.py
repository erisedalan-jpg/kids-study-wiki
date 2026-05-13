"""测试 L2 复验队列 (prepare/ingest)。"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exam_verify import (  # noqa: E402
    parse_verdict_response,
    render_verify_prompt,
)


class TestRenderVerifyPrompt(unittest.TestCase):
    def test_prompt_contains_image_and_tags(self):
        q = {
            "qno": 1,
            "题面图": "素材/真题截图/吉林-数学/2022-文-01.q.png",
            "tags": ["集合的运算", "并集"],
            "summary": "考集合的交集运算。",
        }
        prompt = render_verify_prompt(q)
        self.assertIn("2022-文-01.q.png", prompt)
        self.assertIn("集合的运算", prompt)
        self.assertIn("并集", prompt)
        self.assertIn("吻合", prompt)  # 评判选项


class TestParseVerdictResponse(unittest.TestCase):
    def test_pass(self):
        r = parse_verdict_response("吻合\ntags 与题面一致")
        self.assertEqual(r["verdict"], "吻合")
        self.assertEqual(r["note"], "tags 与题面一致")

    def test_partial(self):
        r = parse_verdict_response("部分偏差\ntags 中 '并集' 应改为 '交集'")
        self.assertEqual(r["verdict"], "部分偏差")
        self.assertIn("交集", r["note"])

    def test_severe(self):
        r = parse_verdict_response("严重偏差\n该题考的是导数不是集合")
        self.assertEqual(r["verdict"], "严重偏差")

    def test_unknown(self):
        r = parse_verdict_response("不确定")
        self.assertEqual(r["verdict"], "未识别")

    def test_empty(self):
        r = parse_verdict_response("")
        self.assertEqual(r["verdict"], "调用失败")


if __name__ == "__main__":
    unittest.main()
