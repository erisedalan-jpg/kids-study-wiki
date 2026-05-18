"""真题截图生成（v2 Step 1）。

用 PyMuPDF 提取每个 PDF 页面的 word boxes（含 bbox），定位：
- 题号 anchor: 形如 "1." "23." 的 word，必须从 1 开始递增
- 答案 anchor: "【答案】" 或带空格的 "【 答 案 】"

然后按 题面区域 = (题号 N → 答案 anchor) / 解析区域 = (答案 anchor → 题号 N+1)
渲染 PNG 截图到 素材/真题截图/<省份>-<学科>/ 目录。

输出: questions.json（含 qno/bbox/page/截图相对路径）

CLI:
    python 00-元/scripts/exam_screenshot.py \\
        --pdf "素材/真题/.../2022年高考数学试卷（文）.pdf" \\
        --province 吉林 --subject 数学 --year 2022 \\
        --out docs/superpowers/working/
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

sys.path.insert(0, str(Path(__file__).parent))
from _exam_utils import (  # noqa: E402
    build_atom_filename,
    build_screenshot_filename,
    load_config,
    normalize_gender,
    normalize_paper,
)
from _utils import REPO_ROOT, setup_utf8  # noqa: E402


# 题号正则：行首数字 + 点（不允许点后接数字，排除 0.04 / 1.6158 等小数）
# 不要求 token 整体仅为题号 —— 早年 PDF (2008-2020) PyMuPDF 把题号+题面合并成
# 单个 word（如 "1．（5分）已知集合M="），仍可从开头取 anchor。
# 例外：点后紧跟「4位数字+年」放行——题干以年份开头的真题号会被防小数
# 误杀（北京数学2020 Q10 "10.2020年3月14日…国际圆周率日"），此特征
# 极特异，不会与 0.04 / 1.6158 等小数冲突。
QNO_TOKEN_RE = re.compile(r"^([1-9]\d?)[\.、．](?:(?!\d)|(?=\d{4}\s*年))")


def find_question_anchors(
    words: list[tuple], expected_max_qno: int, start_qno: int = 1,
    relax_strict: bool = False,
) -> dict[int, dict[str, float]]:
    """找题号 anchor。

    words: PyMuPDF page.get_text("words") 返回的元组列表
           (x0, y0, x1, y1, text, block_no, line_no, word_no)
    返回: {qno: {"x0", "y0", "x1", "y1", "block_no", "line_no"}}

    relax_strict=False (默认): 题号必须从 `start_qno` 起严格递增，跳号丢弃。
    relax_strict=True: 接受每个 unique qno 首次出现，用于 PDF 中部分题号缺
        失的异常卷救援。
    多页 PDF 应由调用方跨页传递 running counter（见 render_screenshots）。
    """
    candidates: list[tuple[int, dict]] = []
    for w in words:
        x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]
        m = QNO_TOKEN_RE.match(text.strip())
        if not m:
            continue
        qno = int(m.group(1))
        if qno > expected_max_qno + 5:  # 容忍 +5 缓冲
            continue
        candidates.append((qno, {
            "x0": x0, "y0": y0, "x1": x1, "y1": y1,
            "block_no": w[5] if len(w) > 5 else 0,
            "line_no": w[6] if len(w) > 6 else 0,
        }))

    # 按 y 坐标排序（页面阅读顺序），然后筛递增
    candidates.sort(key=lambda x: x[1]["y0"])
    result: dict[int, dict] = {}
    if relax_strict:
        # 每 qno 取首次出现，不强制递增
        for qno, info in candidates:
            if qno not in result:
                result[qno] = info
        return result
    next_expected = start_qno
    for qno, info in candidates:
        if qno == next_expected:
            result[qno] = info
            next_expected = qno + 1
    return result


def find_answer_anchors(words: list[tuple]) -> list[dict[str, float]]:
    """找题面与解答区段的分隔 anchor。

    覆盖多种 PDF 格式:
    - 【答案】/【 答 案 】 — 2021+ 新格式
    - 【考点】 — 2008-2020 旧格式题面后首块
    - 【解答】/【解析】 — 解析主体
    - `答案：` / `解析：` / `解答：` — 2021 数学卷类无括号变体
    取最早出现者作为分隔，所以 q.png 仅含题面+选项，a.png 含其后全部解析。

    返回按 y 坐标排序的 list[{"x0", "y0", "x1", "y1"}]。
    """
    answer_re = re.compile(
        r"^(?:"
        r"【\s*(?:答\s*案|考\s*点|解\s*答|解\s*析|参\s*考\s*答\s*案|参\s*考\s*译\s*文)\s*】"
        r"|答\s*案\s*[：:]"
        r"|解\s*析\s*[：:]"
        r"|解\s*答\s*[：:]"
        r"|参\s*考\s*答\s*案\s*[：:]"
        r")"
    )
    anchors: list[dict] = []
    for w in words:
        text = w[4]
        if answer_re.match(text):
            anchors.append({
                "x0": w[0], "y0": w[1], "x1": w[2], "y1": w[3],
            })
    anchors.sort(key=lambda a: a["y0"])
    return anchors


def compute_regions(
    q_anchors: dict[int, dict],
    a_anchors: list[dict],
    page_height: float,
) -> dict[int, dict[str, dict | None]]:
    """根据题号+答案 anchor 算每题的截图区域（**单页内**）。

    返回 {qno: {"q": region_or_None, "a": region_or_None}}
    region = {"y0": float, "y1": float}（x 范围由调用方在渲染时补，通常用整页宽）

    策略:
    - 题面 region: y0=题号 y0, y1=该题对应 answer anchor 的 y0 (若有)，否则下一题题号 y0
    - 解析 region: y0=answer y0, y1=下一题题号 y0（若无下一题用 page_height）
    - answer anchor 区间用左闭右开 [q_y0, next_q_y0)，对应"恰好在 q_y0 行的 answer 也归当前题"语义

    范围边界:
    - 本函数仅处理**单页内**切分。跨页题（题号在本页但 answer/下一题号在下一页）
      的处理由上层 `render_screenshots` 负责（按 page 拆 + 跨页合并截图）。
    - 最后一题的 y1 = page_height，可能包含页脚/页码；上层渲染时自行 crop 或忽略。
    - PyMuPDF y 排序异常（如浮动元素导致 a_y0 < q_y0）：未匹配的 answer 会被静默
      丢弃，但函数末尾打印 stderr warning 提示上层。
    """
    sorted_qnos = sorted(q_anchors.keys())
    regions: dict[int, dict] = {}
    matched_a_indices: set[int] = set()
    for i, qno in enumerate(sorted_qnos):
        q_y0 = q_anchors[qno]["y0"]
        next_q_y0 = (
            q_anchors[sorted_qnos[i + 1]]["y0"]
            if i + 1 < len(sorted_qnos)
            else page_height
        )
        # 找该题区间内第一个 answer anchor（左闭右开）
        a_idx_in_range = next(
            (
                idx for idx, a in enumerate(a_anchors)
                if q_y0 <= a["y0"] < next_q_y0
            ),
            None,
        )
        if a_idx_in_range is not None:
            a = a_anchors[a_idx_in_range]
            matched_a_indices.add(a_idx_in_range)
            q_region = {"y0": q_y0, "y1": a["y0"]}
            a_region = {"y0": a["y0"], "y1": next_q_y0}
        else:
            q_region = {"y0": q_y0, "y1": next_q_y0}
            a_region = None
        regions[qno] = {"q": q_region, "a": a_region}

    # 警告：有未匹配的 answer anchor（y 排序异常）
    unmatched = [
        a for idx, a in enumerate(a_anchors) if idx not in matched_a_indices
    ]
    if unmatched and q_anchors:
        import sys as _sys
        _sys.stderr.write(
            f"compute_regions: {len(unmatched)} answer anchor(s) "
            f"未匹配到任何题号区间（y 排序异常？）\n"
        )

    return regions


def render_screenshots(
    pdf_path: Path,
    *,
    province: str,
    subject: str,
    year: int,
    expected_max_qno: int = 25,
    dpi: int = 200,
    relax_strict: bool = False,
) -> dict[str, Any]:
    """从 PDF 提取题号 + 渲染截图到目标目录。

    返回 questions.json 数据（含 qno / page / 截图相对路径）。

    失败模式（明确 raise）：
    - PDF 不存在 → FileNotFoundError
    - PDF 损坏 / 不可读 → ValueError
    - PDF 加密 → ValueError
    - 全部页面识别不到任何题号（如扫描版无文字层）→ ValueError
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 不存在: {pdf_path}")

    cfg = load_config()
    fname = pdf_path.name
    paper = normalize_paper(fname, cfg)
    gender = normalize_gender(fname, cfg)
    paper_id = f"{year}-{gender}-{paper}"

    out_dir = REPO_ROOT / "素材" / "真题截图" / f"{province}-{subject}"
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        doc = fitz.open(str(pdf_path))
    except fitz.FileDataError as e:
        raise ValueError(f"PDF 损坏或不可读: {pdf_path}: {e}") from e

    try:
        if doc.is_encrypted:
            raise ValueError(f"PDF 已加密，需先解密: {pdf_path}")

        all_questions: list[dict] = []
        all_q_anchors: dict[int, tuple[int, dict]] = {}
        # 缓存每页的 q/a anchors（消除第二遍重复 get_text("words")）
        per_page_anchors: dict[int, dict[str, Any]] = {}
        per_page_height: dict[int, float] = {}

        # 第一遍：先扫每页所有 qno candidate（**保留重复** — instruction-1 + real-Q1 都要）
        raw_q_per_page: dict[int, list[tuple[int, dict]]] = {}
        raw_a_per_page: dict[int, list[dict]] = {}
        for page_no, page in enumerate(doc):
            words = page.get_text("words")
            cands: list[tuple[int, dict]] = []
            for w in words:
                m = QNO_TOKEN_RE.match(w[4].strip())
                if not m:
                    continue
                qno = int(m.group(1))
                if qno > expected_max_qno + 5:
                    continue
                cands.append((qno, {
                    "x0": w[0], "y0": w[1], "x1": w[2], "y1": w[3],
                    "block_no": w[5] if len(w) > 5 else 0,
                    "line_no": w[6] if len(w) > 6 else 0,
                }))
            cands.sort(key=lambda x: x[1]["y0"])
            raw_q_per_page[page_no] = cands
            raw_a_per_page[page_no] = find_answer_anchors(words)
            per_page_height[page_no] = page.rect.height

        # 用 spatial-lookahead 过滤：每个 q 候选必须其后某距离内出现 answer anchor
        # 这能跳过 PDF 顶部 "注意事项 1./2./3./4." 这种伪题号
        from collections import defaultdict
        page_count = len(doc)
        # 把所有 q 候选 + answer anchor 按 (page, y) 全局排序
        all_q_candidates: list[tuple[int, int, dict]] = [
            (p, qno, info)
            for p, cands in raw_q_per_page.items()
            for qno, info in cands
        ]
        all_q_candidates.sort(key=lambda x: (x[0], x[2]["y0"]))
        # answer anchor 全局位置（page, y0）
        all_a_positions: list[tuple[int, float]] = [
            (p, a["y0"]) for p, anchors in raw_a_per_page.items() for a in anchors
        ]
        all_a_positions.sort()

        def has_answer_between(
            p1: int, y1: float, p2: int, y2: float
        ) -> bool:
            """位置 (p1,y1) 到 (p2,y2) 之间是否有 answer anchor。"""
            for ap, ay in all_a_positions:
                if (ap, ay) <= (p1, y1):
                    continue
                if (ap, ay) >= (p2, y2):
                    return False
                return True
            return False

        # 过滤伪题号: 每相邻 (q_i, q_{i+1}) 区间必须含 answer anchor
        # instruction 区段 1./2./3./4. 之间无 anchor → 全部过滤掉
        # 真题 Q1/Q2 之间含 answer → 保留
        filtered_per_page: dict[int, dict[int, dict]] = defaultdict(dict)
        n = len(all_q_candidates)
        passed_count = 0
        for i, (p, qno, info) in enumerate(all_q_candidates):
            if i + 1 < n:
                np_, _, ninfo = all_q_candidates[i + 1]
                next_p, next_y = np_, ninfo["y0"]
            else:
                next_p = page_count - 1
                next_y = per_page_height[next_p]
            if relax_strict or has_answer_between(p, info["y0"], next_p, next_y):
                filtered_per_page[p][qno] = info
                passed_count += 1

        # Fallback: 如果过滤后保留率 < 80%，说明 filter 误伤真题（如英语
        # 卷答案集中卷末，Q1-Q19 之间无 anchor → 全被 reject），改放过所有。
        # 安全是因为：fallback 后仍走 strict-from-1，instruction 1./2./3./4.
        # 只在数理化生 PDF 出现 (那些卷 filter 通过率高，不会 fallback)。
        if n > 0 and passed_count / n < 0.8 and not relax_strict:
            filtered_per_page = defaultdict(dict)
            for p, qno, info in all_q_candidates:
                if qno not in filtered_per_page[p]:
                    filtered_per_page[p][qno] = info

        # 第二遍：在过滤后 q_anchors 上应用 strict-from-1（除非 relax_strict）
        running_qno = 1
        for page_no in range(page_count):
            filtered_q = filtered_per_page.get(page_no, {})
            if relax_strict:
                final_q = filtered_q
            else:
                # 仅保留 == running_qno 的，然后递增
                final_q = {}
                for qno in sorted(filtered_q.keys(), key=lambda q: filtered_q[q]["y0"]):
                    if qno == running_qno:
                        final_q[qno] = filtered_q[qno]
                        running_qno += 1
            per_page_anchors[page_no] = {
                "q_anchors": final_q,
                "a_anchors": raw_a_per_page[page_no],
            }
            for qno, info in final_q.items():
                if qno not in all_q_anchors:
                    all_q_anchors[qno] = (page_no, info)

        if not all_q_anchors:
            raise ValueError(
                f"未识别到任何题号: {pdf_path.name} (可能是扫描版无文字层 / "
                f"或题号格式不在 QNO_TOKEN_RE 范围)"
            )

        # 第二遍：渲染每题截图（跨页支持，多图保留不拼接）
        sorted_qnos = sorted(all_q_anchors.keys())
        for i, qno in enumerate(sorted_qnos):
            page_no, q_info = all_q_anchors[qno]
            q_y0 = q_info["y0"]

            # 下一题边界
            if i + 1 < len(sorted_qnos):
                next_qno = sorted_qnos[i + 1]
                next_page_no, next_info = all_q_anchors[next_qno]
                next_q_y0 = next_info["y0"]
            else:
                next_page_no = len(doc) - 1
                next_q_y0 = per_page_height[next_page_no]

            # 跨页找 a_anchor
            a_anchor = None
            for p in range(page_no, next_page_no + 1):
                for a in per_page_anchors[p]["a_anchors"]:
                    if p == page_no and a["y0"] <= q_y0:
                        continue
                    if p == next_page_no and a["y0"] >= next_q_y0:
                        continue
                    a_anchor = (p, a["y0"])
                    break
                if a_anchor:
                    break

            # 计算 q_pages 和 a_pages 列表 [(page_no, y0, y1), ...]
            q_pages: list[tuple[int, float, float]] = []
            a_pages: list[tuple[int, float, float]] = []
            if a_anchor:
                a_pno, a_y0 = a_anchor
                # 题面: q_y0 → a_anchor
                if page_no == a_pno:
                    q_pages.append((page_no, q_y0, a_y0))
                else:
                    q_pages.append((page_no, q_y0, per_page_height[page_no]))
                    for p in range(page_no + 1, a_pno):
                        q_pages.append((p, 0.0, per_page_height[p]))
                    if a_y0 > 0:
                        q_pages.append((a_pno, 0.0, a_y0))
                # 解析: a_anchor → next_q
                if a_pno == next_page_no:
                    a_pages.append((a_pno, a_y0, next_q_y0))
                else:
                    a_pages.append((a_pno, a_y0, per_page_height[a_pno]))
                    for p in range(a_pno + 1, next_page_no):
                        a_pages.append((p, 0.0, per_page_height[p]))
                    if next_q_y0 > 0:
                        a_pages.append((next_page_no, 0.0, next_q_y0))
            else:
                # 无 a_anchor：题面区域跨到 next_q
                if page_no == next_page_no:
                    q_pages.append((page_no, q_y0, next_q_y0))
                else:
                    q_pages.append((page_no, q_y0, per_page_height[page_no]))
                    for p in range(page_no + 1, next_page_no):
                        q_pages.append((p, 0.0, per_page_height[p]))
                    if next_q_y0 > 0:
                        q_pages.append((next_page_no, 0.0, next_q_y0))

            # 渲染 q 系列
            q_rel_paths: list[str] = []
            for idx, (p, y0, y1) in enumerate(q_pages):
                if y1 - y0 < 5:  # 跳过过小切片
                    continue
                fname = build_screenshot_filename(year, gender, paper, qno, "q", idx)
                out_path = out_dir / fname
                clip = fitz.Rect(0, y0, doc[p].rect.width, y1)
                doc[p].get_pixmap(clip=clip, dpi=dpi).save(str(out_path))
                q_rel_paths.append(
                    f"素材/真题截图/{province}-{subject}/{fname}"
                )

            # 渲染 a 系列
            a_rel_paths: list[str] = []
            for idx, (p, y0, y1) in enumerate(a_pages):
                if y1 - y0 < 5:
                    continue
                fname = build_screenshot_filename(year, gender, paper, qno, "a", idx)
                out_path = out_dir / fname
                clip = fitz.Rect(0, y0, doc[p].rect.width, y1)
                doc[p].get_pixmap(clip=clip, dpi=dpi).save(str(out_path))
                a_rel_paths.append(
                    f"素材/真题截图/{province}-{subject}/{fname}"
                )

            all_questions.append({
                "qno": qno,
                "page": page_no + 1,
                "题面图": q_rel_paths,
                "解析图": a_rel_paths,
            })
    finally:
        doc.close()

    rel_pdf = (
        pdf_path.relative_to(REPO_ROOT)
        if pdf_path.is_relative_to(REPO_ROOT)
        else pdf_path
    )
    return {
        "paper_id": paper_id,
        "year": year,
        "gender": gender,
        "paper": paper,
        "subject": subject,
        "province": province,
        "source_pdf": str(rel_pdf).replace("\\", "/"),
        "questions": all_questions,
    }


