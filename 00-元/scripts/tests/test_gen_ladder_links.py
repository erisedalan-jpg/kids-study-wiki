import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestInject(unittest.TestCase):
    def setUp(self):
        from gen_ladder_links import inject_links, build_reciprocal
        self.inject = inject_links
        self.recip = build_reciprocal

    def test_inject_into_existing_section(self):
        text = "# 乘法\n\n## 🔗 相关词条\n\n🚧\n\n## 📚 素材\n\n🚧\n"
        out = self.inject(text, 前置=[("016-加法", "加法")], 延伸=[("050-乘方", "乘方")])
        self.assertIn("**前置**", out)
        self.assertIn("[[016-加法|加法]]", out)
        self.assertIn("**延伸**", out)
        self.assertIn("[[050-乘方|乘方]]", out)
        self.assertNotIn("🚧\n\n## 📚 素材", out)
        self.assertIn("## 📚 素材", out)

    def test_inject_creates_section_if_missing(self):
        text = "# 乘法\n\n## 🎓 给 12+（进阶版）\n\n群。\n"
        out = self.inject(text, 前置=[("016-加法", "加法")], 延伸=[])
        self.assertIn("## 🔗 相关词条", out)
        self.assertIn("[[016-加法|加法]]", out)

    def test_build_reciprocal(self):
        edges = {"016-加法": {"延伸": ["030-乘法"], "前置": []}}
        recip = self.recip(edges)
        self.assertIn("030-乘法", recip)
        self.assertIn("016-加法", recip["030-乘法"]["前置"])

    def test_inject_preserves_existing_related(self):
        # 初中/高中词条已有相关词条列表，注入前置/延伸不得抹掉
        text = ("# 二次函数\n\n## 🔗 相关词条\n\n"
                "[[205-一元二次方程|一元二次方程]] · [[189-勾股定理|勾股定理]]\n\n"
                "## 📑 出处\n\nx\n")
        out = self.inject(text, 前置=[("212-二次函数定义", "二次函数定义")], 延伸=[])
        self.assertIn("**前置**", out)
        self.assertIn("[[212-二次函数定义|二次函数定义]]", out)
        self.assertIn("[[205-一元二次方程|一元二次方程]]", out)  # 既有保留
        self.assertIn("[[189-勾股定理|勾股定理]]", out)
        self.assertIn("## 📑 出处", out)

    def test_inject_idempotent(self):
        text = "# X\n\n## 🔗 相关词条\n\n[[001-数数|数数]]\n\n## 📚 素材\n\n🚧\n"
        once = self.inject(text, 前置=[("016-加法", "加法")], 延伸=[])
        twice = self.inject(once, 前置=[("016-加法", "加法")], 延伸=[])
        self.assertEqual(once, twice)
        self.assertEqual(once.count("**前置**"), 1)
        self.assertIn("[[001-数数|数数]]", once)


if __name__ == "__main__":
    unittest.main()
