import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestUpsertSections(unittest.TestCase):
    def setUp(self):
        import extract_exam_text as e
        self.e = e

    def test_upsert_appends_when_absent(self):
        md = "---\n题号: 1\n---\n\n## 摘要\n一行\n"
        out = self.e.upsert_text_sections(md, stem="题干X", sol="解析Y")
        self.assertIn("## 题干文本\n题干X", out)
        self.assertIn("## 解析文本\n解析Y", out)
        self.assertIn("## 摘要\n一行", out)        # 不破坏既有

    def test_upsert_replaces_bare_heading(self):
        md = "## 题干文本\n旧\n\n## 解析文本\n旧\n"
        out = self.e.upsert_text_sections(md, stem="新题干", sol="新解析")
        self.assertIn("## 题干文本\n新题干", out)
        self.assertNotIn("旧", out)
        self.assertEqual(out.count("## 题干文本"), 1)   # 不重复追加

    def test_upsert_idempotent_via_markers(self):
        once = self.e.upsert_text_sections("---\n题号: 1\n---\n", stem="A", sol="B")
        twice = self.e.upsert_text_sections(once, stem="A2", sol="B2")
        self.assertEqual(twice.count("## 题干文本"), 1)
        self.assertEqual(twice.count("## 解析文本"), 1)
        self.assertIn("A2", twice)
        self.assertNotIn("A2", once)   # sanity: second call changed content
        self.assertNotIn("\nA\n", twice)  # old stem replaced


if __name__ == "__main__":
    unittest.main()
