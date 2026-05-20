"""真题刷题 → 学科词条 mastery/wrong_count 反写（占位实现）。

【当前】noop：仅校验字段就绪，不写任何数据。

【未来接管】当学生开始填真题 frontmatter 的 `我的状态` 后：
  1. 扫所有 真题/吉林-{科}/*.md → 取 我的状态 / 错次 / 最后做 / 考点 list
  2. 对每个考点 tag → alias-aware 解析到学科词条 stem
     （复用 fix_wikilinks.collect_targets()）
  3. 反写学科词条：
     - wrong_count += 该题错次
     - last_review = max(已有, 该题最后做)
     - review_count += 1（若 已做对/已做错/反复错）
     - mastery 降级规则：
         反复错 → 困难
         已做错 → 初学（若现 ≥ 会做）
         已做对 → 会做（若现 = 未学/初学）
  4. 写回学科词条 frontmatter

【SRS 调度（同样占位）】今日复习 = 学科词条 mastery × last_review：
  - 未学 / 初学 / 困难 → 今日
  - 会做  → last + 3 天
  - 熟练  → last + 7 天
  - 精通  → last + 30 天

CLI：
  python 00-元/scripts/mock_review.py --check       # 校验字段就绪（默认）
  python 00-元/scripts/mock_review.py --apply       # 未来：真写
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import (  # noqa: E402
    REPO_ROOT, SUBJECT_DIRS, iter_entries, iter_exam_dirs,
    read_frontmatter, setup_utf8,
)


def check_fields_ready() -> tuple[int, int]:
    """校验真题 / 学科词条 是否有必要字段。返回 (真题缺字段数, 学科缺字段数)。"""
    exam_missing = atom_missing = 0
    exam_required = {"我的状态", "错次"}
    atom_required = {"mastery", "wrong_count"}

    for sub in iter_exam_dirs():
        for p in sub.glob("*.md"):
            fm = read_frontmatter(p)
            if not fm or not exam_required.issubset(fm.keys()):
                exam_missing += 1

    for s in SUBJECT_DIRS:
        sd = REPO_ROOT / s
        if not sd.is_dir():
            continue
        for p in iter_entries(sd):
            fm = read_frontmatter(p)
            if not fm or not atom_required.issubset(fm.keys()):
                atom_missing += 1

    return exam_missing, atom_missing


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", default=True,
                    help="校验字段就绪（默认）")
    ap.add_argument("--apply", action="store_true",
                    help="未来：真写 mastery / wrong_count（当前 noop）")
    args = ap.parse_args()

    print("[mock_review] 占位脚本，未来接管真题→词条反写", flush=True)
    em, am = check_fields_ready()
    print(f"  真题缺必要字段：{em}（若 > 0 跑 init_review_fields.py --apply）")
    print(f"  词条缺必要字段：{am}（同上）")
    if args.apply:
        print("  [APPLY] 未来此处实现真写逻辑；当前 noop，无变更。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
