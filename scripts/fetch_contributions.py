"""Baixa o calendario publico de contribuicoes e grava data/contributions.json.

Nao usa token nem GraphQL: o GitHub serve o mesmo fragmento HTML que a
propria pagina de perfil consome, em /users/<login>/contributions.
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import requests

USER = os.environ.get("PROFILE_USER", "Duniinjja")
URL = f"https://github.com/users/{USER}/contributions"
OUT = Path(__file__).resolve().parent.parent / "data" / "contributions.json"

# <td ... data-date="2025-08-31" id="contribution-day-component-0-0" data-level="0" ...>
CELL_RE = re.compile(
    r'<td[^>]*?data-date="(?P<date>\d{4}-\d{2}-\d{2})"'
    r'[^>]*?id="(?P<id>contribution-day-component-[^"]+)"'
    r'[^>]*?data-level="(?P<level>\d+)"',
    re.S,
)
# <tool-tip ... for="contribution-day-component-0-0" ...>No contributions on August 31st.</tool-tip>
TIP_RE = re.compile(
    r'<tool-tip[^>]*?for="(?P<id>contribution-day-component-[^"]+)"[^>]*>(?P<text>.*?)</tool-tip>',
    re.S,
)
COUNT_RE = re.compile(r"^\s*(?:(\d[\d,]*)|No)\s+contribution", re.I)


def fetch_html() -> str:
    resp = requests.get(
        URL,
        headers={
            "User-Agent": "profile-art/1.0 (+https://github.com/%s)" % USER,
            "Accept": "text/html",
            "X-Requested-With": "XMLHttpRequest",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text


def parse_days(markup: str) -> list[dict]:
    counts: dict[str, int] = {}
    for tip in TIP_RE.finditer(markup):
        text = html.unescape(re.sub(r"<[^>]+>", "", tip.group("text"))).strip()
        m = COUNT_RE.match(text)
        if m:
            counts[tip.group("id")] = int(m.group(1).replace(",", "")) if m.group(1) else 0

    days = []
    for cell in CELL_RE.finditer(markup):
        cid = cell.group("id")
        days.append(
            {
                "date": cell.group("date"),
                "level": int(cell.group("level")),
                "count": counts.get(cid, 0),
            }
        )
    days.sort(key=lambda d: d["date"])
    return days


def streaks(days: list[dict]) -> tuple[int, int]:
    """Streak atual (ignora o dia de hoje ainda em aberto) e a maior streak."""
    longest = run = 0
    for day in days:
        run = run + 1 if day["count"] > 0 else 0
        longest = max(longest, run)

    current = 0
    today = date.today().isoformat()
    for day in reversed(days):
        if day["date"] > today:
            continue
        if day["count"] > 0:
            current += 1
        elif day["date"] == today:
            continue  # o dia de hoje ainda pode receber commits
        else:
            break
    return current, longest


def build() -> dict:
    days = parse_days(fetch_html())
    if len(days) < 300:
        raise SystemExit(f"HTML inesperado: apenas {len(days)} dias encontrados")

    total = sum(d["count"] for d in days)
    active = [d for d in days if d["count"] > 0]
    best = max(days, key=lambda d: d["count"])
    current, longest = streaks(days)

    months: dict[str, int] = {}
    for day in days:
        months[day["date"][:7]] = months.get(day["date"][:7], 0) + day["count"]

    return {
        "user": USER,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "range": {"from": days[0]["date"], "to": days[-1]["date"]},
        "stats": {
            "total": total,
            "active_days": len(active),
            "busiest_weekday": busiest_weekday(days),
            "current_streak": current,
            "longest_streak": longest,
            "best_day": {"date": best["date"], "count": best["count"]},
            "average_per_active_day": round(total / len(active), 1) if active else 0.0,
        },
        "months": months,
        "days": days,
    }


def busiest_weekday(days: list[dict]) -> str:
    names = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
    totals = [0] * 7
    for day in days:
        totals[datetime.strptime(day["date"], "%Y-%m-%d").weekday()] += day["count"]
    return names[totals.index(max(totals))]


if __name__ == "__main__":
    payload = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    s = payload["stats"]
    print(
        f"{len(payload['days'])} dias | {s['total']} contribuições | "
        f"streak {s['current_streak']} (recorde {s['longest_streak']}) | "
        f"melhor dia {s['best_day']['date']} = {s['best_day']['count']}",
        file=sys.stderr,
    )
