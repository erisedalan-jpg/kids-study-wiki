# gen_kaodian_review.py
from __future__ import annotations

import argparse
import re
import re as _re
import sys
from pathlib import Path

import yaml

_PROMPT = Path(__file__).parent / "_prompts" / "kaodian_review.md"

_REQUIRED_BLOCKS = ("## 知识精要", "## 解题方法与套路", "## 高频易错", "## 代表题精讲")

_LEAK_MARKERS = ("让我重新", "这提示我们", "理解有误", "我需要重新", "重新审视",
                 "似乎不对", "等等，", "等等,", "哦，", "不对，", "依然零解", "我们对总场")


def body_is_complete(body: str) -> bool:
    """LLM 正文是否非空且含全部必需区块。"""
    return bool(body.strip()) and all(b in body for b in _REQUIRED_BLOCKS)


def body_is_clean(body: str) -> bool:
    """拒绝带推导草稿/自我怀疑的脏输出：超长行(>700)或多处思考犹豫标志。"""
    if any(len(line) > 700 for line in body.splitlines()):
        return False
    if sum(body.count(m) for m in _LEAK_MARKERS) >= 2:
        return False
    return True


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


def _generate_one(subject: str, kp: str, info: dict, alias_lookup: dict,
                  weights: dict, call_fn) -> tuple[str, str | None, str]:
    """生成单个考点专题。返回 (考点, md或None, 状态)。call_fn(prompt)->带 .text 的结果。
    全程异常安全：任何失败返回 (kp, None, 状态)，绝不抛出（避免中断线程池其余任务）。"""
    try:
        prompt = build_prompt(subject, kp, info)
        body = call_fn(prompt).text
        if not body_is_complete(body):
            return kp, None, "输出空或缺区块"
        if not body_is_clean(body):
            return kp, None, "疑似思考泄漏/超长行"
        concept_link, weight = resolve_concept(kp, alias_lookup, weights)
        md = render_md(subject, kp, info, llm_body=body, weight=weight, concept_link=concept_link)
        return kp, md, "ok"
    except Exception as ex:  # noqa: BLE001
        return kp, None, f"失败 {type(ex).__name__}: {ex}"


GROUP = lambda subj: Path(__file__).parent / f"group_考点_{subj}.yaml"


def _safe_name(s: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", s)


def _parse_kaodian(v) -> list[str]:
    """考点 字段 → list[str]；兼容 read_frontmatter 返回的字符串 "[a, b]" 或已是 list。"""
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    s = (v or "").strip()
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1]
    return [x.strip() for x in re.split(r"[,，、]", s) if x.strip()]


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
    ap.add_argument("--workers", type=int, default=16, help="并发生成线程数")
    args = ap.parse_args()

    exam_dir = REPO_ROOT / "真题" / f"{args.province}-{args.subject}"
    atoms = []
    for p in sorted(exam_dir.glob("*.md")):
        fm = read_frontmatter(p)
        fm["_bare"] = p.stem
        fm["考点"] = _parse_kaodian(fm.get("考点"))
        body = p.read_text(encoding="utf-8")
        for tag in ("题干文本", "解析文本"):
            m = re.search(rf"## {tag}\n(.*?)(?:\n<!--|\n## |\Z)", body, re.S)
            fm[tag] = m.group(1).strip() if m else ""
        m_zy = re.search(r"## 摘要\n(.*?)(?:\n## |\n<!--|\Z)", body, re.S)
        fm["摘要"] = m_zy.group(1).strip() if m_zy else ""
        atoms.append(fm)

    group_file = GROUP(args.subject)
    group: dict[str, str] = {}
    if group_file.exists():
        raw = yaml.safe_load(group_file.read_text(encoding="utf-8")) or {}
        group = {str(k): str(v) for k, v in raw.items()}
    kmap = build_kaodian_map(atoms, group)
    if args.one:
        kmap = {args.one: kmap[args.one]} if args.one in kmap else {}

    if args.apply:
        from fix_wikilinks import collect_targets
        _, alias_lookup = collect_targets()
        weights: dict[str, int] = {}
        subj_dir = REPO_ROOT / args.subject
        if subj_dir.is_dir():
            for cp in subj_dir.glob("*.md"):
                wf = read_frontmatter(cp)
                if wf.get("weight"):
                    weights[cp.stem] = wf["weight"]
    else:
        alias_lookup = {}
        weights = {}

    out_dir = REPO_ROOT / "复习" / args.subject
    out_dir.mkdir(parents=True, exist_ok=True)
    items = list(kmap.items())
    if args.limit:
        items = items[: args.limit]

    # --- build todo list (apply skip logic; dry-run path unchanged) ---
    skip = 0
    if not args.apply:
        done = 0
        for kp, info in items:
            fpath = out_dir / f"{_safe_name(kp)}.md"
            if fpath.exists():
                if read_frontmatter(fpath).get("状态") == "已校对" or not args.regen:
                    skip += 1
                    continue
            print(f"  · {kp}（{info['真题数']}题）", flush=True)
            done += 1
        print(f"[dry-run] 将生成 {done} / 跳过 {skip}（复习/{args.subject}）", flush=True)
        return 0

    # --- apply mode: build todo, then parallel generation ---
    todo = []
    for kp, info in items:
        fpath = out_dir / f"{_safe_name(kp)}.md"
        if fpath.exists():
            if read_frontmatter(fpath).get("状态") == "已校对" or not args.regen:
                skip += 1
                continue
        todo.append((kp, info))

    from concurrent.futures import ThreadPoolExecutor, as_completed
    call_fn = lambda p: call(prompt=p, task=Task.COMPLEX,
                             system=f"你是高考{args.subject}复习资料编辑，输出知识密集的应试复习正文。")
    done = fail = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(_generate_one, args.subject, kp, info,
                            alias_lookup, weights, call_fn): kp
                for kp, info in todo}
        for fut in as_completed(futs):
            kp, md, status = fut.result()
            if md is not None:
                (out_dir / f"{_safe_name(kp)}.md").write_text(md, encoding="utf-8")
                done += 1
                print(f"  ✓ {kp}", flush=True)
            else:
                fail += 1
                print(f"  ⚠ {kp}: {status}", flush=True)
    print(f"[APPLY] 生成 {done} / 跳过 {skip} / 失败 {fail}（复习/{args.subject}）", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
