import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import markdown  # noqa: E402
from _utils import mask_math, unmask_math  # noqa: E402


def _convert(body: str) -> str:
    """模拟管线：屏蔽数学 → markdown 转换 → 还原。"""
    masked, store = mask_math(body)
    md = markdown.Markdown(extensions=["tables", "fenced_code", "attr_list"])
    return unmask_math(md.convert(masked), store)


class TestMaskMath(unittest.TestCase):
    def test_inline_preserves_backslash_brace(self):
        # 核心 bug：$\left\{...\right\}$ 的反斜杠不能被 markdown 吃掉
        out = _convert(r"求数列 $\left\{\frac{1}{b_n}\right\}$ 的和")
        self.assertIn(r"\left\{", out)
        self.assertIn(r"\right\}", out)
        self.assertNotIn(r"\left{", out)

    def test_block_preserves_double_backslash(self):
        out = _convert("$$\\begin{cases}x+1\\\\y-2\\end{cases}$$")
        self.assertIn("\\\\", out)  # cases 换行 \\ 保留

    def test_ampersand_html_escaped(self):
        # 矩阵 & 必须 HTML 转义以免破坏 HTML 解析
        out = _convert(r"$\begin{cases}a & b\end{cases}$")
        self.assertIn("&amp;", out)
        self.assertNotIn(" & ", out)

    def test_markdown_still_works_outside_math(self):
        out = _convert("**粗体** 和 $x^2$")
        self.assertIn("<strong>粗体</strong>", out)
        self.assertIn("$x^2$", out)

    def test_multiple_spans_restored(self):
        out = _convert("$a_1$ 与 $a_2$ 与 $$b\\\\c$$")
        self.assertIn("$a_1$", out)
        self.assertIn("$a_2$", out)
        self.assertIn("b\\\\c", out)

    def test_no_math_unchanged(self):
        masked, store = mask_math("纯文本无公式")
        self.assertEqual(store, [])
        self.assertEqual(masked, "纯文本无公式")


if __name__ == "__main__":
    unittest.main()
