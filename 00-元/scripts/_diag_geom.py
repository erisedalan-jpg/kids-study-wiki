"""探针：真实 PDF 内容页几何。报告 每页 (主字号, 文本最左x0, 最右x1, 页宽)。
判定 7.1pt 是"整页缩放"(x0 也内移) 还是"纯小字"(x0 与基准同)。"""
import sys
from collections import Counter
import fitz

def page_geom(doc, i):
    c = Counter(); x0 = 9999; x1 = 0
    for blk in doc[i].get_text("dict")["blocks"]:
        for ln in blk.get("lines", []):
            for sp in ln.get("spans", []):
                t = sp["text"].strip()
                if len(t) >= 2:
                    x0 = min(x0, sp["bbox"][0]); x1 = max(x1, sp["bbox"][2])
                    if any('一' <= ch <= '鿿' for ch in t):
                        c[round(sp["size"], 1)] += len(t)
    dom = c.most_common(1)[0][0] if c else None
    return dom, round(x0, 1), round(x1, 1)

for p in sys.argv[1:]:
    doc = fitz.open(p); pw = round(doc[0].rect.width, 1)
    print(f"{p}  pageW={pw}pt")
    for i in range(30, 38):
        dom, x0, x1 = page_geom(doc, i)
        print(f"   p{i+1}: font={dom}pt  x0={x0}  x1={x1}")
    doc.close(); print()
