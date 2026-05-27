import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestAggregate(unittest.TestCase):
    def setUp(self):
        import kaodian_aggregate as k
        self.k = k

    def test_build_kaodian_map_groups_and_sorts(self):
        atoms = [
            {"_bare": "2024-A-01", "考点": ["复数", "模长"], "年份": "2024",
             "难度": "易", "题型": "选择", "题号": "1", "摘要": "求模"},
            {"_bare": "2010-A-02", "考点": ["复数"], "年份": "2010",
             "难度": "中", "题型": "选择", "题号": "2", "摘要": "复数运算"},
        ]
        group = {"复数": "复数", "模长": "复数"}
        m = self.k.build_kaodian_map(atoms, group)
        self.assertEqual(m["复数"]["父主题"], "复数")
        self.assertEqual(m["复数"]["真题数"], 2)
        # 代表题近年优先：2024 排前
        self.assertEqual(m["复数"]["真题"][0]["_bare"], "2024-A-01")
        self.assertIn(("选择", 1), m["复数"]["题位"])

    def test_only_kaodian_with_atoms(self):
        m = self.k.build_kaodian_map([], {"复数": "复数"})
        self.assertEqual(m, {})


if __name__ == "__main__":
    unittest.main()
