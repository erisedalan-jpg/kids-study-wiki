"""
共享工具与常量（家庭学习 Wiki 脚本基础设施）

所有 00-元/scripts/ 下脚本 import 此模块统一行为：
- setup_utf8(): 修复 PowerShell GBK 乱码
- XUEQI_ORDER: 学期排序键（学前→高中选必三）
- SUBJECT_DIRS: 学科目录清单（顶级文件夹名）
- iter_entries(): 遍历某学科目录的所有词条
- read_frontmatter(): 解析词条 frontmatter
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path
from typing import Iterator


def setup_utf8() -> None:
    """让 stdout/stderr 用 UTF-8，避免 Windows GBK 乱码。"""
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# 仓库根（scripts/ → 00-元/ → 仓库根）
REPO_ROOT = Path(__file__).resolve().parents[2]


# 学期 → 排序键。数字越小越靠前。
# 跨学段全局编号：学前=0；小学一上=1...六下=12；初中七上=13...九下=18；
# 高中按学科分两路：语文必修上=20；其它学科必一=21（同一槽位互斥不冲突）。
XUEQI_ORDER: dict[str, int] = {
    # 学前
    "学前": 0,
    # 小学
    "一上": 1, "一下": 2,
    "二上": 3, "二下": 4,
    "三上": 5, "三下": 6,
    "四上": 7, "四下": 8,
    "五上": 9, "五下": 10,
    "六上": 11, "六下": 12,
    # 初中
    "七上": 13, "七下": 14,
    "八上": 15, "八下": 16,
    "九上": 17, "九下": 18,
    "九年级全一": 18,  # 物理九年级合订本与九下同槽位
    # 高中——语文 / 英语 用"必修上下 + 选必上中下"
    "必修上": 20, "必修下": 21,
    "选必上": 22, "选必中": 23, "选必下": 24,
    # 高中——数理化生 用"必一/二/三 + 选必一/二/三/四"
    "必修一": 20, "必修二": 21, "必修三": 22,
    "必一": 20, "必二": 21, "必三": 22,
    "选必一": 30, "选必二": 31, "选必三": 32, "选必四": 33,
    "选择性必修一": 30, "选择性必修二": 31,
    "选择性必修三": 32, "选择性必修四": 33,
}


# 学科目录（顶级文件夹）— 仓库根直接下属的学科文件夹
SUBJECT_DIRS: list[str] = [
    "数学", "语文", "英语",
    "物理", "化学", "生物",
    "政治", "地理", "历史",
    "道德与法治", "科学",
    "美术", "艺术", "音乐", "书法", "体育",
    "生活与社会",
]


# frontmatter 边界
_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
# 文件名前缀（2-4 位数字 + 短横线）
PREFIX_RE = re.compile(r"^(\d{2,4})-")


def iter_entries(subject_dir: Path) -> Iterator[Path]:
    """遍历学科目录下所有 .md 词条（跳过 README/index）。"""
    for p in sorted(subject_dir.glob("*.md")):
        if p.name.lower() in {"readme.md", "index.md"}:
            continue
        yield p


def read_frontmatter(path: Path) -> dict[str, str]:
    """解析词条 frontmatter，返回简单 str→str 字典（多行/数组值保留原文）。"""
    text = path.read_text(encoding="utf-8", errors="replace")
    m = _FM_RE.match(text)
    if not m:
        return {}
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip()
        v = v.strip()
        if k:
            fm[k] = v
    return fm


def strip_prefix(name: str) -> str:
    """去掉数字前缀，返回 bare-name（含 .md）。"""
    return PREFIX_RE.sub("", name)


def bare_name(path: Path) -> str:
    """去掉前缀和扩展名，返回纯概念名。"""
    return strip_prefix(path.name).removesuffix(".md")


def xueqi_key(*values: str) -> int:
    """扫描所有传入字符串中的已知学期键，返回最小排序值（长 key 优先匹配）。

    用法：xueqi_key(fm.get("学段"), fm.get("学期"), fm.get("主题"))

    设计原因：化学/生物等学科 frontmatter `学段` 写 `[高中]`，细分学期
    （必修一/选必三）写在 `主题` 字段里。需要扫描多个字段才能正确排序。

    长 key 优先避免 "选必一" 被子串 "必一" 抢匹配。
    """
    s = " ".join(v for v in values if v)
    if not s:
        return 999
    for k in sorted(XUEQI_ORDER, key=len, reverse=True):
        if k in s:
            return XUEQI_ORDER[k]
    return 999
