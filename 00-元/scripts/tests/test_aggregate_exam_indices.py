"""测试 aggregate_exam_indices.py 聚合 4 份索引 + 反链回填。"""

import sys
import tempfile
import unittest
from pathlib import Path
from textwrap import dedent

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aggregate_exam_indices import aggregate  # noqa: E402


def _write_atom(d: Path, name: str, year: int, qno: int, qtype: str, tags: list[str], gaps: list[str] | None = None):
    fm = dedent(f"""\
        ---
        title: {name.removesuffix('.md')}
        aliases: [{name.removesuffix('.md')}]
        学科: 数学
        学段: 高考
        省份: 吉林
        年份: {year}
        卷别: 新课标Ⅱ
        文理: 不分
        题号: {qno}
        题型: {qtype}
        分值: 5
        考点: [{', '.join(tags)}]
        难度: 中
        录入状态: 已入库
        来源PDF: dummy
        ---

        ## 题面
        dummy
    """)
    body = fm
    if gaps:
        body += "\n## 白名单缺口（待考虑建词条）\n" + "\n".join(f"- {g}" for g in gaps) + "\n"
    (d / name).write_text(body, encoding="utf-8")


class TestAggregateExamIndices(unittest.TestCase):
    def test_creates_four_indices_and_backlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            atom_dir = tmp_path / "真题" / "吉林-数学"
            atom_dir.mkdir(parents=True)
            subject_dir = tmp_path / "数学"
            subject_dir.mkdir()
            (subject_dir / "265-函数.md").write_text(
                "---\ntitle: 函数\naliases: [函数]\n学科: 数学\n学段: 高中\n主题: 必修一\n状态: 完成\n英文术语: function\n---\n\n# 函数\n",
                encoding="utf-8",
            )
            _write_atom(atom_dir, "2024-新课标Ⅱ-08.md", 2024, 8, "选择", ["函数"])
            _write_atom(atom_dir, "2023-新课标Ⅱ-11.md", 2023, 11, "选择", ["函数"], gaps=["微分方程"])

            indices_dir = tmp_path / "索引" / "真题"
            indices_dir.mkdir(parents=True)

            aggregate(
                province="吉林", subject="数学",
                atom_root=tmp_path / "真题",
                indices_root=indices_dir,
                subject_root=tmp_path,
                tag_pool=lambda t, seq: True,
                seq_lookup=lambda t: 265,
            )

            self.assertTrue((indices_dir / "吉林数学-高频考点.md").exists())
            self.assertTrue((indices_dir / "吉林数学-题型×考点交叉表.md").exists())
            self.assertTrue((indices_dir / "吉林数学-缺口词条清单.md").exists())
            self.assertTrue((indices_dir / "吉林数学-试卷地图.md").exists())

            text = (subject_dir / "265-函数.md").read_text(encoding="utf-8")
            self.assertIn("<!-- exam-backlinks-start -->", text)
            self.assertIn("[[2024-新课标Ⅱ-08]]", text)
            self.assertIn("[[2023-新课标Ⅱ-11]]", text)

            gap_text = (indices_dir / "吉林数学-缺口词条清单.md").read_text(encoding="utf-8")
            self.assertIn("微分方程", gap_text)

    def test_backlink_idempotent(self):
        """连续跑两次反链应保持不变（幂等）。"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            atom_dir = tmp_path / "真题" / "吉林-数学"
            atom_dir.mkdir(parents=True)
            subject_dir = tmp_path / "数学"
            subject_dir.mkdir()
            (subject_dir / "265-函数.md").write_text(
                "---\ntitle: 函数\naliases: [函数]\n---\n\n# 函数\n",
                encoding="utf-8",
            )
            _write_atom(atom_dir, "2024-新课标Ⅱ-08.md", 2024, 8, "选择", ["函数"])

            indices_dir = tmp_path / "索引" / "真题"
            indices_dir.mkdir(parents=True)

            kwargs = dict(
                province="吉林", subject="数学",
                atom_root=tmp_path / "真题",
                indices_root=indices_dir,
                subject_root=tmp_path,
                tag_pool=lambda t, seq: True,
                seq_lookup=lambda t: 265,
            )
            aggregate(**kwargs)
            after_first = (subject_dir / "265-函数.md").read_text(encoding="utf-8")
            aggregate(**kwargs)
            after_second = (subject_dir / "265-函数.md").read_text(encoding="utf-8")
            self.assertEqual(after_first, after_second)


if __name__ == "__main__":
    unittest.main()
