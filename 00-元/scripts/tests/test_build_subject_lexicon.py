"""测试 build_subject_lexicon.py 对 mini_subject fixture 的白名单提取。"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_subject_lexicon import build_lexicon  # noqa: E402


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mini_subject"


class TestBuildSubjectLexicon(unittest.TestCase):
    def test_extracts_bare_name_and_aliases(self):
        lex = build_lexicon(FIXTURE_DIR)
        # 每个词条的 bare-name 与 alias 都应进入白名单
        # 白名单结构: {term: {"bare": <bare-name>, "seq": <int|None>}}
        self.assertIn("函数", lex)
        self.assertIn("function", lex)
        self.assertIn("映射", lex)
        self.assertEqual(lex["函数"]["bare"], "函数")
        self.assertEqual(lex["function"]["bare"], "函数")
        # alias 共指向 bare-name
        self.assertEqual(lex["映射"]["bare"], "函数")

    def test_seq_extracted_from_filename_prefix(self):
        lex = build_lexicon(FIXTURE_DIR)
        self.assertEqual(lex["函数"]["seq"], 265)
        self.assertEqual(lex["数列"]["seq"], 100)
        self.assertEqual(lex["加法"]["seq"], 16)

    def test_term_count_at_least_8(self):
        lex = build_lexicon(FIXTURE_DIR)
        # 3 词条 × (bare + 2-3 aliases) = 至少 8 个 term
        self.assertGreaterEqual(len(lex), 8)


if __name__ == "__main__":
    unittest.main()
