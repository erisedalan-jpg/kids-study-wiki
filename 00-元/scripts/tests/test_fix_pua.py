"""测 fix_pua.clean_pua：Adobe Symbol PUA → 真 Unicode。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestCleanPua(unittest.TestCase):
    def setUp(self):
        import fix_pua as f
        self.f = f

    def test_maps_common_symbols(self):
        # U+F07B→{ U+F07D→} U+F028→( U+F029→) U+F02D→− U+F03D→=
        s = ""
        self.assertEqual(self.f.clean_pua(s), "{}()−=")

    def test_maps_greek(self):
        # U+F070→π  U+F06D→μ
        s = ""
        self.assertEqual(self.f.clean_pua(s), "πμ")

    def test_passthrough_normal(self):
        s = "已知 x^2=1，π≈3"
        self.assertEqual(self.f.clean_pua(s), "已知 x^2=1，π≈3")

    def test_idempotent(self):
        # U+F028→( a U+F029→)
        raw = "a"
        once = self.f.clean_pua(raw)
        self.assertEqual(once, "(a)")
        self.assertEqual(once, self.f.clean_pua(once))

    def test_unknown_pua_dropped(self):
        # U+F0FF: low byte 0xFF, not in table, not printable ASCII (0x20–0x7E) → dropped
        s = "ab"
        self.assertEqual(self.f.clean_pua(s), "ab")

    def test_ascii_fallback(self):
        # U+F041: low byte 0x41 = 'A' — IS in table as Greek Α; but test printable ASCII fallback
        # U+F022: low byte 0x22 = '"' — not in table, but is printable ASCII → '"'
        s = ""
        self.assertEqual(self.f.clean_pua(s), '"')

    def test_real_world_braces(self):
        # 真实案例：比数列{na 中的 { } 是 PUA
        s = "比数列na的公比"
        self.assertEqual(self.f.clean_pua(s), "比数列{}na的公比")

    def test_math_symbols(self):
        # ≤ ≥ ± ∞ ∈ √
        s = ""
        self.assertEqual(self.f.clean_pua(s), "≤≥±∞∈√")

    def test_empty_string(self):
        self.assertEqual(self.f.clean_pua(""), "")

    def test_no_pua_unchanged(self):
        s = "f(x) = x² + 1"
        self.assertEqual(self.f.clean_pua(s), s)


if __name__ == "__main__":
    unittest.main()
