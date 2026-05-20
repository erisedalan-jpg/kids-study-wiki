"""打包学生 HTML 站 + 真题截图为 zip，方便其他设备分发。

输出 docs/吉林冲刺-学生包.zip。内部结构：
  吉林冲刺-学生包/
    docs/student/...
    素材/真题截图/吉林-{数学,物理,化学,生物}/...
    README.txt

解压后双击 docs/student/index.html 即用。

CLI：
  python 00-元/scripts/pack_student_zip.py            # 默认压缩输出
  python 00-元/scripts/pack_student_zip.py --no-compress  # 不压缩（PNG 本已压缩，快但同尺寸）
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, setup_utf8  # noqa: E402

TOP = "吉林冲刺-学生包"  # zip 内顶级目录名
INCLUDE_SUBJECTS = ["数学", "物理", "化学", "生物"]
OUT_ZIP = REPO_ROOT / "docs" / "吉林冲刺-学生包.zip"

README = """吉林冲刺·学生 HTML 离线包
===========================

【使用】
1. 解压本 zip
2. 进入文件夹 docs/student/
3. 双击 index.html（用 Chrome / Firefox / Edge 打开）

【内容】
- 4 科 weight ≥ 10 的核心词条 = 610 条
- 吉林历年真题题级页（含截图） = 1666 题
- KaTeX 离线公式渲染
- 移动端响应式（手机/平板友好）

【不含】
- 英语（长期训练非词条学习）
- 北京/湖南/黑龙江真题截图
- Obsidian 源 markdown / 教材 PDF

【若图片不显示】
- file:// 直接打开通常可加载图片
- 个别浏览器（如老 Safari）file:// 受限，可起本地 HTTP：
  cd docs/student && python -m http.server 8000
  然后浏览 http://localhost:8000 或局域网 IP

【更新】
源仓回到本机后跑：
  python 00-元/scripts/compute_weight.py --apply
  python 00-元/scripts/gen_html.py --apply --threshold 10
  python 00-元/scripts/pack_student_zip.py
"""


def add_dir(zf: zipfile.ZipFile, src_dir: Path, arc_prefix: str,
            label: str) -> tuple[int, int]:
    """递归把 src_dir 加入 zip，arcname 前缀 arc_prefix。返回 (文件数, 字节数)。"""
    n_files = 0
    total = 0
    for p in src_dir.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(src_dir).as_posix()
        arcname = f"{arc_prefix}/{rel}"
        zf.write(p, arcname)
        n_files += 1
        total += p.stat().st_size
        if n_files % 200 == 0:
            print(f"    [{label}] {n_files} 文件 / {total/1e6:.1f} MB", flush=True)
    return n_files, total


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-compress", action="store_true",
                    help="不压缩（PNG 本已压缩，DEFLATE 收益小但耗时多）")
    args = ap.parse_args()

    student_dir = REPO_ROOT / "docs" / "student"
    if not student_dir.is_dir():
        sys.exit("docs/student/ 不存在；先跑 gen_html.py --apply")

    OUT_ZIP.parent.mkdir(parents=True, exist_ok=True)
    if OUT_ZIP.exists():
        OUT_ZIP.unlink()

    comp = zipfile.ZIP_STORED if args.no_compress else zipfile.ZIP_DEFLATED
    print(f"打包 → {OUT_ZIP}  (模式: {'STORED' if args.no_compress else 'DEFLATED'})",
          flush=True)

    total_files = 0
    total_bytes = 0
    with zipfile.ZipFile(OUT_ZIP, "w", compression=comp, compresslevel=6) as zf:
        # docs/student/
        print("  → docs/student/", flush=True)
        n, b = add_dir(zf, student_dir, f"{TOP}/docs/student", "html")
        total_files += n; total_bytes += b

        # 素材/真题截图/吉林-{科}/
        for s in INCLUDE_SUBJECTS:
            shot_dir = REPO_ROOT / "素材" / "真题截图" / f"吉林-{s}"
            if not shot_dir.is_dir():
                print(f"  ⚠ skip {shot_dir.name}（目录不存在）")
                continue
            print(f"  → 素材/真题截图/吉林-{s}/", flush=True)
            n, b = add_dir(zf, shot_dir,
                           f"{TOP}/素材/真题截图/吉林-{s}", f"截图-{s}")
            total_files += n; total_bytes += b

        # README
        zf.writestr(f"{TOP}/README.txt", README.encode("utf-8"))
        total_files += 1

    zip_size = OUT_ZIP.stat().st_size
    print(f"\n完成：{total_files} 文件 / 源 {total_bytes/1e6:.0f} MB → "
          f"zip {zip_size/1e6:.0f} MB")
    print(f"输出：{OUT_ZIP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
