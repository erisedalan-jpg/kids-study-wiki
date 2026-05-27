# gen_kaodian_review.py
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

_PROMPT = Path(__file__).parent / "_prompts" / "kaodian_review.md"


def _load_template() -> str:
    return _PROMPT.read_text(encoding="utf-8")


def build_prompt(subject: str, kaodian: str, info: dict, rep_n: int = 3) -> str:
    items = info["真题"]
    rep_ids = {it["_bare"] for it in items[:rep_n]}   # 近年优先（已降序）
    blocks = []
    for it in items:
        mark = "【代表题】" if it["_bare"] in rep_ids else ""
        blocks.append(
            f"### {mark}{it['_bare']}（{it.get('年份','')}）\n"
            f"题干：{it.get('题干文本','') or it.get('摘要','')}\n"
            f"解析：{it.get('解析文本','')}"
        )
    corpus = "\n\n".join(blocks)
    y0, y1 = info["年份跨度"]
    return _load_template().format(
        subject=subject, kaodian=kaodian, parent=info["父主题"],
        n=info["真题数"], y0=y0, y1=y1, corpus=corpus,
    )


# ---------------------------------------------------------------------------
# 延迟导入辅助模块（避免 import 阶段失败影响纯单元测试）
# ---------------------------------------------------------------------------

def _import_helpers():
    sys.path.insert(0, str(Path(__file__).parent))
    from _utils import REPO_ROOT, read_frontmatter, setup_utf8  # noqa: E402
    from _llm_router import call, Task  # noqa: E402
    from kaodian_aggregate import build_kaodian_map  # noqa: E402
    return REPO_ROOT, read_frontmatter, setup_utf8, call, Task, build_kaodian_map


def resolve_concept(kaodian: str, alias_lookup: dict[str, str],
                    weights: dict[str, str | int]) -> tuple[str, int]:
    """考点 → (wikilink 到概念词条, weight)。无对应词条返回 ("", 0)。"""
    stem = alias_lookup.get(kaodian)
    if not stem:
        return "", 0
    try:
        w = int(weights.get(stem, 0) or 0)
    except ValueError:
        w = 0
    return f"[[{stem}|{kaodian}]]", w


GROUP = lambda subj: Path(__file__).parent / f"group_考点_{subj}.yaml"


def _safe_name(s: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", s)


def render_md(subject: str, kaodian: str, info: dict, *, llm_body: str,
              weight: int, concept_link: str) -> str:
    y0, y1 = info["年份跨度"]
    pos = " ".join(f"{t}{n}" for t, n in info["题位"])
    diff = " ".join(f"{k}{v}" for k, v in info["难度分布"].items())
    fm = (f"---\ntitle: {kaodian}\n考点: {kaodian}\n父主题: {info['父主题']}\n"
          f"学科: {subject}\nweight: {weight}\n真题数: {info['真题数']}\n"
          f"高频题位: [{', '.join(f'{t}{n}' for t, n in info['题位'])}]\n状态: 草稿\n---\n")
    定位 = (f"\n## 考点定位\n\n- 父主题：{info['父主题']}\n- 权重 weight：{weight}\n"
            f"- 真题数：{info['真题数']}；年份跨度：{y0}–{y1}\n"
            f"- 出现题位：{pos}\n- 难度分布：{diff}\n")
    清单 = ["\n## 全部真题清单\n"]
    for it in info["真题"]:
        清单.append(f"- [[{it['_bare']}]]（{it.get('年份','')} · {it.get('难度','')}）"
                    f" {it.get('摘要','')}")
    关联 = f"\n\n## 关联\n\n- 概念词条：{concept_link or '（暂无对应词条）'}\n"
    return fm + 定位 + "\n" + llm_body.strip() + "\n" + "\n".join(清单) + 关联


def main() -> int:
    REPO_ROOT, read_frontmatter, setup_utf8, call, Task, build_kaodian_map = _import_helpers()
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--province", default="吉林")
    ap.add_argument("--subject", default="数学")
    ap.add_argument("--考点", dest="one")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--regen", action="store_true", help="草稿也重生")
    args = ap.parse_args()

    exam_dir = REPO_ROOT / "真题" / f"{args.province}-{args.subject}"
    atoms = []
    for p in sorted(exam_dir.glob("*.md")):
        fm = read_frontmatter(p)
        fm["_bare"] = p.stem
        body = p.read_text(encoding="utf-8")
        for tag in ("题干文本", "解析文本"):
            m = re.search(rf"## {tag}\n(.*?)(?:\n<!--|\n## |\Z)", body, re.S)
            fm[tag] = m.group(1).strip() if m else ""
        atoms.append(fm)

    group_file = GROUP(args.subject)
    group: dict[str, str] = {}
    if group_file.exists():
        raw = yaml.safe_load(group_file.read_text(encoding="utf-8")) or {}
        group = {str(k): str(v) for k, v in raw.items()}
    kmap = build_kaodian_map(atoms, group)
    if args.one:
        kmap = {args.one: kmap[args.one]} if args.one in kmap else {}

    from fix_wikilinks import collect_targets
    _, alias_lookup = collect_targets()
    weights: dict[str, int] = {}
    subj_dir = REPO_ROOT / args.subject
    if subj_dir.is_dir():
        for cp in subj_dir.glob("*.md"):
            wf = read_frontmatter(cp)
            if wf.get("weight"):
                weights[cp.stem] = wf["weight"]

    out_dir = REPO_ROOT / "复习" / args.subject
    out_dir.mkdir(parents=True, exist_ok=True)
    items = list(kmap.items())
    if args.limit:
        items = items[: args.limit]
    done = skip = 0
    for kp, info in items:
        fpath = out_dir / f"{_safe_name(kp)}.md"
        if fpath.exists():
            if read_frontmatter(fpath).get("状态") == "已校对" or not args.regen:
                skip += 1
                continue
        prompt = build_prompt(args.subject, kp, info)
        try:
            body = call(prompt=prompt, task=Task.COMPLEX,
                        system=f"你是高考{args.subject}复习资料编辑，输出知识密集的应试复习正文。").text
        except Exception as ex:  # noqa: BLE001
            print(f"  ⚠ {kp}: LLM 失败 {ex}")
            continue
        concept_link, weight = resolve_concept(kp, alias_lookup, weights)
        md = render_md(args.subject, kp, info, llm_body=body, weight=weight,
                       concept_link=concept_link)
        if args.apply:
            fpath.write_text(md, encoding="utf-8")
        done += 1
        print(f"  ✓ {kp}（{info['真题数']}题）")
    print(f"{'[APPLY]' if args.apply else '[dry-run]'} 生成 {done} / 跳过 {skip}（复习/{args.subject}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
