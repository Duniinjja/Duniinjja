"""Desenha data/contributions.json como um heatmap SVG animado.

A animacao e' CSS keyframes embutido no proprio SVG: o GitHub renderiza SVG
via <img> e roda a animacao, mas remove <script> e CSS externo.
Regra de ouro: o estado NATURAL do elemento e' o estado FINAL (visivel).
A animacao usa fill-mode backwards, entao se ela nao rodar (leitor estatico,
prefers-reduced-motion) o desenho aparece completo em vez de sumir.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "contributions.json"
OUT = ROOT / "contrib-heatmap.svg"

BG = "#0d1117"
PANEL = "#0d1117"
STROKE = "#21262d"
DIM = "#7d8590"
FG = "#c9d1d9"
ACCENT = "#39d353"
EMPTY = "#161b22"
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#7ef7a8"]

CELL = 12
GAP = 3
STEP = CELL + GAP
PAD_LEFT = 40
PAD_RIGHT = 28
WIDTH = 860
GRID_TOP = 74
MONTHS_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def br(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def build_grid(days: list[dict]) -> list[dict]:
    first = datetime.strptime(days[0]["date"], "%Y-%m-%d").date()
    origin_offset = (first.weekday() + 1) % 7  # domingo = 0
    cells = []
    for day in days:
        d = datetime.strptime(day["date"], "%Y-%m-%d").date()
        delta = (d - first).days + origin_offset
        cells.append({**day, "week": delta // 7, "row": delta % 7, "d": d})
    return cells


def promote_top(cells: list[dict]) -> None:
    """Nivel 5 (neon) para os dias excepcionais: destaca o pico real do ano."""
    counts = sorted((c["count"] for c in cells if c["count"] > 0), reverse=True)
    if not counts:
        return
    cut = max(10, counts[max(0, int(len(counts) * 0.03))])
    for c in cells:
        if c["count"] >= cut:
            c["level"] = 5


def render() -> str:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    stats = payload["stats"]
    cells = build_grid(payload["days"])
    promote_top(cells)

    weeks = max(c["week"] for c in cells) + 1
    grid_h = 7 * STEP - GAP
    height = GRID_TOP + grid_h + 62

    parts: list[str] = []
    add = parts.append
    add(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" role="img" '
        f'aria-label="{br(stats["total"])} contribuições no último ano">'
    )
    add(
        "<style>"
        "text{font-family:ui-monospace,'SFMono-Regular','JetBrains Mono',Consolas,monospace}"
        "@keyframes drop{from{opacity:0;transform:translate(0,-9px) scale(.4)}"
        "60%{opacity:1}to{opacity:1;transform:translate(0,0) scale(1)}}"
        "@keyframes fade{from{opacity:0}to{opacity:1}}"
        ".c{transform-box:fill-box;transform-origin:center;"
        "animation:drop .5s cubic-bezier(.2,.9,.3,1.4) backwards}"
        ".f{animation:fade .6s ease backwards}"
        "@media(prefers-reduced-motion:reduce){.c,.f{animation:none}}"
        "</style>"
    )

    # janela de terminal
    add(f'<rect width="{WIDTH}" height="{height}" rx="10" fill="{BG}" stroke="{STROKE}"/>')
    add(f'<line x1="0" y1="38" x2="{WIDTH}" y2="38" stroke="{STROKE}"/>')
    for i, color in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        add(f'<circle cx="{22 + i * 18}" cy="19" r="5.5" fill="{color}"/>')
    add(
        f'<text x="84" y="24" font-size="12.5" fill="{DIM}">'
        f'<tspan fill="{ACCENT}">duniinjja@github</tspan>:<tspan fill="#58a6ff">~</tspan>'
        f'$ ./contributions.sh --last-year</text>'
    )

    # rotulos de mes
    seen: set[str] = set()
    for c in cells:
        key = c["d"].strftime("%Y-%m")
        if key in seen or c["row"] != 0 or c["d"].day > 7:
            continue
        seen.add(key)
        x = PAD_LEFT + c["week"] * STEP
        if x < WIDTH - PAD_RIGHT - 20:
            add(
                f'<text class="f" x="{x}" y="{GRID_TOP - 8}" font-size="10.5" fill="{DIM}" '
                f'style="animation-delay:{0.25 + c["week"] * 0.006:.2f}s">{MONTHS_PT[c["d"].month - 1]}</text>'
            )

    # rotulos de dia
    for row, label in ((1, "seg"), (3, "qua"), (5, "sex")):
        y = GRID_TOP + row * STEP + CELL - 2
        add(f'<text class="f" x="6" y="{y}" font-size="10" fill="{DIM}">{label}</text>')

    # celulas
    for c in cells:
        x = PAD_LEFT + c["week"] * STEP
        y = GRID_TOP + c["row"] * STEP
        delay = 0.3 + (c["week"] + c["row"] * 2.2) * 0.011
        title = "sem contribuição" if not c["count"] else f'{c["count"]} contribuições'
        add(
            f'<rect class="c" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.6" '
            f'fill="{PALETTE[c["level"]]}" style="animation-delay:{delay:.2f}s">'
            f'<title>{c["date"]}: {title}</title></rect>'
        )

    # legenda
    base_y = GRID_TOP + grid_h + 24
    legend_x = WIDTH - PAD_RIGHT - 6 * (CELL + 4) - 74
    add(
        f'<text class="f" x="{legend_x}" y="{base_y + 10}" font-size="10.5" fill="{DIM}" '
        f'style="animation-delay:1.5s">menos</text>'
    )
    for i, color in enumerate(PALETTE):
        add(
            f'<rect class="c" x="{legend_x + 40 + i * (CELL + 4)}" y="{base_y}" width="{CELL}" '
            f'height="{CELL}" rx="2.6" fill="{color}" style="animation-delay:{1.55 + i * 0.05:.2f}s"/>'
        )
    add(
        f'<text class="f" x="{legend_x + 40 + 6 * (CELL + 4) + 6}" y="{base_y + 10}" font-size="10.5" '
        f'fill="{DIM}" style="animation-delay:1.9s">mais</text>'
    )

    # rodape com numeros reais
    best = stats["best_day"]
    add(
        f'<text class="f" x="{PAD_LEFT - 2}" y="{base_y + 10}" font-size="11.5" fill="{FG}" '
        f'style="animation-delay:1.45s">'
        f'<tspan fill="{ACCENT}" font-weight="700">{br(stats["total"])}</tspan> contribuições'
        f'<tspan fill="{DIM}"> no último ano &#183; </tspan>'
        f'<tspan fill="{ACCENT}" font-weight="700">{stats["current_streak"]}</tspan>'
        f'<tspan fill="{DIM}"> dias seguidos &#183; pico de </tspan>'
        f'<tspan fill="{ACCENT}" font-weight="700">{best["count"]}</tspan>'
        f'<tspan fill="{DIM}"> em {datetime.strptime(best["date"], "%Y-%m-%d").strftime("%d/%m")}</tspan>'
        f"</text>"
    )
    add("</svg>")
    return "".join(parts)


if __name__ == "__main__":
    OUT.write_text(render(), encoding="utf-8")
    print(f"{OUT.name} -> {OUT.stat().st_size / 1024:.1f} KB")
