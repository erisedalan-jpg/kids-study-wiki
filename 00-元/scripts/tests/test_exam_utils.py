"""测试 _exam_utils.py 公共工具的 4 个核心函数。"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _exam_utils import (  # noqa: E402
    load_config,
    normalize_paper,
    normalize_gender,
    build_atom_filename,
    is_in_tag_pool,
)


class TestExamUtils(unittest.TestCase):
    def test_load_config_returns_dict_with_subjects(self):
        cfg = load_config()
        self.assertIn("subjects", cfg)
        self.assertIn("数学", cfg["subjects"])

    def test_normalize_paper_long_key_first(self):
        cfg = load_config()
        # "新课标Ⅱ卷" 必须命中"新课标Ⅱ"，不能被"新课标"抢
        self.assertEqual(normalize_paper("2024年高考数学试卷（新课标Ⅱ卷）（解析卷）.pdf", cfg), "新课标Ⅱ")
        self.assertEqual(normalize_paper("2021年高考数学试卷（理）（全国乙卷）（新课标Ⅰ）（解析卷）.pdf", cfg), "全国乙")
        self.assertEqual(normalize_paper("2010年高考数学试卷（文）（新课标）（解析卷）.pdf", cfg), "新课标")

    def test_normalize_gender(self):
        cfg = load_config()
        self.assertEqual(normalize_gender("2017年高考数学试卷（文）（新课标Ⅱ）.pdf", cfg), "文")
        self.assertEqual(normalize_gender("2017年高考数学试卷（理）（新课标Ⅱ）.pdf", cfg), "理")
        self.assertEqual(normalize_gender("2024年高考数学试卷（新课标Ⅱ卷）.pdf", cfg), "不分")

    def test_build_atom_filename(self):
        # 2017 文理分卷 → 2017-理-08
        self.assertEqual(build_atom_filename(2017, "理", "新课标Ⅱ", 8), "2017-理-08.md")
        # 2024 不分文理 → 2024-新课标Ⅱ-08
        self.assertEqual(build_atom_filename(2024, "不分", "新课标Ⅱ", 8), "2024-新课标Ⅱ-08.md")

    def test_is_in_tag_pool(self):
        cfg = load_config()
        # 高中数学序号范围内
        self.assertTrue(is_in_tag_pool("函数", 300, "数学", cfg))
        # 初中数学但在额外纳入清单
        self.assertTrue(is_in_tag_pool("数列", 100, "数学", cfg))
        # 小学数学，不在额外纳入清单
        self.assertFalse(is_in_tag_pool("加法", 16, "数学", cfg))


if __name__ == "__main__":
    unittest.main()
