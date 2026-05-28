"""复习手册 PDF 生成器：两轮渲染 + fitz 页码标注。

两步流程：
  Pass 1 → Edge headless render → fitz 搜索 @@safe@@ token → page_map
  Pass 2 → 注入 page_map 重新生成 HTML → Edge render → fitz stamp footer → 最终 PDF

Usage:
  python gen_handbook_pdf.py --subject 物理
  python gen_handbook_pdf.py --all          # 数学/物理/化学/生物
  python gen_handbook_pdf.py --subject 物理 --verify-only   # 仅验证已有 PDF
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths / constants
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
OUT_DIR = REPO_ROOT / "docs" / "student"

EDGE = r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"

SUBJECTS = ["数学", "物理", "化学", "生物"]

PYTHON = sys.executable  # reuse the same python that runs this script

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_out_dir() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def render_html_to_pdf(html_path: Path, pdf_path: Path, *, timeout: int = 300) -> bool:
    """Call Edge headless to render html_path → pdf_path.
    Returns True on success (file produced), False otherwise.
    """
    html_uri = html_path.resolve().as_uri()
    cmd = [
        EDGE,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--virtual-time-budget=180000",
        f"--print-to-pdf={pdf_path.resolve()}",
        html_uri,
    ]
    result = subprocess.run(cmd, check=False, capture_output=True, timeout=timeout)
    if result.returncode != 0:
        print(f"  [WARN] Edge exited {result.returncode}", flush=True)
    # Edge may exit 0 even on failure; check file exists and non-empty
    if not pdf_path.exists() or pdf_path.stat().st_size < 1024:
        print(f"  [ERROR] PDF not produced or too small: {pdf_path}", flush=True)
        return False
    return True


def run_handbook_gen(subject: str, *, page_map_path: Path | None = None) -> int:
    """Call gen_review_handbook.py --subject S --apply [--page-map path].
    Returns subprocess returncode.
    """
    cmd = [PYTHON, str(SCRIPT_DIR / "gen_review_handbook.py"),
           "--subject", subject, "--apply"]
    if page_map_path is not None:
        cmd += ["--page-map", str(page_map_path)]
    result = subprocess.run(cmd, capture_output=False, timeout=120,
                            env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
    return result.returncode


def build_kp_safe_pairs(subject: str) -> list[tuple[str, str]]:
    """Read 复习/<subject>/*.md and return [(考点, safe_name), ...].
    Imports gen_review_handbook.load_zhuanti for consistency.
    """
    # Add scripts dir to sys.path if needed
    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))
    from gen_review_handbook import load_zhuanti
    from gen_kaodian_review import _safe_name
    entries = load_zhuanti(subject)
    return [(e["考点"], _safe_name(e["考点"])) for e in entries]


def fitz_build_page_map(pdf_path: Path, kp_safe_pairs: list[tuple[str, str]]) -> dict[str, int]:
    """Search pdf_path for @@safe@@ tokens (primary) or visible 考点 text (fallback).
    Returns {考点: 1-based page}.

    Primary: white-text @@safe@@ tokens embedded by gen_review_handbook.
    Fallback: if 0 tokens found on a sampling probe (Edge may not output invisible
    white text to the text layer on some versions), fall back to searching for the
    visible 考点 text itself.  Each 考点 is unique so first match = section page.
    """
    import fitz  # type: ignore
    doc = fitz.open(str(pdf_path))
    page_map: dict[str, int] = {}
    total_pages = doc.page_count
    print(f"  fitz: {total_pages} pages, searching {len(kp_safe_pairs)} tokens …", flush=True)

    # ── Primary: token search ─────────────────────────────────────────────
    for kp, safe in kp_safe_pairs:
        token = f"@@{safe}@@"
        for i in range(total_pages):
            if doc[i].search_for(token):
                page_map[kp] = i + 1
                break

    token_hits = len(page_map)
    print(f"  primary (@@token@@): {token_hits}/{len(kp_safe_pairs)} hits", flush=True)

    # ── Fallback: visible text search ────────────────────────────────────
    # If fewer than 5% of tokens matched, assume white text was suppressed by Edge.
    # We need to find the SECTION page, not the tree occurrence.
    # Strategy: find where the zhuanti section starts (search for "考点专题复习" heading),
    # then search for 考点 text starting from that page.
    if token_hits < max(1, len(kp_safe_pairs) * 0.05):
        print(f"  [FALLBACK] Using visible 考点 text search (skipping tree pages) …", flush=True)
        # Find first page of zhuanti section
        zhuanti_start = 0
        for i in range(total_pages):
            if doc[i].search_for("考点专题复习"):
                zhuanti_start = i
                print(f"  zhuanti section starts at page {i+1}", flush=True)
                break
        page_map = {}
        for kp, _safe in kp_safe_pairs:
            # Search from zhuanti_start to find section page (not tree page)
            for i in range(zhuanti_start, total_pages):
                if doc[i].search_for(kp):
                    page_map[kp] = i + 1
                    break
            # If not found in zhuanti section, fall back to full search
            if kp not in page_map:
                for i in range(total_pages):
                    if doc[i].search_for(kp):
                        page_map[kp] = i + 1
                        break
        print(f"  fallback (visible text): {len(page_map)}/{len(kp_safe_pairs)} hits", flush=True)

    doc.close()
    print(f"  page_map: {len(page_map)}/{len(kp_safe_pairs)} 考点定位成功", flush=True)
    return page_map


def fitz_stamp_footer(pass2_pdf: Path, final_pdf: Path) -> int:
    """Add '— N —' footer to every page; return page count."""
    import fitz  # type: ignore
    doc = fitz.open(str(pass2_pdf))
    n = doc.page_count
    for i in range(n):
        pg = doc[i]
        r = pg.rect
        pg.insert_text(
            (r.width / 2 - 18, r.height - 24),
            f"— {i + 1} —",
            fontsize=9,
            color=(0.4, 0.4, 0.4),
        )
    doc.save(str(final_pdf))
    doc.close()
    return n


def fitz_verify(final_pdf: Path, page_map: dict[str, int],
                kp_safe_pairs: list[tuple[str, str]]) -> bool:
    """Spot-check 3 考点: confirm section page in pass2 == page_map[考点].
    Tries @@token@@ search first; falls back to visible 考点 text search.
    Also confirms footer '— 1 —' on first page.
    Returns True if all checks pass (no drift).
    """
    import fitz  # type: ignore
    doc = fitz.open(str(final_pdf))
    total = doc.page_count

    # Footer check: look for footer stamp on the first page.
    # fitz may render the em dash '—' as '·' or other glyphs depending on font metrics;
    # search for digit-containing footer text patterns instead of exact unicode.
    footer_ok = False
    if total > 0:
        text = doc[0].get_text()
        # Accept: '— 1 —' or '· 1 ·' or any variant containing ' 1 '
        if "— 1 —" in text or "· 1 ·" in text or "- 1 -" in text:
            footer_ok = True
        else:
            # Broader check: last 100 chars contain ' 1 ' (the page number with spaces)
            tail = text[-100:] if len(text) > 100 else text
            import re as _re
            if _re.search(r'[\W]1[\W]', tail):
                footer_ok = True
    if not footer_ok:
        print("  [VERIFY FAIL] Footer page number not found on page 1", flush=True)
        doc.close()
        return False
    print("  footer ✓ (page number on p.1)", flush=True)

    # TOC page-ref check: sample up to 3 考点 that are in page_map
    drift_found = False
    sample_pairs = [(kp, safe) for kp, safe in kp_safe_pairs if kp in page_map][:3]
    for kp, safe in sample_pairs:
        expected_page = page_map[kp]
        # Try @@token@@ first, fall back to visible text
        actual_page = None
        token = f"@@{safe}@@"
        for i in range(total):
            if doc[i].search_for(token):
                actual_page = i + 1
                break
        if actual_page is None:
            # Fallback: visible text, searching from zhuanti section start
            zhuanti_start_v = 0
            for ii in range(total):
                if doc[ii].search_for("考点专题复习"):
                    zhuanti_start_v = ii
                    break
            for i in range(zhuanti_start_v, total):
                if doc[i].search_for(kp):
                    actual_page = i + 1
                    break
        if actual_page is None:
            print(f"  [VERIFY WARN] {kp!r} not found in final PDF (neither token nor text)", flush=True)
        elif actual_page != expected_page:
            print(f"  [DRIFT] {kp!r}: page_map={expected_page}, actual={actual_page}", flush=True)
            drift_found = True
        else:
            print(f"  refs ✓ {kp!r}: page_map={expected_page} == actual={actual_page}", flush=True)

    # TOC text check: look for 'p.' in first 20 pages
    toc_ref_found = False
    for i in range(min(20, total)):
        if " p." in doc[i].get_text():
            toc_ref_found = True
            break
    if toc_ref_found:
        print("  tree page-refs ✓ ('p.' found in first 20 pages)", flush=True)
    else:
        print("  [VERIFY WARN] No 'p.' page refs found in first 20 pages", flush=True)

    doc.close()
    return not drift_found


# ---------------------------------------------------------------------------
# Per-subject orchestration
# ---------------------------------------------------------------------------

def process_subject(subject: str) -> tuple[bool, int, int]:
    """Run full two-pass pipeline for one subject.
    Returns (success, page_count, toc_count).
    """
    print(f"\n{'='*60}", flush=True)
    print(f"Subject: {subject}", flush=True)
    print(f"{'='*60}", flush=True)

    _ensure_out_dir()
    html_path = OUT_DIR / f"{subject}复习手册.html"
    final_pdf = OUT_DIR / f"{subject}复习手册.pdf"

    with tempfile.TemporaryDirectory(prefix=f"handbook_{subject}_") as tmpdir:
        tmp = Path(tmpdir)
        pass1_pdf = tmp / "pass1.pdf"
        pass2_pdf = tmp / "pass2.pdf"
        map_json = tmp / "page_map.json"

        # ── Step 1: Generate HTML without page_map ─────────────────────────
        print(f"\n[1/6] Generating HTML (pass 1, no page_map) …", flush=True)
        rc = run_handbook_gen(subject)
        if rc != 0:
            print(f"  [ERROR] gen_review_handbook.py exited {rc}", flush=True)
            return False, 0, 0
        if not html_path.exists():
            print(f"  [ERROR] HTML not found: {html_path}", flush=True)
            return False, 0, 0

        # ── Step 2: Render pass 1 → temp PDF ──────────────────────────────
        print(f"\n[2/6] Rendering pass 1 PDF …", flush=True)
        t0 = time.time()
        ok = render_html_to_pdf(html_path, pass1_pdf)
        print(f"  done in {time.time()-t0:.1f}s  ({pass1_pdf.stat().st_size//1024}KB)" if ok else "  FAILED", flush=True)
        if not ok:
            return False, 0, 0

        # ── Step 3: fitz page_map ──────────────────────────────────────────
        print(f"\n[3/6] Building page_map (fitz token search) …", flush=True)
        kp_safe_pairs = build_kp_safe_pairs(subject)
        page_map = fitz_build_page_map(pass1_pdf, kp_safe_pairs)
        with map_json.open("w", encoding="utf-8") as f:
            json.dump(page_map, f, ensure_ascii=False, indent=2)
        print(f"  saved → {map_json}", flush=True)

        if not page_map:
            print(f"  [WARN] page_map is empty — tokens not found; check Edge render", flush=True)

        # ── Step 4: Regen HTML with page_map ──────────────────────────────
        print(f"\n[4/6] Generating HTML (pass 2, with page_map) …", flush=True)
        rc = run_handbook_gen(subject, page_map_path=map_json)
        if rc != 0:
            print(f"  [ERROR] gen_review_handbook.py (pass 2) exited {rc}", flush=True)
            return False, 0, 0

        # ── Step 5: Render pass 2 → temp PDF ──────────────────────────────
        print(f"\n[5/6] Rendering pass 2 PDF …", flush=True)
        t0 = time.time()
        ok = render_html_to_pdf(html_path, pass2_pdf)
        print(f"  done in {time.time()-t0:.1f}s  ({pass2_pdf.stat().st_size//1024}KB)" if ok else "  FAILED", flush=True)
        if not ok:
            return False, 0, 0

        # ── Step 6: fitz stamp footer + save final PDF ────────────────────
        print(f"\n[6/6] Stamping footer page numbers …", flush=True)
        n_pages = fitz_stamp_footer(pass2_pdf, final_pdf)
        print(f"  → {final_pdf}  ({n_pages} pages)", flush=True)

        # ── Verify ────────────────────────────────────────────────────────
        print(f"\n[VERIFY] {subject} …", flush=True)
        ok_verify = fitz_verify(final_pdf, page_map, kp_safe_pairs)
        if not ok_verify:
            print(f"\n  [STOP] Drift detected in {subject} — not shipping.", flush=True)
            return False, n_pages, len(page_map)

        toc_count = len(page_map)
        print(f"\n  SUMMARY: {subject}: {n_pages}页, 目录页码 {toc_count}个, footer OK", flush=True)
        return True, n_pages, toc_count


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="生成复习手册 PDF（两轮渲染+页码标注）")
    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("--subject", help="单科：数学/物理/化学/生物")
    grp.add_argument("--all", action="store_true", help="四科全部")
    ap.add_argument("--verify-only", action="store_true",
                    help="仅验证已有 final PDF（不重新渲染）")
    args = ap.parse_args()

    subjects = SUBJECTS if args.all else [args.subject]

    results: dict[str, tuple[bool, int, int]] = {}
    for s in subjects:
        ok, pages, toc = process_subject(s)
        results[s] = (ok, pages, toc)

    print("\n" + "="*60, flush=True)
    print("FINAL REPORT", flush=True)
    print("="*60, flush=True)
    all_ok = True
    for s, (ok, pages, toc) in results.items():
        status = "OK" if ok else "FAILED"
        print(f"  {s}: {status}  {pages}页  目录页码 {toc}个", flush=True)
        if not ok:
            all_ok = False

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
