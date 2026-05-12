"""测试 _utils.bare_name 对真题目录与普通学科目录的差异化行为。"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _utils import bare_name  # noqa: E402


class TestBareName(unittest.TestCase):
    def test_normal_subject_strips_numeric_prefix(self):
        # 普通学科词条：2-4 位数字前缀是序号，应剥掉
        self.assertEqual(bare_name(Path("数学/016-加法.md")), "加法")
        self.assertEqual(bare_name(Path("语文/001-拼音.md")), "拼音")
        self.assertEqual(bare_name(Path("数学/73-圆周率.md")), "圆周率")

    def test_exam_atom_preserves_year_prefix(self):
        # 真题词条：YYYY- 是年份，不应剥掉，否则跨年同名冲突
        self.assertEqual(
            bare_name(Path("真题/吉林-数学/2022-文-01.md")),
            "2022-文-01",
        )
        self.assertEqual(
            bare_name(Path("真题/吉林-数学/2024-新课标Ⅱ-08.md")),
            "2024-新课标Ⅱ-08",
        )
        # 不同年的同卷别同题号必须 bare 不冲突
        self.assertNotEqual(
            bare_name(Path("真题/吉林-数学/2022-文-01.md")),
            bare_name(Path("真题/吉林-数学/2020-文-01.md")),
        )

    def test_no_prefix_unchanged(self):
        self.assertEqual(bare_name(Path("数学/加法.md")), "加法")


if __name__ == "__main__":
    unittest.main()
