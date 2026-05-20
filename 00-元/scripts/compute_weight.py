"""计算学科词条多段权重（配置驱动）。

公式：
  反链得分 = Σ (省份权重[atom.省] × 文理权重[atom.文理])  for each backlink
  来源得分 = 课标必考 × 3 + 学习路径 × 2 + alias数 × 1
  weight  = (反链得分 + 来源得分) × 学段权重[学段] × 缩放系数

字段写 frontmatter：
  weight: int
  weight_breakdown: {flow-style JSON}   # 单行紧凑，不破坏多行 fm 结构

CLI:
  python 00-元/scripts/compute_weight.py --dry-run         # 仅打印 top
  python 00-元/scripts/compute_weight.py --apply           # 全库落盘
  python 00-元/scripts/compute_weight.py --subject 数学 --apply
  python 00-元/scripts/compute_weight.py --top 20          # 打印 top N 调试

非启用维度（权重=0）：breakdown 仍计算并写盘，调 yaml 即时刷新。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from _utils import (  # noqa: E402
    REPO_ROOT,
    SUBJECT_DIRS,
    iter_entries,
    iter_exam_dirs,
    read_frontmatter,
    setup_utf8,
)

CONFIG_PATH = Path(__file__).parent / "weight_config.yaml"
BACKLINK_RE = re.compile(
    r"<!-- exam-backlinks-start -->(.*?)<!-- exam-backlinks-end -->", re.DOTALL
)
LINK_RE = re.compile(r"\[\[([^\[\]|]+?)(?:\|[^\]]*)?\]\]")
FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_list_field(v: str) -> list[str]:
    """`[高中]` / `[高中, 初中]` → ['高中', '初中']；裸 `高中` → ['高中']。"""
    if not v:
        return []
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        return [x.strip() for x in v[1:-1].split(",") if x.strip()]
    return [v]


def build_atom_index() -> dict[str, dict[str, str]]:
    """所有真题 stem → {province, gender, year, subject}。

    province 从目录名 `<省>-<科>` 取；gender 从 frontmatter `文理`。
    """
    idx: dict[str, dict[str, str]] = {}
    for sub in iter_exam_dirs():
        # 目录名 `北京-数学` / `吉林-英语`
        parts = sub.name.split("-", 1)
        if len(parts) != 2:
            continue
        province, subject = parts
        for p in sub.glob("*.md"):
            fm = read_frontmatter(p)
            idx[p.stem] = {
                "province": province,
                "gender": (fm.get("文理") or "不分").strip(),
                "year": (fm.get("年份") or "").strip(),
                "subject": subject,
            }
    return idx


def build_path_refs() -> dict[str, int]:
    """学习路径文件中引用的词条 stem → 引用次数。

    扫 00-元/学习路径/<学段>/<学科>/*.md 内所有 `[[X]]` 链接。
    """
    refs: dict[str, int] = defaultdict(int)
    base = REPO_ROOT / "00-元" / "学习路径"
    if not base.is_dir():
        return refs
    for p in base.rglob("*.md"):
        try:
            txt = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for m in LINK_RE.finditer(txt):
            target = m.group(1).strip()
            if "#" in target:
                target = target.split("#", 1)[0]
            refs[target] += 1
    return refs


def extract_backlink_atoms(text: str) -> list[str]:
    """从词条 <!-- exam-backlinks-start --> 段抽真题 atom stems。"""
    m = BACKLINK_RE.search(text)
    if not m:
        return []
    block = m.group(1)
    return [mm.group(1).strip() for mm in LINK_RE.finditer(block)]


def count_aliases(fm: dict[str, str], bare: str) -> int:
    """frontmatter aliases 数（减 bare-name 自身）。"""
    raw = fm.get("aliases", "")
    if not raw:
        return 0
    items = parse_list_field(raw)
    n = len(items)
    if bare in items:
        n -= 1
    return max(0, n)


def period_factor(fm_xueduan: str, cfg: dict[str, Any]) -> tuple[float, str]:
    """学段权重 = max(适用段)；返回 (系数, 命中段名)。"""
    pw = cfg["学段权重"]
    segments = parse_list_field(fm_xueduan)
    if not segments:
        return 0.0, ""
    best, best_seg = 0.0, ""
    for seg in segments:
        v = pw.get(seg, 0.0)
        if v > best:
            best, best_seg = v, seg
    return best, best_seg


def is_core_concept(fm: dict[str, str]) -> int:
    """课标必考占位：当前未引入字段，恒 0。未来通过 frontmatter 标记开启。"""
    state = (fm.get("状态") or "").strip()
    return 1 if state in {"核心", "必考"} else 0


def compute_one(
    path: Path,
    text: str,
    fm: dict[str, str],
    atom_idx: dict[str, dict[str, str]],
    path_refs: dict[str, int],
    cfg: dict[str, Any],
) -> dict[str, Any]:
    """单词条权重 + breakdown。"""
    # 1) 真题反链 → (province, gender) 分组
    backlink_stems = extract_backlink_atoms(text)
    pg_counts: dict[str, int] = defaultdict(int)
    for stem in backlink_stems:
        meta = atom_idx.get(stem)
        if not meta:
            continue
        key = f"{meta['province']}-{meta['gender']}"
        pg_counts[key] += 1

    # 2) 反链得分
    prov_w = cfg["省份权重"]
    gen_w = cfg["文理权重"]
    backlink_score = 0.0
    for key, cnt in pg_counts.items():
        province, gender = key.split("-", 1)
        wp = prov_w.get(province, prov_w.get("全国默认", 0.0))
        wg = gen_w.get(gender, 0.0)
        backlink_score += cnt * wp * wg

    # 3) 来源得分
    src_w = cfg["来源权重"]
    core_n = is_core_concept(fm)
    path_n = path_refs.get(path.stem, 0)
    alias_n = count_aliases(fm, path.stem.split("-", 1)[-1] if "-" in path.stem else path.stem)
    bare = re.sub(r"^\d+-", "", path.stem)
    alias_n = count_aliases(fm, bare)
    source_score = (
        core_n * src_w.get("课标必考", 0.0)
        + path_n * src_w.get("学习路径", 0.0)
        + alias_n * src_w.get("alias收敛", 0.0)
    )

    # 4) 学段乘子
    period_w, period_hit = period_factor(fm.get("学段", ""), cfg)

    raw = (backlink_score + source_score) * period_w
    scale = float(cfg.get("缩放系数", 1.0))
    final = round(raw * scale)

    breakdown = {
        "prov_gen": dict(pg_counts),
        "source": {
            "课标必考": core_n,
            "学习路径": path_n,
            "alias": alias_n,
        },
        "period": period_hit or "未识别",
        "config_version": cfg.get("配置版本", ""),
        "computed": date.today().isoformat(),
    }
    return {"weight": final, "weight_breakdown": breakdown, "raw": raw}


FLAT_FIELDS = [
    "weight",
    "吉林反链", "黑龙江反链", "北京反链", "湖南反链",
    "alias_count", "学习路径出现",
    "weight_breakdown",
]


def upsert_fm_fields(text: str, weight: int, breakdown: dict[str, Any]) -> str:
    """frontmatter 插入/替换 weight 系列扁平字段 + JSON breakdown。

    扁平字段（Dataview 友好）：weight / 吉林反链 / 黑龙江反链 / 北京反链 /
    湖南反链 / alias_count / 学习路径出现 / weight_breakdown（JSON 详情）。
    """
    m = FM_RE.match(text)
    if not m:
        return text
    fm_body = m.group(1)
    bd_str = json.dumps(breakdown, ensure_ascii=False, separators=(",", ":"))
    pg = breakdown.get("prov_gen", {})

    def prov_total(prov: str) -> int:
        return sum(v for k, v in pg.items() if k.startswith(f"{prov}-"))

    flats = {
        "weight": weight,
        "吉林反链": prov_total("吉林"),
        "黑龙江反链": prov_total("黑龙江"),
        "北京反链": prov_total("北京"),
        "湖南反链": prov_total("湖南"),
        "alias_count": breakdown.get("source", {}).get("alias", 0),
        "学习路径出现": breakdown.get("source", {}).get("学习路径", 0),
        "weight_breakdown": bd_str,
    }

    new_lines: list[str] = []
    seen: set[str] = set()
    for line in fm_body.splitlines():
        replaced = False
        for k, v in flats.items():
            if line.startswith(f"{k}:"):
                new_lines.append(f"{k}: {v}")
                seen.add(k)
                replaced = True
                break
        if not replaced:
            new_lines.append(line)
    for k, v in flats.items():
        if k not in seen:
            new_lines.append(f"{k}: {v}")
    new_fm = "\n".join(new_lines)
    return text[: m.start(1)] + new_fm + text[m.end(1) :]


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="写盘；否则仅 dry-run")
    ap.add_argument("--subject", help="仅指定学科目录（默认全学科）")
    ap.add_argument("--top", type=int, default=20, help="dry-run 显示 top N（默认 20）")
    args = ap.parse_args()

    cfg = load_config()
    atom_idx = build_atom_index()
    path_refs = build_path_refs()
    print(f"加载：{len(atom_idx)} 真题 atoms / {len(path_refs)} 学习路径引用 stems",
          flush=True)

    subjects = [args.subject] if args.subject else SUBJECT_DIRS
    all_results: list[tuple[Path, int, dict[str, Any], float]] = []
    n_written = 0

    for s in subjects:
        sd = REPO_ROOT / s
        if not sd.is_dir():
            continue
        for p in iter_entries(sd):
            text = p.read_text(encoding="utf-8")
            fm = read_frontmatter(p)
            if not fm:
                continue
            r = compute_one(p, text, fm, atom_idx, path_refs, cfg)
            all_results.append((p, r["weight"], r["weight_breakdown"], r["raw"]))
            if args.apply:
                new_text = upsert_fm_fields(text, r["weight"], r["weight_breakdown"])
                if new_text != text:
                    p.write_text(new_text, encoding="utf-8", newline="")
                    n_written += 1

    all_results.sort(key=lambda x: -x[1])
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"\n[{mode}] 扫描 {len(all_results)} 词条 / 写盘 {n_written}", flush=True)

    nonzero = [r for r in all_results if r[1] > 0]
    print(f"weight > 0：{len(nonzero)} 词条")
    print(f"\nTop {args.top}（按 weight 降序）：")
    for p, w, bd, raw in all_results[: args.top]:
        rel = p.relative_to(REPO_ROOT)
        pg = bd["prov_gen"]
        print(f"  {w:5d}  {rel}  prov_gen={pg}  src={bd['source']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
