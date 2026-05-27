import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestValidateReview(unittest.TestCase):
    def setUp(self):
        import validate_review as v
        self.v = v

    def test_clean_doc_passes(self):
        md = ("---\n考点: 复数\n父主题: 复数\n学科: 数学\n状态: 草稿\n---\n"
              "## 考点定位\nx\n## 知识精要\n模长 $|z|$\n## 解题方法与套路\nx\n"
              "## 高频易错\nx\n## 代表题精讲\nx\n## 全部真题清单\n- [[a]]\n## 关联\nx\n")
        self.assertEqual(self.v.check(md), [])

    def test_flags_latex_delim_and_missing_block(self):
        md = ("---\n考点: 复数\n父主题: 复数\n学科: 数学\n状态: 草稿\n---\n"
              "## 考点定位\n模长 \\(|z|\\)\n## 知识精要\nx\n## 高频易错\nx\n"
              "## 代表题精讲\nx\n## 全部真题清单\nx\n## 关联\nx\n")
        errs = self.v.check(md)
        self.assertTrue(any("LaTeX 定界符" in e for e in errs))
        self.assertTrue(any("缺区块" in e and "解题方法与套路" in e for e in errs))

    def test_flags_code_fence(self):
        md = ("---\n考点: x\n父主题: y\n学科: 数学\n状态: 草稿\n---\n"
              "## 考点定位\n```\n围栏\n```\n## 知识精要\nx\n## 解题方法与套路\nx\n"
              "## 高频易错\nx\n## 代表题精讲\nx\n## 全部真题清单\nx\n## 关联\nx\n")
        self.assertTrue(any("代码围栏" in e for e in self.v.check(md)))


if __name__ == "__main__":
    unittest.main()
