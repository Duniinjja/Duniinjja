"""Converte a foto preparada em um retrato ASCII que se digita sozinho.

Duas decisoes que separam um retrato limpo de ruido:
  - monocromatico (colorir cada caractere vira estatica de TV);
  - rampa alinhada ao FUNDO: sobre preto, denso = brilhante, entao claro->denso.
    Inverter isso imprime o retrato em negativo.

A animacao e' SMIL (<animate>), que o GitHub roda dentro de <img>. O estado
NATURAL do clip e' 'aberto': se a animacao nao rodar, o retrato aparece
inteiro em vez de sumir.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "source-prepped.png"
OUT = ROOT / "ascii-portrait.svg"

RAMP = " .`:-=+*csS#%@"  # escuro (esparso) -> claro (denso), porque o fundo e' escuro
COLS = 76
CHAR_W = 6.0
LINE_H = 10.0
FONT_SIZE = 10.0
INK = "#c9d1d9"
BG = "#0d1117"
STROKE = "#21262d"
ACCENT = "#39d353"


def to_rows(cols: int) -> list[str]:
    im = Image.open(SRC).convert("L")
    rows = max(1, int(round(cols * im.height / im.width * (CHAR_W / LINE_H))))
    small = np.asarray(im.resize((cols, rows), Image.LANCZOS), dtype=np.float64) / 255.0
    idx = np.clip((small * (len(RAMP) - 1)).round().astype(int), 0, len(RAMP) - 1)
    return trim(["".join(RAMP[i] for i in row) for row in idx])


def trim(rows: list[str]) -> list[str]:
    """Corta a moldura vazia que a mascara eliptica deixa em volta do rosto."""
    while rows and not rows[0].strip():
        rows.pop(0)
    while rows and not rows[-1].strip():
        rows.pop()
    left = min((len(r) - len(r.lstrip()) for r in rows if r.strip()), default=0)
    return [r[left:].rstrip() for r in rows]


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(rows: list[str]) -> str:
    art_w = max(len(r) for r in rows) * CHAR_W
    pad_x, pad_top, pad_bottom = 16.0, 44.0, 16.0
    width = art_w + pad_x * 2
    height = pad_top + len(rows) * LINE_H + pad_bottom
    per_line, dur = 0.042, 0.34

    p: list[str] = []
    add = p.append
    add(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-label="Retrato em ASCII">'
    )
    add(
        "<style>"
        "text{font-family:ui-monospace,'SFMono-Regular','JetBrains Mono',Consolas,monospace;"
        "white-space:pre;font-size:%.0fpx}" % FONT_SIZE
        + "</style>"
    )
    add(f'<rect width="{width:.0f}" height="{height:.0f}" rx="10" fill="{BG}" stroke="{STROKE}"/>')
    add(f'<line x1="0" y1="34" x2="{width:.0f}" y2="34" stroke="{STROKE}"/>')
    for i, color in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        add(f'<circle cx="{20 + i * 16}" cy="17" r="5" fill="{color}"/>')
    add(
        f'<text x="76" y="21" font-size="11" fill="#7d8590">'
        f'<tspan fill="{ACCENT}">whoami</tspan> --render=ascii</text>'
    )

    # um clip por linha: a mascara "abre" da esquerda para a direita
    add("<defs>")
    for i in range(len(rows)):
        y = pad_top + i * LINE_H - LINE_H
        # Um unico <animate> com values/keyTimes: segura a mascara fechada durante o
        # atraso e so' entao abre. Com 'begin', o SMIL manteria o valor BASE ate' o
        # inicio -- a linha apareceria inteira e depois piscaria ao ser revelada.
        # O valor base continua sendo a largura cheia, entao sem SMIL tudo aparece.
        delay = i * per_line
        total = delay + dur
        hold = delay / total
        add(
            f'<clipPath id="w{i}"><rect x="{pad_x}" y="{y:.1f}" width="{art_w:.0f}" '
            f'height="{LINE_H + 2:.0f}">'
            f'<animate attributeName="width" values="0;0;{art_w:.0f}" '
            f'keyTimes="0;{hold:.4f};1" dur="{total:.2f}s" fill="freeze"/></rect></clipPath>'
        )
    add("</defs>")

    add(f'<g fill="{INK}">')
    for i, row in enumerate(rows):
        y = pad_top + i * LINE_H
        add(f'<text x="{pad_x}" y="{y:.1f}" clip-path="url(#w{i})">{esc(row)}</text>')
    add("</g>")

    # cursor que corre na borda do wipe; nasce invisivel, entao some se o SMIL nao rodar
    for i in range(len(rows)):
        y = pad_top + i * LINE_H - LINE_H + 1
        add(
            f'<rect x="{pad_x}" y="{y:.1f}" width="{CHAR_W:.0f}" height="{LINE_H:.0f}" '
            f'fill="{ACCENT}" opacity="0">'
            f'<animate attributeName="opacity" values="0;.85;.85;0" keyTimes="0;.06;.94;1" '
            f'begin="{i * per_line:.2f}s" dur="{dur}s"/>'
            f'<animate attributeName="x" from="{pad_x}" to="{pad_x + art_w:.0f}" '
            f'begin="{i * per_line:.2f}s" dur="{dur}s"/></rect>'
        )
    add("</svg>")
    return "".join(p)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true", help="imprime o ASCII no terminal")
    ap.add_argument("--cols", type=int, default=COLS)
    args = ap.parse_args()
    COLS = args.cols
    rows = to_rows(COLS)
    if args.preview:
        print("\n".join(rows))
    else:
        OUT.write_text(render(rows), encoding="utf-8")
        print(f"{OUT.name} -> {len(rows)} linhas x {COLS} colunas, {OUT.stat().st_size / 1024:.1f} KB")
