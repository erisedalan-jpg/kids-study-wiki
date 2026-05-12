"""测试真题流水线共享工具。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _exam_utils import (  # noqa: E402
    build_atom_filename,
    build_screenshot_filename,
    load_config,
    normalize_gender,
    normalize_paper,
)


class TestNormalize(unittest.TestCase):
    def setUp(self):
        self.cfg = load_config()

    def test_paper_long_key_first(self):
        # "新课标Ⅱ卷" 应该命中 "新课标Ⅱ" 而非 "新课标"
        self.assertEqual(
            normalize_paper("2024年高考数学试卷（新课标Ⅱ卷）.pdf", self.cfg),
            "新课标Ⅱ",
        )

    def test_paper_quanguoyi(self):
        self.assertEqual(
            normalize_paper("2022年高考数学试卷（文）（全国乙卷）.pdf", self.cfg),
            "全国乙",
        )

    def test_gender_wen(self):
        self.assertEqual(normalize_gender("2022...（文）...pdf", self.cfg), "文")
        self.assertEqual(normalize_gender("2022...（理）...pdf", self.cfg), "理")

    def test_gender_unknown_defaults(self):
        self.assertEqual(normalize_gender("2024-新课标Ⅱ.pdf", self.cfg), "不分")


class TestFilenames(unittest.TestCase):
    def test_atom_filename_with_gender(self):
        self.assertEqual(build_atom_filename(2022, "文", "全国乙", 1), "2022-文-01.md")

    def test_atom_filename_without_gender(self):
        # 2023+ 不分文理用卷别
        self.assertEqual(build_atom_filename(2024, "不分", "新课标Ⅱ", 8), "2024-新课标Ⅱ-08.md")

    def test_screenshot_filename(self):
        self.assertEqual(
            build_screenshot_filename(2022, "文", "全国乙", 1, "q"),
            "2022-文-01.q.png",
        )
        self.assertEqual(
            build_screenshot_filename(2024, "不分", "新课标Ⅱ", 8, "a"),
            "2024-新课标Ⅱ-08.a.png",
        )


if __name__ == "__main__":
    unittest.main()
