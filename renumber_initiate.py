"""
Renumber 数学/语文/英语 entries with 3-digit prefix per学期 first appearance.

Strategy:
  1. Files with existing N-digit prefix (小学) → keep original order.
  2. Files without prefix (初中) → sort by 学期 priority + topic group + alphabet.
  3. Concatenate, then assign 001, 002, ... 3-digit prefix.
  4. Add bare-name to aliases[0] (idempotent).
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\tjusu\Desktop\cc\family\kids\study")

XUEQI_ORDER = {
    "学前": 1,
    "一上": 2, "一下": 3, "二上": 4, "二下": 5,
    "三上": 6, "三下": 7, "四上": 8, "四下": 9,
    "五上": 10, "五下": 11, "六上": 12, "六下": 13,
    "七上": 14, "七下": 15, "八上": 16, "八下": 17,
    "九上": 18, "九年级全一": 18, "九下": 19,
}

LANG_GROUP = {
    "概念": 1, "文学常识": 1, "汉字": 1, "拼音": 1, "标点": 1, "笔画": 1,
    "古诗": 2, "古诗词": 2, "诗歌": 2,
    "课文": 3, "文言": 3, "文言文": 3,
    "名著": 4, "名著导读": 4,
    "文体": 5,
    "修辞": 6, "写作": 6,
}

ENG_GROUP = {
    "词汇": 1, "单词": 1, "短语": 1,
    "语法": 2, "时态": 2,
    "句型": 3, "句子": 3, "对话": 3,
}

MATH_GROUP = {}  # 数学 within学期 fallback to alphabetical


def parse_frontmatter_raw(path):
    text = path.read_text(encoding='utf-8', errors='replace')
    m = re.match(r'^---\r?\n(.*?)\r?\n---', text, re.S)
    return text, (m.group(1) if m else "")


def get_topics(fm_text):
    m = re.search(r'^主题:\s*\[(.*?)\]', fm_text, re.M)
    if not m:
        return []
    return [s.strip() for s in m.group(1).split(',') if s.strip()]


def get_xueduan(fm_text):
    m = re.search(r'^学段:\s*\[(.*?)\]', fm_text, re.M)
    if not m:
        return []
    return [s.strip() for s in m.group(1).split(',') if s.strip()]


def get_xueqi_priority(fm_text):
    topics = get_topics(fm_text)
    for t in topics:
        if t in XUEQI_ORDER:
            return XUEQI_ORDER[t]
    xd = get_xueduan(fm_text)
    if "学前" in xd:
        return 1
    if "小学" in xd:
        return 12
    if "初中" in xd:
        return 14
    return 99


def get_group_priority(fm_text, group_map):
    topics = get_topics(fm_text)
    for t in topics:
        if t in group_map:
            return group_map[t]
    return 99


def strip_prefix(stem):
    m = re.match(r'^(\d+)-(.+)$', stem)
    if m:
        return int(m.group(1)), m.group(2)
    return None, stem


def add_bare_alias(text, bare):
    m = re.match(r'^(---\r?\n)(.*?)(\r?\n---)', text, re.S)
    if not m:
        return text, False
    head = m.group(1)
    fm = m.group(2)
    foot = m.group(3)
    rest = text[m.end():]
    al_match = re.search(r'^aliases:\s*\[(.*?)\]', fm, re.M)
    if not al_match:
        return text, False
    items_str = al_match.group(1)
    items = [s.strip() for s in items_str.split(',')] if items_str.strip() else []
    items = [s for s in items if s and s != bare]
    new_items = [bare] + items
    new_aliases = f'aliases: [{", ".join(new_items)}]'
    new_fm = re.sub(r'^aliases:\s*\[.*?\]', new_aliases, fm, count=1, flags=re.M)
    if new_fm == fm:
        return text, False
    return head + new_fm + foot + rest, True


def plan_subject(subj_name, group_map):
    subj_dir = ROOT / subj_name
    files = sorted(subj_dir.glob('*.md'))
    items = []
    for f in files:
        text, fm = parse_frontmatter_raw(f)
        prefix_num, bare = strip_prefix(f.stem)
        if prefix_num is not None:
            sort_key = (0, prefix_num, bare)
        else:
            xq = get_xueqi_priority(fm)
            grp = get_group_priority(fm, group_map)
            sort_key = (1, xq, grp, bare)
        items.append((sort_key, f, bare))
    items.sort(key=lambda x: x[0])
    plan = []
    for i, (key, f, bare) in enumerate(items, 1):
        new_prefix = f'{i:03d}'
        new_name = f'{new_prefix}-{bare}.md'
        plan.append((f, subj_dir / new_name, bare))
    return plan


def apply_plan(plan, dry_run=False):
    rename_count = 0
    alias_count = 0
    for old, new, bare in plan:
        # 1) Add bare alias if missing
        text = old.read_text(encoding='utf-8', errors='replace')
        new_text, changed = add_bare_alias(text, bare)
        if changed and not dry_run:
            old.write_text(new_text, encoding='utf-8')
            alias_count += 1
        elif changed:
            alias_count += 1
        # 2) git mv if name differs
        if old != new:
            if dry_run:
                rename_count += 1
            else:
                old_rel = old.relative_to(ROOT).as_posix()
                new_rel = new.relative_to(ROOT).as_posix()
                r = subprocess.run(
                    ['git', 'mv', '-f', old_rel, new_rel],
                    cwd=ROOT, capture_output=True,
                    encoding='utf-8', errors='replace',
                )
                if r.returncode != 0:
                    print(f'ERR: git mv {old_rel} -> {new_rel}: {r.stderr}', file=sys.stderr)
                else:
                    rename_count += 1
    return rename_count, alias_count


def main():
    dry_run = '--dry-run' in sys.argv
    plans = {
        '数学': plan_subject('数学', MATH_GROUP),
        '语文': plan_subject('语文', LANG_GROUP),
        '英语': plan_subject('英语', ENG_GROUP),
    }
    for subj, plan in plans.items():
        renames = sum(1 for o, n, _ in plan if o != n)
        print(f'{subj}: {len(plan)} entries, {renames} renames planned')
    if dry_run:
        # Show first 5 of each
        for subj, plan in plans.items():
            print(f'\n=== {subj} sample ===')
            for o, n, _ in plan[:3]:
                print(f'  {o.name} -> {n.name}')
            print('  ...')
            for o, n, _ in plan[-3:]:
                print(f'  {o.name} -> {n.name}')
        return
    for subj, plan in plans.items():
        rc, ac = apply_plan(plan)
        print(f'{subj}: renamed {rc}, aliases updated {ac}')


if __name__ == '__main__':
    main()
