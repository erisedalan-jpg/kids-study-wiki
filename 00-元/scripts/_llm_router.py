"""
统一 LLM 调用路由（DeepSeek）

家庭学习 Wiki 多模型异构工作流的核心入口。所有需要调 LLM 的脚本
（gen_atom_skeleton / clean_exam_text / review_dispatch 的 deepseek-self 等）
都走这里，统一处理：
- 模型路由（按任务难度选 model）
- 重试与超时
- 调用日志（JSONL 落盘到 _llm_logs/，便于事后核算 token/成本）
- 失败降级（DeepSeek 异常 → 抛 LLMError，由上层决定是否走人工兜底）

⚠️ opus/sonnet 复检由 review_dispatch.py 写 prompt 队列、Claude Code
主会话人工跑，本路由只负责 DeepSeek 调用。
⚠️ 模型 ID 由用户在 MODEL_REGISTRY 中配置。DeepSeek 官方 API 的 model
字段命名以 https://api.deepseek.com 文档为准。
⚠️ deepseek-reasoner 即将弃用，其工作（推理 / 自检）已并入 v4-pro。

用法
----
    from _llm_router import call, LLMError, Task

    result = call(
        prompt="生成词条骨架：函数",
        task=Task.SIMPLE,          # SIMPLE → flash, COMPLEX → pro
        system="你是家庭学习 Wiki 的助手 ...",
        temperature=0.3,
        max_tokens=4000,
    )
    print(result.text, result.model, result.usage)

环境变量
--------
    DEEPSEEK_API_KEY     必填，DeepSeek 官方 API key
    LLM_LOG_DIR          可选，默认 00-元/scripts/_llm_logs/

退出码 / 异常
-------------
    raise LLMError       网络/4xx/5xx/超时，调用方决定是否降级或重试
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv  # type: ignore[import-not-found]

    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

try:
    import httpx  # type: ignore[import-not-found]
except ImportError as e:
    raise SystemExit(
        "缺少 httpx 依赖。请先：pip install -r 00-元/scripts/requirements-llm.txt"
    ) from e


# ---------------------------------------------------------------------------
# 模型注册表
# ---------------------------------------------------------------------------

class Task(str, Enum):
    """任务难度等级，决定默认走哪个 model。"""

    SIMPLE = "simple"       # 短文本清洗、单字段抽取、分类打标
    COMPLEX = "complex"     # 词条骨架生成、长上下文改写、多步推理 / 自检（吃掉原 reasoner 的活）


@dataclass(frozen=True)
class ModelSpec:
    provider: str        # "deepseek"
    model: str           # API 端实际 model 字段
    endpoint: str        # 完整 endpoint URL


# ⚠️ 模型 ID 由用户指定。运行前请校验 DeepSeek 官方文档对应字段名。
MODEL_REGISTRY: dict[Task, ModelSpec] = {
    Task.SIMPLE: ModelSpec(
        provider="deepseek",
        model="deepseek-v4-flash",
        endpoint="https://api.deepseek.com/chat/completions",
    ),
    Task.COMPLEX: ModelSpec(
        provider="deepseek",
        model="deepseek-v4-pro",
        endpoint="https://api.deepseek.com/chat/completions",
    ),
}


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

class LLMError(RuntimeError):
    """LLM 调用失败的统一异常。上层据此判断是否降级/重试。"""


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResult:
    text: str
    model: str
    provider: str
    usage: Usage = field(default_factory=Usage)
    latency_ms: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def call(
    prompt: str,
    *,
    task: Task = Task.COMPLEX,
    system: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 4000,
    timeout: float = 120.0,
    max_retries: int = 2,
    extra: dict[str, Any] | None = None,
) -> LLMResult:
    """同步调用 LLM。失败时按 max_retries 指数退避，最终仍失败抛 LLMError。"""
    spec = MODEL_REGISTRY[task]

    if spec.provider != "deepseek":
        raise LLMError(f"未知 provider: {spec.provider}")

    result = _call_deepseek(
        spec, prompt, system, temperature, max_tokens, timeout, max_retries, extra
    )

    _log_call(task=task, spec=spec, prompt=prompt, result=result)
    return result


# ---------------------------------------------------------------------------
# Provider 实现
# ---------------------------------------------------------------------------

def _call_deepseek(
    spec: ModelSpec,
    prompt: str,
    system: str | None,
    temperature: float,
    max_tokens: int,
    timeout: float,
    max_retries: int,
    extra: dict[str, Any] | None,
) -> LLMResult:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise LLMError("环境变量 DEEPSEEK_API_KEY 未设置")

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload: dict[str, Any] = {
        "model": spec.model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if extra:
        payload.update(extra)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    return _post_with_retry(
        endpoint=spec.endpoint,
        headers=headers,
        payload=payload,
        timeout=timeout,
        max_retries=max_retries,
        parse=_parse_openai_like,
        spec=spec,
    )


def _post_with_retry(
    *,
    endpoint: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: float,
    max_retries: int,
    parse,
    spec: ModelSpec,
) -> LLMResult:
    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        t0 = time.monotonic()
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(endpoint, headers=headers, json=payload)
            latency_ms = int((time.monotonic() - t0) * 1000)
            if resp.status_code >= 400:
                # 4xx 不重试（key 错/参数错）；5xx 与超时才退避
                if 400 <= resp.status_code < 500 and resp.status_code != 429:
                    raise LLMError(f"{spec.model} {resp.status_code}: {resp.text[:300]}")
                raise httpx.HTTPStatusError(
                    f"{resp.status_code}", request=resp.request, response=resp
                )
            data = resp.json()
            return parse(data, spec=spec, latency_ms=latency_ms)
        except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.HTTPError) as e:
            last_err = e
            if attempt >= max_retries:
                break
            time.sleep(2 ** attempt)
    raise LLMError(f"{spec.model} 调用失败（{max_retries + 1} 次后）: {last_err}")


def _parse_openai_like(data: dict[str, Any], *, spec: ModelSpec, latency_ms: int) -> LLMResult:
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise LLMError(f"DeepSeek 返回格式异常: {data}") from e
    usage_raw = data.get("usage", {})
    return LLMResult(
        text=text,
        model=spec.model,
        provider=spec.provider,
        usage=Usage(
            prompt_tokens=usage_raw.get("prompt_tokens", 0),
            completion_tokens=usage_raw.get("completion_tokens", 0),
            total_tokens=usage_raw.get("total_tokens", 0),
        ),
        latency_ms=latency_ms,
        raw=data,
    )


# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------

def _log_call(*, task: Task, spec: ModelSpec, prompt: str, result: LLMResult) -> None:
    log_dir = Path(os.environ.get("LLM_LOG_DIR") or Path(__file__).parent / "_llm_logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"
    entry = {
        "id": uuid.uuid4().hex[:12],
        "ts": datetime.now(timezone.utc).isoformat(),
        "task": task.value,
        "provider": spec.provider,
        "model": spec.model,
        "prompt_preview": prompt[:200],
        "output_preview": result.text[:200],
        "usage": result.usage.__dict__,
        "latency_ms": result.latency_ms,
    }
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
