"""测试 _llm_router.py 的注册表、参数解析、错误处理（不打真实网络）。"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _llm_router import (  # noqa: E402
    MODEL_REGISTRY,
    LLMError,
    LLMResult,
    Task,
    Usage,
    _parse_openai_like,
    call,
)


class TestRegistry(unittest.TestCase):
    def test_all_tasks_have_spec(self):
        for t in Task:
            self.assertIn(t, MODEL_REGISTRY, f"Task {t} 未注册 ModelSpec")

    def test_provider_is_deepseek(self):
        for spec in MODEL_REGISTRY.values():
            self.assertEqual(spec.provider, "deepseek")

    def test_endpoint_starts_with_https(self):
        for spec in MODEL_REGISTRY.values():
            self.assertTrue(spec.endpoint.startswith("https://"))


class TestParsers(unittest.TestCase):
    def test_parse_openai_like_extracts_text_and_usage(self):
        data = {
            "choices": [{"message": {"content": "你好"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        spec = MODEL_REGISTRY[Task.SIMPLE]
        r = _parse_openai_like(data, spec=spec, latency_ms=100)
        self.assertEqual(r.text, "你好")
        self.assertEqual(r.usage.total_tokens, 15)
        self.assertEqual(r.provider, "deepseek")

    def test_parse_openai_like_malformed_raises(self):
        spec = MODEL_REGISTRY[Task.SIMPLE]
        with self.assertRaises(LLMError):
            _parse_openai_like({"unexpected": True}, spec=spec, latency_ms=0)


class TestCallMissingKey(unittest.TestCase):
    def test_deepseek_without_key_raises_llm_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(LLMError) as ctx:
                call("test", task=Task.SIMPLE, max_retries=0)
            self.assertIn("DEEPSEEK_API_KEY", str(ctx.exception))


class TestCallHappyPath(unittest.TestCase):
    def test_deepseek_happy_path_with_mocked_httpx(self):
        # 模拟 httpx.Client.__enter__().post() 返回合法 200
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        fake_client = MagicMock()
        fake_client.__enter__.return_value.post.return_value = fake_resp

        with tempfile.TemporaryDirectory() as tmp:
            env = {"DEEPSEEK_API_KEY": "sk-test", "LLM_LOG_DIR": tmp}
            with patch.dict(os.environ, env, clear=True):
                with patch("_llm_router.httpx.Client", return_value=fake_client):
                    r = call("test", task=Task.SIMPLE, max_retries=0)

            self.assertEqual(r.text, "ok")
            self.assertEqual(r.usage.total_tokens, 2)

            # 校验日志落盘
            log_files = list(Path(tmp).glob("*.jsonl"))
            self.assertEqual(len(log_files), 1)
            entry = json.loads(log_files[0].read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(entry["provider"], "deepseek")
            self.assertEqual(entry["task"], "simple")


if __name__ == "__main__":
    unittest.main()
