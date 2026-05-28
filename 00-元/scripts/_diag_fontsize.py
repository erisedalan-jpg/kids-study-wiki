"""探针：统计 PDF 正文文字字号分布（top 频次），对比各科是否被整体缩放。
用法: python _diag_fontsize.py <pdf1> [pdf2 ...]
只吐小统计，不打印正文。"""
import sys
from collections import Counter
import fitz  # PyMuPDF

def probe(pdf_path, lo=30, hi=55):
    doc = fitz.open(pdf_path)
    n = doc.page_count
    sizes = Counter()
    for i in range(min(lo, n), min(hi, n)):
        d = doc[i].get_text("dict")
        for blk in d.get("blocks", []):
            for ln in blk.get("lines", []):
                for sp in ln.get("spans", []):
                    t = sp.get("text", "").strip()
                    if len(t) >= 4:  # 跳过短碎片
                        sizes[round(sp["size"], 1)] += len(t)
    doc.close()
    return n, sizes

for p in sys.argv[1:]:
    n, sizes = probe(p)
    top = sizes.most_common(6)
    print(f"{p}  pages={n}")
    for sz, cnt in top:
        print(f"    {sz:>5}pt  chars={cnt}")
    print()
