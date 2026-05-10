"""真题流水线共享工具。

复用 _utils.py 的 setup_utf8 / REPO_ROOT。
本模块新增：
- load_config(): 读 exam_pipeline_config.yaml
- normalize_paper(): PDF 文件名 → 卷别短简称
- normalize_gender(): PDF 文件名 → 文/理/不分
- build_atom_filename(): 真题词条文件名构造
- is_in_tag_pool(): 判断 tag 是否进入高频统计池
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
    """PDF 文件名 → 卷别短简称。

    paper_aliases 列表已按长度从长到短排序（yaml 里维护），
    保证 "新课标Ⅱ卷" 命中 "新课标Ⅱ" 而非 "新课标"。
    """
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
    """真题词条文件名。

    - 2008-2022 文/理分卷：YYYY-<文|理>-NN.md
    - 2023+ 不分文理：YYYY-<卷别>-NN.md
    """
    nn = f"{qno:02d}"
    if gender in ("文", "理"):
        return f"{year}-{gender}-{nn}.md"
    return f"{year}-{paper}-{nn}.md"


def is_in_tag_pool(tag: str, entry_seq: int, subject: str, cfg: dict[str, Any]) -> bool:
    """tag 是否参与"高频考点"统计。

    - 在高中序号范围内 → True
    - 在"额外纳入"白名单 → True
    - 否则 False（不影响反链，仅影响高频榜单）
    """
    flt = cfg.get("tag_pool_filters", {}).get(subject)
    if not flt:
        return True  # 没配置过滤就全部纳入
    lo, hi = flt["序号范围"]
    if lo <= entry_seq <= hi:
        return True
    if tag in flt.get("额外纳入", []):
        return True
    return False
