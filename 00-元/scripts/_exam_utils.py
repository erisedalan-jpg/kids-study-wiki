"""真题流水线共享工具。

提供：
- load_config(): 读 exam_pipeline_config.yaml
- normalize_paper(): PDF 文件名 → 卷别短简称
- normalize_gender(): PDF 文件名 → 文/理/不分
- build_atom_filename(): 真题词条文件名（如 2022-文-01.md）
- build_screenshot_filename(): 截图文件名（含 .q.png / .a.png 后缀）
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT  # noqa: E402

CONFIG_PATH = REPO_ROOT / "00-元" / "scripts" / "exam_pipeline_config.yaml"


def load_config() -> dict[str, Any]:
    """读 exam_pipeline_config.yaml 并返回 dict。"""
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def normalize_paper(pdf_filename: str, cfg: dict[str, Any]) -> str:
    """PDF 文件名 → 卷别短简称。长 key 优先匹配。"""
    for pattern, simple in cfg["paper_aliases"]:
        if pattern in pdf_filename:
            return simple
    return "未知"


def normalize_gender(pdf_filename: str, cfg: dict[str, Any]) -> str:
    """PDF 文件名 → 文/理/不分。"""
    for pattern, gender in cfg["gender_aliases"]:
        if pattern in pdf_filename:
            return gender
    return "不分"


def build_atom_filename(year: int, gender: str, paper: str, qno: int) -> str:
    """真题词条文件名（无扩展前缀，跨年同名靠年份避免）。"""
    nn = f"{qno:02d}"
    if gender in ("文", "理"):
        return f"{year}-{gender}-{nn}.md"
    return f"{year}-{paper}-{nn}.md"


def build_screenshot_filename(year: int, gender: str, paper: str, qno: int, kind: str) -> str:
    """截图文件名 <year>-<gender|paper>-<qno>.<kind>.png

    kind: "q"(题面) 或 "a"(答案/解析)
    """
    if kind not in ("q", "a"):
        raise ValueError(f"kind 必须是 'q' 或 'a'，收到 {kind!r}")
    nn = f"{qno:02d}"
    prefix = gender if gender in ("文", "理") else paper
    return f"{year}-{prefix}-{nn}.{kind}.png"
