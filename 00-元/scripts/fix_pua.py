"""清理 PDF Symbol 字体 PUA 乱码 → 真 Unicode。

根因：pypdf 从 Adobe Symbol 字体提取的字符落在 PUA 区 U+F000–U+F0FF；
symbolCode = ord(ch) - 0xF000，按 Adobe Symbol 编码表映射为真 Unicode。

CLI:
  python fix_pua.py --subject 数学 [--province 吉林] [--apply]

  --apply     写盘（默认 dry-run，只统计）
  --province  省份；省略则扫所有省份
  --subject   学科（必填）
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

# ─── 工具基础 ─────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, setup_utf8  # noqa: E402

# ─── Adobe Symbol 字体编码表（低字节 → Unicode）───────────────────────────────
_SYMBOL: dict[int, str] = {
    0x20: " ", 0x21: "!", 0x23: "#", 0x25: "%", 0x26: "&",
    0x28: "(", 0x29: ")", 0x2B: "+", 0x2C: ",", 0x2D: "−",
    0x2E: ".", 0x2F: "/", 0x3A: ":", 0x3B: ";", 0x3C: "<",
    0x3D: "=", 0x3E: ">", 0x3F: "?", 0x5B: "[", 0x5D: "]",
    0x5F: "_", 0x7B: "{", 0x7D: "}",
    # 数字
    0x30: "0", 0x31: "1", 0x32: "2", 0x33: "3", 0x34: "4",
    0x35: "5", 0x36: "6", 0x37: "7", 0x38: "8", 0x39: "9",
    # 希腊大写
    0x41: "Α", 0x42: "Β", 0x43: "Χ", 0x44: "Δ", 0x45: "Ε",
    0x46: "Φ", 0x47: "Γ", 0x48: "Η", 0x49: "Ι", 0x4A: "ϑ",
    0x4B: "Κ", 0x4C: "Λ", 0x4D: "Μ", 0x4E: "Ν", 0x4F: "Ο",
    0x50: "Π", 0x51: "Θ", 0x52: "Ρ", 0x53: "Σ", 0x54: "Τ",
    0x55: "Υ", 0x56: "ς", 0x57: "Ω", 0x58: "Ξ", 0x59: "Ψ",
    0x5A: "Ζ",
    # 希腊小写
    0x61: "α", 0x62: "β", 0x63: "χ", 0x64: "δ", 0x65: "ε",
    0x66: "φ", 0x67: "γ", 0x68: "η", 0x69: "ι", 0x6A: "ϕ",
    0x6B: "κ", 0x6C: "λ", 0x6D: "μ", 0x6E: "ν", 0x6F: "ο",
    0x70: "π", 0x71: "θ", 0x72: "ρ", 0x73: "σ", 0x74: "τ",
    0x75: "υ", 0x76: "ϖ", 0x77: "ω", 0x78: "ξ", 0x79: "ψ",
    0x7A: "ζ",
    # 常用数学符号
    0xA2: "′", 0xA3: "≤", 0xA5: "∞", 0xAB: "↔", 0xAE: "→",
    0xB0: "°", 0xB1: "±", 0xB3: "≥", 0xB4: "×", 0xB6: "∂",
    0xB8: "÷", 0xB9: "≠", 0xBA: "≡", 0xBB: "≈", 0xBC: "…",
    0xC7: "∩", 0xC8: "∪", 0xCE: "∈", 0xCF: "∉", 0xD6: "√",
    0xDB: "⇐", 0xDE: "⇒", 0xE5: "∑", 0xF2: "∫",
}


def clean_pua(text: str) -> str:
    """将 PUA 区 U+F000–U+F0FF 按 Adobe Symbol 编码映射为真 Unicode。

    - 表内：精确映射
    - 不在表但低字节是可打印 ASCII（0x20–0x7E）：原样保留 ASCII 字符
    - 其余未知 PUA：丢弃
    幂等：已清理的文本再跑一次结果不变（不含 PUA 字符）。
    """
    out: list[str] = []
    for ch in text:
        o = ord(ch)
        if 0xF000 <= o <= 0xF0FF:
            low = o - 0xF000
            if low in _SYMBOL:
                out.append(_SYMBOL[low])
            elif 0x20 <= low <= 0x7E:
                out.append(chr(low))
            # else: 未知 PUA → 丢弃
        else:
            out.append(ch)
    return "".join(out)


def _has_pua(text: str) -> bool:
    return any(0xF000 <= ord(c) <= 0xF0FF for c in text)


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser(description="清理真题 md 中的 PDF Symbol PUA 乱码")
    ap.add_argument("--subject", required=True, help="学科，如 数学")
    ap.add_argument("--province", default=None, help="省份（省略则扫所有省份）")
    ap.add_argument("--apply", action="store_true", help="写盘（默认 dry-run）")
    args = ap.parse_args()

    zhen_ti_dir = REPO_ROOT / "真题"
    if not zhen_ti_dir.is_dir():
        print("错误：找不到 真题/ 目录", file=sys.stderr)
        return 1

    # 收集目标目录
    if args.province:
        dirs = [zhen_ti_dir / f"{args.province}-{args.subject}"]
    else:
        dirs = sorted(
            d for d in zhen_ti_dir.iterdir()
            if d.is_dir() and d.name.endswith(f"-{args.subject}")
        )

    n_changed = 0
    for d in dirs:
        if not d.is_dir():
            print(f"  跳过（目录不存在）：{d.name}", file=sys.stderr)
            continue
        for p in sorted(d.glob("*.md")):
            try:
                text = p.read_text(encoding="utf-8")
            except OSError as e:
                print(f"  ⚠ 读取失败 {p.name}: {e}", file=sys.stderr)
                continue
            if not _has_pua(text):
                continue
            cleaned = clean_pua(text)
            n_changed += 1
            if args.apply:
                p.write_text(cleaned, encoding="utf-8")

    label = "[APPLY]" if args.apply else "[dry-run]"
    print(f"{label} 清理 {n_changed} 文件（--subject {args.subject}"
          + (f" --province {args.province}" if args.province else "，全省份")
          + "）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
