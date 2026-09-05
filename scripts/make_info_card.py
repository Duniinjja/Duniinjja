"""Monta o card estilo `neofetch` que fica ao lado do retrato.

O conteudo vem de data/profile.json (editavel sem tocar em Python); os numeros
do rodape vem de data/contributions.json, entao nunca ficam desatualizados.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "data" / "profile.json"
CONTRIB = ROOT / "data" / "contributions.json"
OUT = ROOT / "info-card.svg"

BG = "#0d1117"
STROKE = "#21262d"
DIM = "#7d8590"
FG = "#c9d1d9"
KEY = "#39d353"
BLUE = "#58a6ff"

WIDTH = 560
PAD = 18.0
FS = 11.5
CHAR_W = FS * 0.601  # largura do glifo na monoespacada
KEY_COL = 92.0
LINE_H = 19.0
MAX_VALUE_CHARS = int((WIDTH - PAD * 2 - KEY_COL) / CHAR_W)


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def wrap(text: str, limit: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split(" "):
        candidate = f"{cur} {word}".strip()
        if len(candidate) > limit and cur:
            lines.append(cur)
            cur = word
        else:
            cur = candidate
    if cur:
        lines.append(cur)
    return lines


def br(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def render() -> str:
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    stats = json.loads(CONTRIB.read_text(encoding="utf-8"))["stats"]

    # pre-calcula as linhas para saber a altura antes de desenhar
    body: list[tuple[str, str]] = []
    for key, value in profile["rows"]:
        for i, chunk in enumerate(wrap(value, MAX_VALUE_CHARS)):
            body.append((key if i == 0 else "", chunk))

    top = 34.0 + 26.0  # barra do terminal + respiro
    title_block = 34.0
    body_top = top + title_block
    lang_top = body_top + len(body) * LINE_H + 16.0
    kpi_top = lang_top + 44.0
    height = kpi_top + 76.0

    p: list[str] = []
    add = p.append
    add(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height:.0f}" '
        f'viewBox="0 0 {WIDTH} {height:.0f}" role="img" aria-label="Card de perfil">'
    )
    add(
        "<style>"
        "text{font-family:ui-monospace,'SFMono-Regular','JetBrains Mono',Consolas,monospace}"
        "@keyframes in{from{opacity:0;transform:translate(-10px,0)}to{opacity:1;transform:none}}"
        "@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
        ".r{animation:in .45s ease backwards}"
        ".bar{transform-box:fill-box;transform-origin:left center;animation:grow .7s cubic-bezier(.2,.8,.3,1) backwards}"
        "@media(prefers-reduced-motion:reduce){.r,.bar{animation:none}}"
        "</style>"
    )
    add(f'<rect width="{WIDTH}" height="{height:.0f}" rx="10" fill="{BG}" stroke="{STROKE}"/>')
    add(f'<line x1="0" y1="34" x2="{WIDTH}" y2="34" stroke="{STROKE}"/>')
    for i, color in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        add(f'<circle cx="{20 + i * 16}" cy="17" r="5" fill="{color}"/>')
    add(f'<text x="76" y="21" font-size="11" fill="{DIM}"><tspan fill="{KEY}">neofetch</tspan> --profile</text>')

    # titulo + regua
    add(
        f'<text class="r" x="{PAD}" y="{top + 12}" font-size="13.5" font-weight="700" fill="{KEY}">'
        f'{esc(profile["title"])}<tspan fill="{DIM}" font-weight="400">  {esc(profile["subtitle"])}</tspan></text>'
    )
    add(
        f'<text class="r" x="{PAD}" y="{top + 26}" font-size="11.5" fill="{STROKE}" '
        f'style="animation-delay:.06s">{"─" * int((WIDTH - PAD * 2) / CHAR_W)}</text>'
    )

    # linhas chave/valor
    for i, (key, value) in enumerate(body):
        y = body_top + i * LINE_H
        delay = 0.12 + i * 0.055
        if key:
            add(
                f'<text class="r" x="{PAD}" y="{y}" font-size="{FS}" fill="{KEY}" font-weight="600" '
                f'style="animation-delay:{delay:.2f}s">{esc(key)}<tspan fill="{DIM}" font-weight="400">:</tspan></text>'
            )
        add(
            f'<text class="r" x="{PAD + KEY_COL}" y="{y}" font-size="{FS}" fill="{FG}" '
            f'style="animation-delay:{delay + 0.02:.2f}s">{esc(value)}</text>'
        )

    # barra de linguagens
    langs = profile["languages"]
    total = sum(l[2] for l in langs) or 1
    bar_w = WIDTH - PAD * 2
    x = PAD
    add(f'<g><clipPath id="barclip"><rect x="{PAD}" y="{lang_top}" width="{bar_w}" height="8" rx="4"/></clipPath>')
    for i, (_, color, pct) in enumerate(langs):
        w = bar_w * pct / total
        add(
            f'<rect class="bar" x="{x:.1f}" y="{lang_top}" width="{w:.1f}" height="8" fill="{color}" '
            f'clip-path="url(#barclip)" style="animation-delay:{0.7 + i * 0.07:.2f}s"/>'
        )
        x += w
    add("</g>")

    legend_y = lang_top + 26
    lx = PAD
    for i, (name, color, pct) in enumerate(langs):
        add(
            f'<circle class="r" cx="{lx + 4:.1f}" cy="{legend_y - 4:.1f}" r="4" fill="{color}" '
            f'style="animation-delay:{1.0 + i * 0.06:.2f}s"/>'
        )
        label = f"{name} {pct}%"
        add(
            f'<text class="r" x="{lx + 13:.1f}" y="{legend_y}" font-size="10.5" fill="{DIM}" '
            f'style="animation-delay:{1.02 + i * 0.06:.2f}s">{esc(label)}</text>'
        )
        lx += 13 + len(label) * 6.3 + 14

    # tres KPIs com os numeros reais do calendario
    kpis = [
        (br(stats["total"]), "contribuições / ano"),
        (str(stats["current_streak"]), "dias seguidos"),
        (str(stats["best_day"]["count"]), "pico em um dia"),
    ]
    box_w = (WIDTH - PAD * 2 - 16) / 3
    for i, (value, label) in enumerate(kpis):
        bx = PAD + i * (box_w + 8)
        add(
            f'<g class="r" style="animation-delay:{1.3 + i * 0.1:.2f}s">'
            f'<rect x="{bx:.1f}" y="{kpi_top}" width="{box_w:.1f}" height="60" rx="8" '
            f'fill="#161b22" stroke="{STROKE}"/>'
            f'<text x="{bx + box_w / 2:.1f}" y="{kpi_top + 27}" text-anchor="middle" font-size="19" '
            f'font-weight="700" fill="{KEY}">{esc(value)}</text>'
            f'<text x="{bx + box_w / 2:.1f}" y="{kpi_top + 45}" text-anchor="middle" font-size="9.5" '
            f'fill="{DIM}">{esc(label)}</text></g>'
        )
    add("</svg>")
    return "".join(p)


if __name__ == "__main__":
    OUT.write_text(render(), encoding="utf-8")
    print(f"{OUT.name} -> {OUT.stat().st_size / 1024:.1f} KB")
