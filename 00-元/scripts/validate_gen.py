# -*- coding: utf-8 -*-
"""生成体检门：gen_atom_skeleton 批量生成后**立即**跑、过不了不准进后处理（renumber 等）。

在源头拦下 v4-pro 批量生成的已知故障类（皆为实战踩过的坑）：
  1. 代码围栏包裹      —— 文件以 ``` 开头，frontmatter 失效
  2. 提示模板吐出      —— 正文混入提示词原文（签名见 TEMPLATE_SIGNATURES）
  3. frontmatter 缺字段 —— 学段/学期/主题 缺失或无法解析
  4. 学期带括号        —— 写成 `[选必一]` 而非裸值 `选必一`
  5. 跨学段裸名碰撞     —— 高中 topic 撞已有初中条目（概念应单条跨学段）

用法
----
    # renumber 前先跑；exit 1 表示有硬错误，须先修
    python 00-元/scripts/validate_gen.py 历史 政治 地理
    python 00-元/scripts/validate_gen.py --dir 历史

退出码
------
    0  无硬错误（warn 不阻断）
    1  有硬错误（需修复后再进后处理）
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, bare_name, read_frontmatter, setup_utf8  # noqa: E402

# 正文中出现即判定为"提示模板吐出"的签名（实战见过的回吐片段）
TEMPLATE_SIGNATURES = [
    "接下来按学段选用正文层数",
    "之后固定追加以下区块",
    "[[bare-name]]",
    "给 3-6 岁（共读版）",   # 初中/高中条目不应出现 3-6 岁层
    "<学段>",
    "<bare-name>",
    "<一句话定义",
]

CODE_FENCE = "`" * 3


def check_entry(p: Path) -> list[str]:
    """返回该条目的硬错误列表（空 = 通过）。"""
    errs: list[str] = []
    text = p.read_text(encoding="utf-8")

    # 1. 代码围栏包裹
    if text.lstrip().startswith(CODE_FENCE):
        errs.append("代码围栏包裹（``` 开头）")

    # 2. 提示模板吐出
    hits = [s for s in TEMPLATE_SIGNATURES if s in text]
    if hits:
        errs.append(f"提示模板吐出：{hits}")

    # 3. frontmatter 缺字段
    fm = read_frontmatter(p)
    for k in ("学段", "学期", "主题"):
        if not str(fm.get(k, "")).strip():
            errs.append(f"frontmatter 缺/未解析：{k}")

    # 4. 学期带括号（应为裸值）
    xq = str(fm.get("学期", "")).strip()
    if xq.startswith("[") or xq.endswith("]"):
        errs.append(f"学期带括号（应裸值）：{xq!r}")

    return errs


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("subjects", nargs="*", help="学科目录名，如 历史 政治 地理")
    ap.add_argument("--dir", help="单个学科目录（与位置参数二选一）")
    args = ap.parse_args()

    subjects = list(args.subjects)
    if args.dir:
        subjects.append(args.dir)
    if not subjects:
        sys.exit("ERROR: 至少指定一个学科目录")

    hard = 0
    for sub in subjects:
        sub_dir = REPO_ROOT / sub
        if not sub_dir.is_dir():
            print(f"⚠️  目录不存在: {sub_dir}")
            continue

        files = sorted(sub_dir.glob("*.md"))

        # 逐条硬错误
        for p in files:
            errs = check_entry(p)
            if errs:
                hard += len(errs)
                print(f"✗ {sub}/{p.name}")
                for e in errs:
                    print(f"    - {e}")

        # 5. 跨学段裸名碰撞（同目录裸名重复）
        by_bare: dict[str, list[str]] = defaultdict(list)
        for p in files:
            by_bare[bare_name(p)].append(p.name)
        for bare, names in by_bare.items():
            if len(names) > 1:
                hard += 1
                print(f"✗ {sub} 裸名碰撞「{bare}」: {names}")

    print()
    if hard:
        print(f"❌ 生成体检：{hard} 处硬错误 —— 修复后再进后处理（renumber 等）")
        return 1
    print("✅ 生成体检：全部通过，可进后处理")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
