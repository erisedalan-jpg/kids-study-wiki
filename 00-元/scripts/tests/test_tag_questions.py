"""测试 tag_questions.py 候选 tag 生成。"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tag_questions import tag_paper  # noqa: E402

FIX = Path(__file__).parent / "fixtures"


class TestTagQuestions(unittest.TestCase):
    def setUp(self):
        self.qa = json.loads((FIX / "mini_qa.json").read_text(encoding="utf-8"))
        self.lex = json.loads((FIX / "mini_lexicon.json").read_text(encoding="utf-8"))

    def test_q1_hits_function_and_monotonicity(self):
        result = tag_paper(self.qa, self.lex)
        q1 = result["questions"][0]
        self.assertIn("函数", q1["tag_candidates"])
        self.assertIn("单调性", q1["tag_candidates"])
        self.assertIn("导数", q1["tag_candidates"])

    def test_q2_hits_sequence(self):
        result = tag_paper(self.qa, self.lex)
        q2 = result["questions"][1]
        self.assertIn("数列", q2["tag_candidates"])
        self.assertIn("等差数列", q2["tag_candidates"])

    def test_no_false_positive_addition(self):
        # "加法" 在白名单里但题面无明显出现 → 不应误命中
        result = tag_paper(self.qa, self.lex)
        for q in result["questions"]:
            self.assertNotIn("加法", q["tag_candidates"])


if __name__ == "__main__":
    unittest.main()
