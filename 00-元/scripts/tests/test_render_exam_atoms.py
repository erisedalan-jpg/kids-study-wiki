"""测试 render_exam_atoms.py 渲染真题词条。"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from render_exam_atoms import render_paper  # noqa: E402


SAMPLE = {
    "paper_id": "2024-不分-新课标Ⅱ",
    "year": 2024,
    "gender": "不分",
    "paper": "新课标Ⅱ",
    "subject": "数学",
    "province": "吉林",
    "source_pdf": "素材/真题/吉林/.../2024年.pdf",
    "questions": [
        {"qno": 8, "qtype": "选择", "score": 5,
         "stem": "已知 f(x)=x^2，求 f(2)。", "answer": "B",
         "solution": "代入 x=2 得 4。",
         "tags": ["函数"], "gap_terms": [], "difficulty": "易"},
    ],
}


class TestRenderExamAtoms(unittest.TestCase):
    def test_creates_atom_file_with_correct_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            files = render_paper(SAMPLE, output_root=tmp_path)
            self.assertEqual(len(files), 1)
            expected = tmp_path / "吉林-数学" / "2024-新课标Ⅱ-08.md"
            self.assertTrue(expected.exists())

    def test_atom_frontmatter_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            files = render_paper(SAMPLE, output_root=tmp_path)
            text = files[0].read_text(encoding="utf-8")
            self.assertIn("title: 2024-新课标Ⅱ-08", text)
            self.assertIn("年份: 2024", text)
            self.assertIn("题号: 8", text)
            self.assertIn("考点: [函数]", text)
            self.assertIn("录入状态: 已入库", text)
            self.assertIn("[[函数]]", text)


if __name__ == "__main__":
    unittest.main()
