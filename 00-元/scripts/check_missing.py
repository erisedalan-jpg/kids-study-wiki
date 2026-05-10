"""
通用 expected-vs-actual 词条 diff。

子代理批量写入后，常因 rate limit / content filter 漏掉部分词条。
此脚本对比"应有清单"和"实际存在文件"，输出缺失项，供主会话兜底。

用法
----
    # expected.txt 一行一个 bare-name（不带前缀、不带 .md）
    python 00-元/scripts/check_missing.py 生物 expected.txt

    # 也可直接传逗号分隔清单
    python 00-元/scripts/check_missing.py 生物 --names "光合作用,呼吸作用,蒸腾作用"

输出
----
    stdout: 缺失的 bare-name（一行一个），方便管道给下一个工具
    stderr: 摘要统计

退出码
------
    0  无缺失
    1  存在缺失
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, bare_name, iter_entries, setup_utf8  # noqa: E402


def existing(subject: str) -> set[str]:
    d = REPO_ROOT / subject
    if not d.is_dir():
        sys.exit(f"ERROR: 学科目录不存在: {d}")
    return {bare_name(p) for p in iter_entries(d)}


def load_expected(file: Path | None, names: str) -> list[str]:
    items: list[str] = []
    if file:
        for line in file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                items.append(line)
    if names:
        items.extend(s.strip() for s in names.split(",") if s.strip())
    return items


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("subject", help="学科目录名，如 生物")
    ap.add_argument("expected_file", nargs="?", type=Path, help="期望词条清单文件")
    ap.add_argument("--names", default="", help="逗号分隔候选清单（替代 file）")
    args = ap.parse_args()

    have = existing(args.subject)
    expected = load_expected(args.expected_file, args.names)
    if not expected:
        sys.exit("ERROR: 必须提供 expected_file 或 --names")

    expected_set = set(expected)
    missing = sorted(expected_set - have)
    extra = sorted(have - expected_set)

    print("\n".join(missing))
    print(
        f"[{args.subject}] expected={len(expected_set)} have={len(have)} "
        f"missing={len(missing)} extra={len(extra)}",
        file=sys.stderr,
    )
    if extra:
        print(f"  extra (in dir but not in expected): {extra[:10]}{'...' if len(extra) > 10 else ''}",
              file=sys.stderr)
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
