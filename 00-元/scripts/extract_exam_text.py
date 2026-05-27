"""P0：从解析卷 PDF 按题抽题干/解析文本，写回真题 md 的「## 题干文本」「## 解析文本」。

CLI:
  python extract_exam_text.py --province 吉林 --subject 数学            # dry-run
  python extract_exam_text.py --province 吉林 --subject 数学 --apply
  python extract_exam_text.py --province 吉林 --subject 数学 --apply --force  # 覆盖已抽
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pypdf

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, read_frontmatter, setup_utf8  # noqa: E402
from exam_text_segment import segment_by_qno  # noqa: E402

STEM_START, STEM_END = "<!-- 题干文本-start -->", "<!-- 题干文本-end -->"
SOL_START, SOL_END = "<!-- 解析文本-start -->", "<!-- 解析文本-end -->"
_BLOCK = "{s}\n## {title}\n{body}\n{e}"


def _sub_block(text: str, start: str, end: str, title: str, body: str) -> str:
    seg = _BLOCK.format(s=start, title=title, body=body, e=end)
    pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if start in text:
        return pat.sub(seg, text)
    # Also replace bare heading (no markers) — matches ## title up to next ## or EOF
    bare_pat = re.compile(
        r"^(## " + re.escape(title) + r")\n.*?(?=^##|\Z)", re.S | re.M
    )
    if bare_pat.search(text):
        return bare_pat.sub(seg + "\n\n", text).rstrip("\n") + "\n"
    return text.rstrip() + "\n\n" + seg + "\n"


def upsert_text_sections(md: str, *, stem: str, sol: str) -> str:
    md = _sub_block(md, STEM_START, STEM_END, "题干文本", stem)
    md = _sub_block(md, SOL_START, SOL_END, "解析文本", sol)
    return md


def read_pdf_page(pdf_rel: str, page: int) -> str:
    path = REPO_ROOT / pdf_rel
    reader = pypdf.PdfReader(str(path))
    if not (1 <= page <= len(reader.pages)):
        return ""
    return reader.pages[page - 1].extract_text() or ""


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--province", default="吉林")
    ap.add_argument("--subject", default="数学")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--force", action="store_true", help="覆盖已抽取的题")
    args = ap.parse_args()

    exam_dir = REPO_ROOT / "真题" / f"{args.province}-{args.subject}"
    paths = sorted(exam_dir.glob("*.md"))
    done = fail = skip = warn = 0
    fails: list[str] = []
    for p in paths:
        text = p.read_text(encoding="utf-8")
        if STEM_START in text and not args.force:
            skip += 1
            continue
        fm = read_frontmatter(p)
        pdf_rel, page, qno = fm.get("PDF"), fm.get("PDF页码"), fm.get("题号")
        if not (pdf_rel and page and qno):
            fail += 1
            fails.append(f"{p.name}: 缺 PDF/页码/题号")
            continue
        try:
            page_text = read_pdf_page(str(pdf_rel), int(page))
        except (OSError, ValueError, pypdf.errors.PyPdfError) as ex:
            fail += 1
            fails.append(f"{p.name}: PDF 读取失败 {ex}")
            continue
        seg = segment_by_qno(page_text, int(qno))
        if seg["fallback"]:
            warn += 1
            fails.append(f"{p.name}: 切分回退（整页入解析）")
        new = upsert_text_sections(text, stem=seg["题干"], sol=seg["解析"])
        if args.apply and new != text:
            p.write_text(new, encoding="utf-8")
        done += 1
    print(f"{'[APPLY]' if args.apply else '[dry-run]'} 处理 {done} / 跳过 {skip} / 失败 {fail} / 切分回退 {warn}"
          f"（{exam_dir.name}）")
    for f in fails[:40]:
        print("  ⚠", f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