def _as_img_list(v: Any) -> list[str]:
    """规范化 题面图/解析图 字段：兼容 str (旧) 和 list (新)。"""
    if not v:
        return []
    if isinstance(v, str):
        return [v]
    return list(v)


def assert_screenshot_quality(qa: dict[str, Any], expected_qno_range: tuple[int, int]) -> list[str]:
    """L1 自动断言。返回违规列表（空 = 通过）。"""
    violations: list[str] = []
    n = len(qa["questions"])
    lo, hi = expected_qno_range
    if not (lo <= n <= hi):
        violations.append(f"题数 {n} 不在期望范围 {lo}-{hi}")
    for q in qa["questions"]:
        q_imgs = _as_img_list(q.get("题面图"))
        if not q_imgs:
            violations.append(f"Q{q['qno']}: 题面图为空")
            continue
        # 至少首张题面图必须存在
        first_q = REPO_ROOT / q_imgs[0]
        if not first_q.exists():
            violations.append(f"Q{q['qno']}: 题面图不存在 {q_imgs[0]}")
            continue
        size = first_q.stat().st_size
        if size < 10 * 1024:
            violations.append(f"Q{q['qno']}: 题面图过小 ({size} bytes < 10KB)")
        for a_rel in _as_img_list(q.get("解析图")):
            a_img_path = REPO_ROOT / a_rel
            if not a_img_path.exists():
                violations.append(f"Q{q['qno']}: 解析图不存在 {a_rel}")
                break
    return violations


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--province", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--out", default="docs/superpowers/working/")
    ap.add_argument("--expected-min", type=int, default=18, help="期望最少题数（含）")
    ap.add_argument("--expected-max", type=int, default=25, help="期望最多题数（含）")
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument(
        "--relax-strict", action="store_true",
        help="跳过 strict-from-1 anchor 检查 (用于 PDF 中部分题号缺失的卷)",
    )
    args = ap.parse_args()

    qa = render_screenshots(
        Path(args.pdf),
        province=args.province,
        subject=args.subject,
        year=args.year,
        expected_max_qno=args.expected_max,
        dpi=args.dpi,
        relax_strict=args.relax_strict,
    )

    violations = assert_screenshot_quality(qa, (args.expected_min, args.expected_max))

    # 无论 L1 通过与否都 dump JSON（含 violations 字段供调试）
    qa["_violations"] = violations
    out_dir = REPO_ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = (
        out_dir / f"{args.province}-{args.subject}-{qa['paper_id']}-questions.json"
    )

    # merge: 重跑 screenshot 时保留已有 enrich/verify 字段，避免 LLM 数据丢失
    if out_path.exists():
        try:
            old_qa = json.loads(out_path.read_text(encoding="utf-8"))
            old_by_qno = {q["qno"]: q for q in old_qa.get("questions", [])}
            preserve_keys = (
                "answer", "solution_text", "summary", "tags", "difficulty",
                "verdict", "verdict_note", "enrich_error",
            )
            for q in qa["questions"]:
                old = old_by_qno.get(q["qno"])
                if not old:
                    continue
                for k in preserve_keys:
                    if k in old and old[k] not in (None, "", []):
                        q[k] = old[k]
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️  merge 失败 (旧 file 损坏？): {e}", file=sys.stderr)

    out_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")

    if violations:
        print("L1 断言失败:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        print(f"⚠️ 仍写入 questions.json 含 _violations 字段 → {out_path}", file=sys.stderr)
        return 1

    print(f"OK: 截图 {len(qa['questions'])} 题 + questions.json → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
