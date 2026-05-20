"""测 fix_stale_links 的 split_inner（核心管线分组）+ NUMPFX。

主体 main 端到端依赖真实 repo（cur_stems/bare2stems 模块顶层扫描），
本测试仅覆盖可纯函数化逻辑；集成路径留待引入 --repo 参数后补。
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestSplitInner(unittest.TestCase):
    def setUp(self):
        from fix_stale_links import split_inner
        self.split = split_inner

    def test_no_pipe(self):
        t, sep, d = self.split("017-减法")
        self.assertEqual((t, sep, d), ("017-减法", "", ""))

    def test_simple_pipe(self):
        t, sep, d = self.split("017-减法|减法")
        self.assertEqual((t, sep, d), ("017-减法", "|", "减法"))

    def test_escaped_pipe_for_table(self):
        # 表格行内必须用 `\|` 转义
        t, sep, d = self.split("017-减法\\|减法")
        self.assertEqual((t, sep, d), ("017-减法", "\\|", "减法"))

    def test_pipe_then_disp_with_spaces(self):
        t, sep, d = self.split("  017-减法  |  减法显示  ")
        self.assertEqual(t, "017-减法")
        self.assertEqual(sep, "|")
        # disp 不 strip，保留原样
        self.assertEqual(d, "  减法显示  ")


class TestNumPfx(unittest.TestCase):
    def test_match(self):
        from fix_stale_links import NUMPFX
        m = NUMPFX.match("017-减法")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "017")
        self.assertEqual(m.group(2), "减法")

    def test_no_match(self):
        from fix_stale_links import NUMPFX
        self.assertIsNone(NUMPFX.match("减法"))
        self.assertIsNone(NUMPFX.match("abc-减法"))

    def test_match_with_hyphen_in_name(self):
        from fix_stale_links import NUMPFX
        m = NUMPFX.match("2022-文-01")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "2022")
        self.assertEqual(m.group(2), "文-01")


class TestLinkRegex(unittest.TestCase):
    def test_link_extract(self):
        from fix_stale_links import LINK
        text = "见 [[017-减法|减法]] 和 [[20-加法]]，外加 [[2022-文-01]]"
        ms = LINK.findall(text)
        self.assertEqual(ms, ["017-减法|减法", "20-加法", "2022-文-01"])

    def test_link_not_match_section(self):
        # 注：fix_stale_links 内会单独处理 # 跳过
        from fix_stale_links import LINK
        ms = LINK.findall("[[017-减法#章节]]")
        self.assertEqual(ms, ["017-减法#章节"])


if __name__ == "__main__":
    unittest.main()
