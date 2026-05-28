"""隔离实验：极简 1 页 HTML（正文段落 + 可选超宽公式 + 可选 _FIT_SCRIPT），
渲染成 PDF 后测正文段落字号，判定 ①溢出是否触发整体缩放 ②hbFit 是否在打印中生效。"""
import sys, subprocess
from pathlib import Path
import fitz
sys.path.insert(0, "00-元/scripts")
from gen_review_handbook import build_full_html, _FIT_SCRIPT, OUT_DIR

EDGE = r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"

# 正文段落 + 超宽 \text 反应链 放在【同一个 kp-zhuanti 块】（同页），复刻真实每考点布局
PARA = ('正文测量段落字号是否被整体缩放，基准应为十点七磅左右的小四号字。'
        'This is a normal body paragraph used to measure the rendered font size.')
# 足够长以确保渲染宽度 > A4纸宽(793px≈595pt)，复刻化学真实溢出
WIDEF = ('$' + r'\rightarrow'.join(
    r'\text{反应管硬质试管坩埚水蒸气检验无水CuSO4}' for _ in range(20)) + '$')

def make(name, with_wide, with_fit):
    inner = f'<p>{PARA}</p>' + (f'<p>{WIDEF}</p>' if with_wide else "")
    body = f'<div class="parent-group"><div class="kp-zhuanti">{inner}</div></div>'
    h = build_full_html("测试", body)
    if not with_fit:
        h = h.replace(_FIT_SCRIPT, "")
    p = OUT_DIR / f"_test_{name}.html"
    p.write_text(h, encoding="utf-8", newline="")
    return p

def render(html_path, pdf_path):
    cmd = [EDGE, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
           "--virtual-time-budget=20000", f"--print-to-pdf={pdf_path.resolve()}",
           html_path.resolve().as_uri()]
    subprocess.run(cmd, check=False, capture_output=True, timeout=120)

def probe(pdf_path):
    doc = fitz.open(str(pdf_path)); from collections import Counter; c = Counter()
    pw = doc[0].rect.width; maxx = 0
    for i in range(doc.page_count):
        for blk in doc[i].get_text("dict")["blocks"]:
            for ln in blk.get("lines", []):
                for sp in ln.get("spans", []):
                    maxx = max(maxx, sp["bbox"][2])
                    t = sp["text"].strip()
                    if any('一' <= ch <= '鿿' for ch in t) and len(t) >= 6:
                        c[round(sp["size"], 1)] += len(t)
    doc.close(); return doc.page_count if False else (c.most_common(2), round(pw, 1), round(maxx, 1))

for name, wide, fit in [("nowide", False, True), ("wide_nofit", True, False), ("wide_fit", True, True)]:
    hp = make(name, wide, fit)
    pp = OUT_DIR / f"_test_{name}.pdf"
    render(hp, pp)
    font, pw, maxx = probe(pp)
    print(f"{name:12} wide={wide} fit={fit}  pageW={pw}pt maxTextX={maxx}pt  bodyfont={font}")
