"""英语真题元数据抽取（专用，篇章/大题级）。

读 exam_eng_screenshot.py 的 blocks.json，对每块从 raw_ans/raw_sol 结构化：
- answer：聚合答案（去页眉噪声 + 【答案】标记，折叠为 "1. C  2. B …"）
- 文体：【导语】里「本文是一篇X文」/「书面表达」
- 题型：答案形态 + qno 段位推断（鲁棒于年份块数变化）
- solution_text：raw_sol（【导语】+逐题详解，喂 enrich）

题型推断（优先答案形态，qno 辅助）：
  无 qno / raw_ans 含 Dear / sol 含「书面表达」 → 书面表达
  答案为长句（含多词空格） → 阅读表达
  答案字母含 F/G（A–G 选项） → 七选五
  答案纯单字母 ABCD，qno 起点 ≥ 21 → 阅读理解
  答案为单词/词组（非单字母），qno 11–20 → 语篇填空
  答案纯单字母，qno 起点 ≤ 10 → 完形填空
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, setup_utf8  # noqa: E402

NOISE = re.compile(r"第\s*\d+\s*页|共\s*\d+\s*页|学科网|股份有限公司")
# 听力块：raw_sol 以【原文】开头（截图偶丢前导【，故【可选）。
# 篇章块以【导语】开头 → 永不命中；北京机考无听力卷亦无此标记 → 向后兼容。
LISTENING = re.compile(r"^\s*【?\s*原\s*文\s*】")
ANS_TAG = re.compile(r"【\s*答\s*案\s*】")
GENRE = re.compile(r"本文是一篇\s*(.{1,10}?文)")
WRITING = re.compile(r"书面表达|应用文写|读后续写")
# 一条答案项: "12. self-awareness" / "1. C" / "35. G"
ANS_ITEM = re.compile(r"(\d{1,2})\s*[\.．]\s*([^\n]*?)\s*(?=\d{1,2}\s*[\.．]|\Z)", re.S)


def clean_answer(raw: str) -> str:
    """去页眉噪声 + 【答案】标记，折叠聚合答案为单行。"""
    txt = ANS_TAG.split(raw, maxsplit=1)
    body = txt[1] if len(txt) > 1 else txt[0]
    lines = [ln.strip() for ln in body.splitlines()
             if ln.strip() and not NOISE.search(ln)]
    joined = " ".join(lines)
    return re.sub(r"\s+", " ", joined).strip()


def infer_genre(raw_sol: str) -> str:
    # 只看【导语】区（前 80 字），避免 raw_sol 尾部混入下块文体
    head = raw_sol[:80]
    m = GENRE.search(head)
    if m:
        return m.group(1)
    if WRITING.search(head):
        return "应用文/书面表达"
    return ""


def infer_qtype(qnos: list[int], answer: str, raw_ans: str, raw_sol: str) -> str:
    # 抽答案项的值部分（先算，作为最强特征）
    vals = [m.group(2).strip() for m in ANS_ITEM.finditer(
        ANS_TAG.split(raw_ans, maxsplit=1)[-1])]
    vals = [v for v in vals if v and not NOISE.search(v)]
    single_letter = [v for v in vals if re.fullmatch(r"[A-G]", v)]
    longish = [v for v in vals if len(v.split()) >= 3]
    start = min(qnos) if qnos else 99
    # WRITING 只看【导语】区（前 80 字），避免 raw_sol 尾部混入下块书面表达
    head = raw_sol[:80]

    # 1) 无 qno / Dear 开头 / 【导语】明示书面表达 → 书面表达
    if not qnos or "Dear" in raw_ans[:80] or WRITING.search(head):
        return "书面表达"
    # 2) 七选五：全 A–G 单字母且含 E/F/G，qno 35–45（强特征，优先于阅读）
    if (vals and all(re.fullmatch(r"[A-G]", v) for v in vals)
            and any(v in ("E", "F", "G") for v in vals) and 35 <= start <= 45):
        return "七选五"
    # 3) 长句答案 → 阅读表达（主观简答）
    if longish and len(longish) >= max(1, len(vals) // 2):
        return "阅读表达"
    # 3.5) 单篇 ≥10 个单字母空 → 完形填空（阅读篇章每篇 ≤5 题；
    #      北京完形 qno1-10 亦 ≥10 空命中，向后兼容）
    if single_letter and len(single_letter) == len(vals) and len(vals) >= 10:
        return "完形填空"
    # 4) 纯单字母 ABCD，qno≥21 → 阅读理解
    if single_letter and len(single_letter) == len(vals) and start >= 21:
        return "阅读理解"
    if start <= 10 and single_letter:
        return "完形填空"
    if 11 <= start <= 20:
        return "语篇填空"
    if single_letter:
        return "阅读理解"
    return "语篇填空"


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", required=True)
    args = ap.parse_args()
    bp = Path(args.blocks)
    qa = json.loads(bp.read_text(encoding="utf-8"))

    for b in qa["blocks"]:
        raw_ans = b.get("raw_ans", "")
        raw_sol = b.get("raw_sol", "")
        b["is_listening"] = bool(LISTENING.match(raw_sol))
        if b["is_listening"]:
            # 听力块不进篇章考点模型（render 跳过），仅标记
            b["answer"] = clean_answer(raw_ans)
            b["genre"] = ""
            b["qtype"] = "听力"
            b["solution_text"] = ""
            continue
        b["answer"] = clean_answer(raw_ans)
        b["genre"] = infer_genre(raw_sol)
        b["qtype"] = infer_qtype(b.get("qnos", []), b["answer"], raw_ans, raw_sol)
        # solution_text：导语 + 详解（喂 enrich），去页眉噪声
        sol_lines = [ln for ln in raw_sol.splitlines() if not NOISE.search(ln)]
        b["solution_text"] = "\n".join(sol_lines).strip()

    bp.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: {len(qa['blocks'])} 块结构化 → {bp.name}")
    for b in qa["blocks"]:
        print(f"  块{b['block_no']:>2} {b['qtype']:<6} qno={b['qno_range']:<7} "
              f"文体={b['genre']:<14} ans={b['answer'][:48]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
