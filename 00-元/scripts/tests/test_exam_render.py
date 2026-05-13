"""测试 v2 词条渲染。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exam_render import render_atom  # noqa: E402


class TestRenderAtom(unittest.TestCase):
    def setUp(self):
        self.qa_meta = {
            "year": 2022,
            "gender": "文",
            "paper": "全国乙",
            "subject": "数学",
            "province": "吉林",
            "source_pdf": "素材/真题/吉林/.../2022.pdf",
        }
        self.q = {
            "qno": 1,
            "page": 1,
            "题面图": "素材/真题截图/吉林-数学/2022-文-01.q.png",
            "解析图": "素材/真题截图/吉林-数学/2022-文-01.a.png",
            "answer": "A",
            "summary": "考集合的交集运算",
            "tags": ["集合的运算", "并集"],
            "difficulty": "易",
        }

    def test_frontmatter_fields_present(self):
        text = render_atom(self.qa_meta, self.q)
        for field in ["title:", "学科:", "年份:", "卷别:", "文理:", "题号:",
                       "考点:", "答案:", "PDF页码:", "题面图:", "解析图:"]:
            self.assertIn(field, text, f"missing {field}")

    def test_includes_screenshots(self):
        text = render_atom(self.qa_meta, self.q)
        self.assertIn("![](../../素材/真题截图/吉林-数学/2022-文-01.q.png)", text)
        self.assertIn("![](../../素材/真题截图/吉林-数学/2022-文-01.a.png)", text)

    def test_includes_tags_backlinks(self):
        text = render_atom(self.qa_meta, self.q)
        self.assertIn("[[集合的运算]]", text)
        self.assertIn("[[并集]]", text)

    def test_summary_section(self):
        text = render_atom(self.qa_meta, self.q)
        self.assertIn("考集合的交集运算", text)

    def test_status_done_when_tags_nonempty(self):
        text = render_atom(self.qa_meta, self.q)
        self.assertIn("录入状态: 已入库", text)


if __name__ == "__main__":
    unittest.main()
