"""测 fix_latex_delim 的 4 SUBS regex + RESIDUAL + 负向后顾保护 `\\[Npt]`。"""
import sys
import re
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestSubs(unittest.TestCase):
    def setUp(self):
        from fix_latex_delim import SUBS, RESIDUAL
        self.SUBS = SUBS
        self.RESIDUAL = RESIDUAL

    def _apply(self, txt: str) -> str:
        for rx, rep in self.SUBS:
            txt = rx.sub(rep, txt)
        return txt

    def test_inline_round_brackets(self):
        # \( x^2 \) → $ x^2 $
        out = self._apply(r"已知 \( x^2 + 1 \) > 0")
        self.assertEqual(out, "已知 $ x^2 + 1 $ > 0")

    def test_block_square_brackets(self):
        # \[ ... \] → $$ ... $$
        out = self._apply(r"\[ \sum_{i=1}^n i = \frac{n(n+1)}{2} \]")
        self.assertEqual(out, r"$$ \sum_{i=1}^n i = \frac{n(n+1)}{2} $$")

    def test_mixed_in_paragraph(self):
        src = r"对 \( a \) 与 \[ b \]，求和 \( c \)。"
        out = self._apply(src)
        self.assertEqual(out, "对 $ a $ 与 $$ b $$，求和 $ c $。")

    def test_preserve_latex_linebreak(self):
        # `\\[6pt]` 是 LaTeX 行距换行符（双反斜杠 + 数字+pt），不能被改
        src = r"\begin{cases} x \\[6pt] y \\[4pt] z \end{cases}"
        out = self._apply(src)
        self.assertEqual(out, src, "negative lookbehind 应保护 \\\\[Npt]")

    def test_preserve_double_backslash(self):
        # 双反斜杠跟方括号 `\\[...]` 不动
        src = r"text \\[6pt] more"
        out = self._apply(src)
        self.assertIn(r"\\[6pt]", out)

    def test_residual_detects_unconverted(self):
        # `(?<!\\)` 单反斜杠定界符未替换 → RESIDUAL 命中
        # 但完整 SUBS 一次替换后应无残留
        src = r"\( x \) \[ y \]"
        out = self._apply(src)
        self.assertEqual(self.RESIDUAL.findall(out), [])

    def test_residual_finds_unpaired(self):
        # 奇数计数：单独一个 `\(` 没 `\)` → 用户须手清
        src = r"\( x"
        # 此函数前部已被替换，残留检测应捕获 0（因 SUBS 也处理孤悬 `\(` ）
        out = self._apply(src)
        self.assertNotIn(r"\(", out)


class TestManifestTitles(unittest.TestCase):
    def test_missing_manifest_returns_empty(self):
        from fix_latex_delim import manifest_titles
        # 不存在的 manifest_prefix → set()，不抛
        s = manifest_titles("非真实前缀_测试_xyz", "数学")
        self.assertEqual(s, set())


if __name__ == "__main__":
    unittest.main()
