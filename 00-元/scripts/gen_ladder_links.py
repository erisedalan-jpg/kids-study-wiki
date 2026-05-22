"""按 strand_map YAML 向词条 `## 🔗 相关词条` 段注入「前置/延伸」双向链。

YAML schema（strand_map_数学小学.yaml）:
  edges:
    "016-加法":   {strand: 数与运算, 前置: [], 延伸: ["030-乘法"]}
    "030-乘法":   {strand: 数与运算, 前置: ["016-加法"], 延伸: ["050-乘方"]}
显式声明的 延伸 会自动在目标处回填对应 前置（build_reciprocal）。

CLI:
  python 00-元/scripts/gen_ladder_links.py --map strand_map_数学小学.yaml --dir 数学 --dry
  python 00-元/scripts/gen_ladder_links.py --map strand_map_数学小学.yaml --dir 数学 --apply
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, setup_utf8  # noqa: E402

SECTION_HEADER = "## 🔗 相关词条"


def _bare(stem: str) -> str:
    return re.sub(r"^\d{2,4}-", "", stem)


def _fmt(items: list[tuple[str, str]]) -> str:
    return " ".join(f"[[{stem}|{disp}]]" for stem, disp in items)


def build_reciprocal(edges: dict[str, dict]) -> dict[str, dict]:
    """据每条 延伸 边回填目标的 前置；返回补全后的 edges（含新键）。"""
    out: dict[str, dict] = {
        s: {"前置": list(v.get("前置", [])), "延伸": list(v.get("延伸", []))}
        for s, v in edges.items()
    }
    for src, v in edges.items():
        for dst in v.get("延伸", []):
            out.setdefault(dst, {"前置": [], "延伸": []})
            if src not in out[dst]["前置"]:
                out[dst]["前置"].append(src)
        for dst in v.get("前置", []):
            out.setdefault(dst, {"前置": [], "延伸": []})
            if src not in out[dst]["延伸"]:
                out[dst]["延伸"].append(src)
    return out


def _block(前置: list[tuple[str, str]], 延伸: list[tuple[str, str]]) -> str:
    lines = [SECTION_HEADER, ""]
    if 前置:
        lines.append(f"- **前置**：{_fmt(前置)}")
    if 延伸:
        lines.append(f"- **延伸**：{_fmt(延伸)}")
    if not 前置 and not 延伸:
        lines.append("🚧")
    lines.append("")
    return "\n".join(lines)


def inject_links(
    text: str,
    前置: list[tuple[str, str]],
    延伸: list[tuple[str, str]],
) -> str:
    """替换/新建 🔗 相关词条 段。"""
    block = _block(前置, 延伸)
    m = re.search(re.escape(SECTION_HEADER), text)
    if m:
        rest = text[m.end():]
        nxt = re.search(r"^##\s", rest, re.MULTILINE)
        end = m.end() + (nxt.start() if nxt else len(rest))
        return text[: m.start()] + block + ("\n" if not text[end:].startswith("\n") else "") + text[end:]
    sep = "" if text.endswith("\n") else "\n"
    return text + sep + "\n" + block


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", required=True, help="strand_map YAML 文件名（位于 scripts/）")
    ap.add_argument("--dir", required=True, help="学科目录")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    map_path = Path(__file__).parent / args.map
    cfg = yaml.safe_load(map_path.read_text(encoding="utf-8"))
    edges = build_reciprocal(cfg.get("edges", {}))

    base = REPO_ROOT / args.dir
    stem_to_path = {p.stem: p for p in base.glob("*.md")}
    disp = {stem: _bare(stem) for stem in stem_to_path}

    n_write = 0
    for stem, v in edges.items():
        p = stem_to_path.get(stem)
        if not p:
            print(f"  ⚠ map 中 {stem} 无对应词条文件，跳过")
            continue
        前置 = [(s, disp.get(s, _bare(s))) for s in v["前置"]]
        延伸 = [(s, disp.get(s, _bare(s))) for s in v["延伸"]]
        text = p.read_text(encoding="utf-8")
        new = inject_links(text, 前置, 延伸)
        if new != text:
            print(f"  🔗 {p.name}: 前置{len(前置)} 延伸{len(延伸)}")
            if args.apply:
                p.write_text(new, encoding="utf-8", newline="")
                n_write += 1
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"\n[{mode}] 注入 {len(edges)} 词条 / 写盘 {n_write}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
