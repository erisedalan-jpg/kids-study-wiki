"""PDF 内容比对：抽全文 → 归一化 → SequenceMatcher.ratio。

用途：扩省份前判同卷。**不要看文件名**——同卷在不同下载站的 PDF 二进制
MD5/水印/页眉页脚常不同，但归一化后文本 ratio=1.0000 即逐字符同卷，
应仅写「同卷说明」而非建镜像目录。

默认对比目录：`素材/真题/吉林/2008-2024·（吉林）<学科>高考真题` vs
`素材/真题/黑龙江/2008-2024·（黑龙江）<学科>高考真题`（最初 case）。
用 `--dir-a` / `--dir-b` 切换其他省份对（接绝对或仓内相对路径）。

判定阈值：
- ratio ≥ .995  → 同卷
- .97 - .995   → 近似（建议人工核）
- < .97        → 实质差异（独立卷，进 5 步真题管线入库）
"""
import sys, os, re, argparse, difflib
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
from pathlib import Path
import fitz  # PyMuPDF

REPO = Path(__file__).resolve().parents[2]
DEFAULT_BASE = REPO / "素材/真题"
SUBJECTS = ["数学", "物理", "化学", "生物", "英语"]

# 常见下载站水印 / 页眉页脚噪声（剥离后再比，避免误判来源差异为命题差异）
NOISE = [
    r'学科网[（(].*?[)）]?', r'www\.[a-zA-Z0-9./?=_-]+', r'http[s]?://\S+',
    r'[一-龥]{0,6}(网校|组卷|教育网|资源网|题库)', r'扫描全能王', r'CamScanner',
    r'第\s*\d+\s*页', r'共\s*\d+\s*页', r'第[一二三四五六七八九十]+页',
    r'绝密.{0,8}启用前', r'本卷.{0,20}', r'\b\d{6,}\b', r'[A-Za-z0-9_]+@[A-Za-z0-9_.]+',
]
NOISE_RE = [re.compile(p) for p in NOISE]


def extract(pdf: Path) -> str:
    try:
        doc = fitz.open(pdf)
    except Exception as e:
        return f"<<OPEN_FAIL:{e}>>"
    parts = []
    for pg in doc:
        parts.append(pg.get_text())
    doc.close()
    return "\n".join(parts)


def normalize(t: str) -> str:
    for r in NOISE_RE:
        t = r.sub('', t)
    # 去所有空白 + 统一标点宽窄
    t = re.sub(r'\s+', '', t)
    trans = str.maketrans('（）；，：？！．、', '();,:?!.,')
    t = t.translate(trans)
    return t


def cmp_pair(a: Path, b: Path):
    ta, tb = normalize(extract(a)), normalize(extract(b))
    if ta.startswith("<<OPEN_FAIL") or tb.startswith("<<OPEN_FAIL"):
        return None, ta if ta.startswith("<<") else tb, len(ta), len(tb)
    ratio = difflib.SequenceMatcher(None, ta, tb, autojunk=False).ratio()
    return ratio, None, len(ta), len(tb)


def resolve_dir(p: str) -> Path:
    """支持仓内相对路径与绝对路径。"""
    pp = Path(p)
    return pp if pp.is_absolute() else REPO / pp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--subject', help='只跑单学科')
    ap.add_argument('--only', help='文件名子串过滤(如 2022 解析)')
    ap.add_argument('--dir-a', help='省 A 目录（含 {subject} 占位符则按学科展开；默认 素材/真题/吉林/2008-2024·（吉林）{subject}高考真题）')
    ap.add_argument('--dir-b', help='省 B 目录（同上；默认 黑龙江版）')
    ap.add_argument('--show-diff', action='store_true', help='ratio<0.97 时输出差异片段')
    args = ap.parse_args()

    pat_a = args.dir_a or "素材/真题/吉林/2008-2024·（吉林）{subject}高考真题"
    pat_b = args.dir_b or "素材/真题/黑龙江/2008-2024·（黑龙江）{subject}高考真题"

    subs = [args.subject] if args.subject else SUBJECTS
    rows = []
    for s in subs:
        jd = resolve_dir(pat_a.format(subject=s))
        hd = resolve_dir(pat_b.format(subject=s))
        if not jd.exists() or not hd.exists():
            print(f"[skip] {s}: 目录缺失 (a={jd} b={hd})")
            continue
        for jf in sorted(jd.glob("*.pdf")):
            bn = jf.name
            if args.only and not all(k in bn for k in args.only.split()):
                continue
            hf = hd / bn
            if not hf.exists():
                rows.append((s, bn, None, "缺对", 0, 0))
                continue
            ratio, err, la, lb = cmp_pair(jf, hf)
            rows.append((s, bn, ratio, err, la, lb))

    print(f"{'学科':<4} {'ratio':>6}  {'A_len':>7} {'B_len':>7}  文件")
    buckets = {'同(≥.995)': 0, '近(.97-.995)': 0, '异(<.97)': 0, '错误': 0}
    for s, bn, r, err, la, lb in rows:
        if err:
            buckets['错误'] += 1
            print(f"{s:<4} {'ERR':>6}  {err}  {bn}")
            continue
        tag = '同(≥.995)' if r >= 0.995 else ('近(.97-.995)' if r >= 0.97 else '异(<.97)')
        buckets[tag] += 1
        flag = '' if r >= 0.97 else '  <<<实质差异?'
        print(f"{s:<4} {r:6.4f}  {la:7d} {lb:7d}  {bn}{flag}")
    print("\n=== 汇总 ===")
    for k, v in buckets.items():
        print(f"  {k}: {v}")
    print(f"  合计对数: {sum(buckets.values())}")


if __name__ == '__main__':
    main()
