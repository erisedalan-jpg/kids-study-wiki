"""测 pdf_content_diff 的 normalize（剥水印 + 空白 + 标点宽窄）+ resolve_dir。

cmp_pair 需真 PDF fixture（暂略），靠 normalize 单元测覆盖核心归一化逻辑。
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestNormalize(unittest.TestCase):
    def setUp(self):
        from pdf_content_diff import normalize
        self.norm = normalize

    def test_strip_whitespace(self):
        self.assertEqual(self.norm("a b\n c\td"), "abcd")

    def test_strip_url(self):
        out = self.norm("题目 www.example.com 真题 https://foo.bar/path")
        self.assertEqual(out, "题目真题")

    def test_strip_xuekewang_actual_behavior(self):
        # NOISE 第 0 条 `学科网[（(].*?[)）]?` 是 lazy + 可选末括 → 实际只剥
        # `学科网(` 前缀，右括号与括号内文残留。本测固定**当前行为**，
        # 修正逻辑应使 `[)）]?` 改 `[)）]` 强制吃右括（见 follow-up）。
        out = self.norm("题目 学科网(北京)股份有限公司 正文")
        self.assertEqual(out, "题目北京)股份有限公司正文")

    def test_strip_jiaoyu(self):
        # 含「教育网」类后缀（NOISE 第 4 条）
        out = self.norm("题目 中考教育网 正文")
        self.assertEqual(out, "题目正文")

    def test_strip_page_marker(self):
        out = self.norm("正文 第 3 页 共 10 页 续")
        self.assertEqual(out, "正文续")

    def test_strip_camscanner(self):
        out = self.norm("正文 CamScanner 续")
        self.assertEqual(out, "正文续")

    def test_punct_full_to_half(self):
        # 中文标点 → 英文标点，去空白后比对
        out = self.norm("（甲）；（乙），（丙）：？！．、")
        self.assertEqual(out, "(甲);(乙),(丙):?!.,")

    def test_strip_secret(self):
        out = self.norm("绝密★启用前 正文")
        self.assertEqual(out, "正文")

    def test_strip_long_digit_id(self):
        # ≥6 位连续数字（疑似流水号/电话）被剥
        out = self.norm("正文 123456 续")
        self.assertEqual(out, "正文续")

    def test_preserve_short_digit(self):
        # 4 位以下数字保留（年份/题号）
        out = self.norm("2022 第 1 题")
        self.assertEqual(out, "2022第1题")


class TestResolveDir(unittest.TestCase):
    def test_absolute_path(self):
        from pdf_content_diff import resolve_dir, REPO
        # 绝对路径原样返回
        if sys.platform.startswith("win"):
            abs_p = "C:\\temp\\foo"
        else:
            abs_p = "/tmp/foo"
        self.assertEqual(str(resolve_dir(abs_p)), abs_p.replace("/", "\\") if sys.platform.startswith("win") else abs_p)

    def test_relative_path_joined_to_repo(self):
        from pdf_content_diff import resolve_dir, REPO
        out = resolve_dir("素材/真题/吉林")
        self.assertEqual(out, REPO / "素材/真题/吉林")


if __name__ == "__main__":
    unittest.main()
