"""测试索引聚合 + 反链回填。"""
import sys
import unittest
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exam_index import (  # noqa: E402
    BACKLINK_START,
    BACKLINK_END,
    build_freq_table,
    build_gap_list,
    backfill_backlinks,
    parse_atom_fm,
)


class TestFreqTable(unittest.TestCase):
    def test_count_tags(self):
        atoms = [
            {"考点": ["集合的运算", "并集"], "题号": 1, "卷别": "全国乙", "文理": "文"},
            {"考点": ["集合的运算", "交集"], "题号": 2, "卷别": "全国乙", "文理": "文"},
            {"考点": ["函数最值"], "题号": 5, "卷别": "全国乙", "文理": "文"},
        ]
        freq = build_freq_table(atoms)
        self.assertEqual(freq["集合的运算"], 2)
        self.assertEqual(freq["并集"], 1)
        self.assertEqual(freq["函数最值"], 1)


class TestGapList(unittest.TestCase):
    def test_gap_detection(self):
        atoms = [
            {"考点": ["集合的运算", "未知概念"], "题号": 1, "卷别": "全国乙", "文理": "文"},
        ]
        existing = {"集合的运算"}  # lexicon
        gaps = build_gap_list(atoms, existing)
        self.assertIn("未知概念", gaps)
        self.assertNotIn("集合的运算", gaps)


class TestBacklinkMarkers(unittest.TestCase):
    def test_markers_defined(self):
        self.assertEqual(BACKLINK_START, "<!-- exam-backlinks-start -->")
        self.assertEqual(BACKLINK_END, "<!-- exam-backlinks-end -->")


class TestParseAtomFm(unittest.TestCase):
    def test_list_field_parsed(self):
        text = "---\ntitle: foo\n考点: [集合的运算, 并集]\n---\n\nbody"
        fm = parse_atom_fm(text)
        self.assertEqual(fm["考点"], ["集合的运算", "并集"])
        self.assertEqual(fm["title"], "foo")

    def test_no_frontmatter_returns_empty(self):
        self.assertEqual(parse_atom_fm("no fm here"), {})


class TestBackfillBacklinks(unittest.TestCase):
    """跑真实文件系统：在 tmp 工作目录里建一个学科目录 + 真题词条。"""

    def _make_repo(self, tmp_path: Path):
        # 这些测试只能改 _path 字段触发；为简单起见，monkey-patch REPO_ROOT
        import exam_index
        self._orig_root = exam_index.REPO_ROOT
        exam_index.REPO_ROOT = tmp_path
        # 重要：_utils.REPO_ROOT 也得 monkey-patch，因为 iter_entries 内部用它
        import _utils
        self._orig_utils_root = _utils.REPO_ROOT
        _utils.REPO_ROOT = tmp_path

    def _restore(self):
        import exam_index, _utils
        exam_index.REPO_ROOT = self._orig_root
        _utils.REPO_ROOT = self._orig_utils_root

    def test_first_append_then_idempotent_rewrite(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            self._make_repo(tmp)
            try:
                (tmp / "数学").mkdir()
                target = tmp / "数学" / "016-集合的运算.md"
                target.write_text("---\ntitle: 集合的运算\n---\n\n正文。\n", encoding="utf-8")
                atoms = [
                    {"考点": ["集合的运算"], "_bare": "2022-文-01"},
                    {"考点": ["集合的运算"], "_bare": "2022-文-02"},
                ]
                # 首次回填
                paths1 = backfill_backlinks(atoms, "数学")
                self.assertEqual(len(paths1), 1)
                t1 = target.read_text(encoding="utf-8")
                self.assertIn(BACKLINK_START, t1)
                self.assertIn(BACKLINK_END, t1)
                self.assertIn("[[2022-文-01]]", t1)
                self.assertIn("[[2022-文-02]]", t1)
                # 同样 atoms 再跑一次，文件应字节不变（updated 列表为空）
                paths2 = backfill_backlinks(atoms, "数学")
                self.assertEqual(paths2, [], "second run should be no-op")
                t2 = target.read_text(encoding="utf-8")
                self.assertEqual(t1, t2)
            finally:
                self._restore()

    def test_replace_existing_section(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            self._make_repo(tmp)
            try:
                (tmp / "数学").mkdir()
                target = tmp / "数学" / "016-集合的运算.md"
                target.write_text("---\ntitle: 集合的运算\n---\n\n正文。\n", encoding="utf-8")
                # 首次：1 题
                backfill_backlinks([{"考点": ["集合的运算"], "_bare": "2022-文-01"}], "数学")
                # 再跑：2 题
                backfill_backlinks(
                    [
                        {"考点": ["集合的运算"], "_bare": "2022-文-01"},
                        {"考点": ["集合的运算"], "_bare": "2022-文-02"},
                    ],
                    "数学",
                )
                text = target.read_text(encoding="utf-8")
                self.assertIn("[[2022-文-02]]", text)
                # 标记只出现一次（不重复 section）
                self.assertEqual(text.count(BACKLINK_START), 1)
                self.assertEqual(text.count(BACKLINK_END), 1)
            finally:
                self._restore()

    def test_missing_subject_dir_returns_zero(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            self._make_repo(tmp)
            try:
                atoms = [{"考点": ["集合的运算"], "_bare": "2022-文-01"}]
                paths = backfill_backlinks(atoms, "数学")  # 学科目录不存在
                self.assertEqual(paths, [])
            finally:
                self._restore()


if __name__ == "__main__":
    unittest.main()
