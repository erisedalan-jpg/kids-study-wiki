"""测试 L2 复验队列 (prepare/ingest)。"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _utils import setup_utf8  # noqa: E402
from exam_verify import (  # noqa: E402
    parse_verdict_response,
    render_verify_prompt,
    run_prepare,
    run_ingest,
)


def setUpModule() -> None:
    """避免 Windows GBK 控制台在 print emoji 时崩溃。"""
    setup_utf8()


class TestRenderVerifyPrompt(unittest.TestCase):
    def test_prompt_contains_image_and_tags(self):
        q = {
            "qno": 1,
            "题面图": "素材/真题截图/吉林-数学/2022-文-01.q.png",
            "tags": ["集合的运算", "并集"],
            "summary": "考集合的交集运算。",
        }
        prompt = render_verify_prompt(q)
        self.assertIn("2022-文-01.q.png", prompt)
        self.assertIn("集合的运算", prompt)
        self.assertIn("并集", prompt)
        self.assertIn("吻合", prompt)  # 评判选项


class TestParseVerdictResponse(unittest.TestCase):
    def test_pass(self):
        r = parse_verdict_response("吻合\ntags 与题面一致")
        self.assertEqual(r["verdict"], "吻合")
        self.assertEqual(r["note"], "tags 与题面一致")

    def test_partial(self):
        r = parse_verdict_response("部分偏差\ntags 中 '并集' 应改为 '交集'")
        self.assertEqual(r["verdict"], "部分偏差")
        self.assertIn("交集", r["note"])

    def test_severe(self):
        r = parse_verdict_response("严重偏差\n该题考的是导数不是集合")
        self.assertEqual(r["verdict"], "严重偏差")

    def test_unknown(self):
        r = parse_verdict_response("不确定")
        self.assertEqual(r["verdict"], "未识别")

    def test_empty(self):
        r = parse_verdict_response("")
        self.assertEqual(r["verdict"], "调用失败")

    def test_severe_wins_over_partial_in_same_line(self):
        """Fix 1: priority order — 严重偏差 should win over 部分偏差 in ambiguous line."""
        r = parse_verdict_response("部分偏差，接近严重偏差\n备注")
        self.assertEqual(r["verdict"], "严重偏差")


def _make_question(qno: int, with_verdict: bool = False) -> dict:
    q = {
        "qno": qno,
        "题面图": f"素材/真题截图/test/2022-文-{qno:02d}.q.png",
        "tags": ["集合的运算"],
        "summary": f"测试题 {qno}",
    }
    if with_verdict:
        q["verdict"] = "吻合"
        q["verdict_note"] = "已 ingest"
    return q


class TestRunPrepare(unittest.TestCase):
    def test_skip_already_verdicted(self):
        """Fix 5 (prepare side): 已 verdict 的题不再生成 prompt。"""
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            qa_path = td_path / "questions.json"
            qa = {
                "paper_id": "test-paper",
                "questions": [
                    _make_question(1, with_verdict=True),
                    _make_question(2, with_verdict=False),
                ],
            }
            qa_path.write_text(
                json.dumps(qa, ensure_ascii=False), encoding="utf-8"
            )
            run_prepare(qa_path)
            queue_dir = td_path / "verdicts" / "test-paper"
            self.assertFalse((queue_dir / "q01.prompt.md").exists())
            self.assertTrue((queue_dir / "q02.prompt.md").exists())

    def test_rerun_truncates_pending_log(self):
        """Fix 2: _pending.jsonl 应在每次 prepare 时重写而非追加。"""
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            qa_path = td_path / "questions.json"
            qa = {
                "paper_id": "test-paper",
                "questions": [
                    _make_question(1, with_verdict=False),
                    _make_question(2, with_verdict=False),
                ],
            }
            qa_path.write_text(
                json.dumps(qa, ensure_ascii=False), encoding="utf-8"
            )
            run_prepare(qa_path)
            run_prepare(qa_path)
            pending_log = td_path / "verdicts" / "test-paper" / "_pending.jsonl"
            lines = [
                ln for ln in pending_log.read_text(encoding="utf-8").splitlines()
                if ln.strip()
            ]
            self.assertEqual(len(lines), 2)


class TestRunIngest(unittest.TestCase):
    def test_missing_verdict_file_skipped_and_returns_1(self):
        """Fix 4 indirect: 无 verdict 文件时不写入 verdict 且返回 1。"""
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            qa_path = td_path / "questions.json"
            qa = {
                "paper_id": "test-paper",
                "questions": [
                    _make_question(1, with_verdict=False),
                    _make_question(2, with_verdict=False),
                ],
            }
            qa_path.write_text(
                json.dumps(qa, ensure_ascii=False), encoding="utf-8"
            )
            queue_dir = td_path / "verdicts" / "test-paper"
            queue_dir.mkdir(parents=True, exist_ok=True)
            rc = run_ingest(qa_path)
            self.assertEqual(rc, 1)
            after = json.loads(qa_path.read_text(encoding="utf-8"))
            for q in after["questions"]:
                self.assertNotIn("verdict", q)

    def test_severe_counter_and_return_code(self):
        """严重偏差 ingest 后写入正确，返回码非 0。"""
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            qa_path = td_path / "questions.json"
            qa = {
                "paper_id": "test-paper",
                "questions": [_make_question(1, with_verdict=False)],
            }
            qa_path.write_text(
                json.dumps(qa, ensure_ascii=False), encoding="utf-8"
            )
            queue_dir = td_path / "verdicts" / "test-paper"
            queue_dir.mkdir(parents=True, exist_ok=True)
            (queue_dir / "q01.verdict.txt").write_text(
                "严重偏差\n该题考的是导数不是集合", encoding="utf-8"
            )
            rc = run_ingest(qa_path)
            self.assertEqual(rc, 1)
            after = json.loads(qa_path.read_text(encoding="utf-8"))
            self.assertEqual(after["questions"][0]["verdict"], "严重偏差")


if __name__ == "__main__":
    unittest.main()
