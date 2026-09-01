#!/usr/bin/env python3
"""Refresh PublicEvents.json with upcoming public event suggestions.

The weekly GitHub Actions workflow runs this script after pulling the latest
repository state. It is intentionally conservative: it removes stale one-off
entries, preserves single anchored yearly recurring entries, and uses public
Wikidata lookups plus curated special-event rules to add dated future movies,
PlayStation games, Nintendo games, and major special events. Entries without
confirmed dates are skipped rather than guessed.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import ssl
import textwrap
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
EVENTS_PATH = ROOT / "PublicEvents.json"
HORIZON_DAYS = 365
MAX_ITEMS_PER_MEDIA_KIND = 20
USER_AGENT = "Remainders-Public-Data weekly updater (public GitHub Actions workflow)"
NON_ID_CHARS_RE = re.compile(r"[^a-z0-9]+")
FALLBACK_TITLE_RE = re.compile(r"^Q[0-9]+$")

TRANSLATED_NOTES = {
    "movie": {
        "en": "The scheduled theatrical release of {title}.",
        "es": "El estreno cinematográfico previsto de {title}.",
        "it": "L'uscita cinematografica prevista di {title}.",
    },
    "playstation_game": {
        "en": "The scheduled PlayStation release of {title}.",
        "es": "El lanzamiento previsto de {title} para PlayStation.",
        "it": "L'uscita prevista di {title} per PlayStation.",
    },
    "nintendo_game": {
        "en": "The scheduled Nintendo release of {title}.",
        "es": "El lanzamiento previsto de {title} para Nintendo.",
        "it": "L'uscita prevista di {title} per Nintendo.",
    },
}

SPECIAL_EVENTS = [
    {
        "id_base": "super-bowl-lxi",
        "name": "Super Bowl LXI",
        "date": "2027-02-14",
        "icon": "sportscourt.fill",
        "color": "green",
        "notes": {
            "en": "The NFL championship game for the 2026 season, scheduled for SoFi Stadium.",
            "es": "El partido de campeonato de la NFL de la temporada 2026, previsto en el SoFi Stadium.",
            "it": "La finale NFL della stagione 2026, in programma al SoFi Stadium.",
        },
    },
    {
        "id_base": "fifa-world-cup-final",
        "name": "FIFA World Cup Final",
        "date": "2026-07-19",
        "icon": "sportscourt.fill",
        "color": "green",
        "notes": {
            "en": "The championship match of the 2026 FIFA World Cup.",
            "es": "El partido final de la Copa Mundial de la FIFA 2026.",
            "it": "La finale della Coppa del Mondo FIFA 2026.",
        },
    },
    {
        "id_base": "winter-olympics-opening-ceremony",
        "name": "Winter Olympics Opening Ceremony",
        "date": "2026-02-06",
        "icon": "snowflake",
        "color": "blue",
        "notes": {
            "en": "The opening ceremony of the Milano Cortina 2026 Olympic Winter Games.",
            "es": "La ceremonia de apertura de los Juegos Olímpicos de Invierno Milano Cortina 2026.",
            "it": "La cerimonia di apertura dei Giochi olimpici invernali di Milano Cortina 2026.",
        },
    },
    {
        "id_base": "summer-olympics-opening-ceremony",
        "name": "Summer Olympics Opening Ceremony",
        "date": "2028-07-14",
        "icon": "sportscourt.fill",
        "color": "orange",
        "notes": {
            "en": "The opening ceremony of the Los Angeles 2028 Olympic Games.",
            "es": "La ceremonia de apertura de los Juegos Olímpicos Los Ángeles 2028.",
            "it": "La cerimonia di apertura dei Giochi olimpici di Los Angeles 2028.",
        },
    },
]


def load_events() -> list[dict[str, Any]]:
    with EVENTS_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise TypeError("PublicEvents.json must contain a top-level array")
    return data


def write_events(events: list[dict[str, Any]]) -> None:
    with EVENTS_PATH.open("w", encoding="utf-8") as handle:
        json.dump(events, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def slugify(value: str) -> str:
    slug = NON_ID_CHARS_RE.sub("-", value.lower()).strip("-")
    return slug or "event"


def unique_id(base: str, due_date: str, existing_ids: set[str]) -> str:
    year = due_date[:4]
    candidate = f"{slugify(base)}-{year}"
    suffix = 2
    while candidate in existing_ids:
        candidate = f"{slugify(base)}-{suffix}-{year}"
        suffix += 1
    existing_ids.add(candidate)
    return candidate


def sparql_query(query: str) -> list[dict[str, Any]]:
    params = urlencode({"query": query, "format": "json"})
    request = Request(
        f"https://query.wikidata.org/sparql?{params}",
        headers={"Accept": "application/sparql-results+json", "User-Agent": USER_AGENT},
    )
    try:
        with urlopen(request, timeout=30, context=ssl.create_default_context()) as response:
            return json.loads(response.read().decode())["results"]["bindings"]
    except (HTTPError, URLError, TimeoutError) as error:
        print(f"Wikidata lookup skipped: {error}")
        return []


def media_query(kind: str, today: dt.date, horizon: dt.date) -> str:
    if kind == "movie":
        type_filter = "?item wdt:P31/wdt:P279* wd:Q11424."
        platform_filter = ""
    elif kind == "playstation_game":
        type_filter = "?item wdt:P31/wdt:P279* wd:Q7889."
        platform_filter = "VALUES ?platform { wd:Q10677 wd:Q5014725 wd:Q63184502 } ?item wdt:P400 ?platform."
    else:
        type_filter = "?item wdt:P31/wdt:P279* wd:Q7889."
        platform_filter = "VALUES ?platform { wd:Q19610114 wd:Q8079 wd:Q203597 } ?item wdt:P400 ?platform."
    return textwrap.dedent(f"""
        SELECT ?item ?itemLabel ?date WHERE {{
          {type_filter}
          {platform_filter}
          ?item wdt:P577 ?date.
          FILTER(?date >= "{today.isoformat()}"^^xsd:dateTime && ?date <= "{horizon.isoformat()}"^^xsd:dateTime)
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        ORDER BY ?date ?itemLabel
        LIMIT {MAX_ITEMS_PER_MEDIA_KIND}
    """)


def build_media_events(today: dt.date) -> list[dict[str, Any]]:
    horizon = today + dt.timedelta(days=HORIZON_DAYS)
    events: list[dict[str, Any]] = []
    for kind in ("movie", "playstation_game", "nintendo_game"):
        time.sleep(1)
        for row in sparql_query(media_query(kind, today, horizon)):
            title = row.get("itemLabel", {}).get("value", "").strip()
            if not title or FALLBACK_TITLE_RE.fullmatch(title):
                print(f"Skipping {kind} without a verified English title: {title or '<empty>'}")
                continue
            due_date = row["date"]["value"][:10]
            notes = TRANSLATED_NOTES[kind]
            events.append({
                "_id_base": title,
                "category": "Movie" if kind == "movie" else "Game",
                "localizedNames": {"en": title, "es": title, "it": title},
                "allDay": True,
                "dueDate": due_date,
                "icon": "film.fill" if kind == "movie" else "gamecontroller.fill",
                "color": "purple" if kind == "movie" else ("blue" if kind == "playstation_game" else "red"),
                "repeatEvent": "Never",
                "notifications": False,
                "primaryReminderSeconds": 0,
                "secondaryReminderSeconds": None,
                "localizedNotes": {language: template.format(title=title) for language, template in notes.items()},
            })
    return events


def build_special_events(today: dt.date) -> list[dict[str, Any]]:
    current_years = {today.year, today.year + 1}
    events: list[dict[str, Any]] = []
    for item in SPECIAL_EVENTS:
        due_date = dt.date.fromisoformat(item["date"])
        if due_date < today or due_date.year not in current_years:
            continue
        events.append({
            "_id_base": item["id_base"],
            "category": "Special Event",
            "localizedNames": {"en": item["name"], "es": item["name"], "it": item["name"]},
            "allDay": True,
            "dueDate": item["date"],
            "icon": item["icon"],
            "color": item["color"],
            "repeatEvent": "Never",
            "notifications": False,
            "primaryReminderSeconds": 0,
            "secondaryReminderSeconds": None,
            "localizedNotes": item["notes"],
        })
    return events


def remove_stale_events(events: list[dict[str, Any]], today: dt.date) -> list[dict[str, Any]]:
    return [
        event
        for event in events
        if event.get("repeatEvent") != "Never"
        or dt.date.fromisoformat(event["dueDate"]) >= today
    ]


def merge_new_events(events: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    existing_keys = {(event["localizedNames"]["en"].lower(), event["dueDate"]) for event in events}
    existing_ids = {event["id"] for event in events}
    additions: list[dict[str, Any]] = []
    for candidate in sorted(candidates, key=lambda item: (item["dueDate"], item["_id_base"])):
        key = (candidate["localizedNames"]["en"].lower(), candidate["dueDate"])
        if key in existing_keys:
            continue
        candidate = dict(candidate)
        candidate["id"] = unique_id(candidate.pop("_id_base"), candidate["dueDate"], existing_ids)
        additions.append(candidate)
        existing_keys.add(key)
    return additions


def main() -> int:
    today = dt.date.today()
    events = load_events()
    before_count = len(events)
    events = remove_stale_events(events, today)
    media_candidates = build_media_events(today)
    special_candidates = build_special_events(today)
    new_additions = merge_new_events(events, media_candidates + special_candidates)
    events.extend(new_additions)
    removed_count = before_count - (len(events) - len(new_additions))
    if removed_count == 0 and not new_additions:
        print("PublicEvents.json is already current; no events changed.")
        return 0
    write_events(events)
    print(f"Removed {removed_count} stale event(s).")
    print(f"Added {len(new_additions)} discovered event(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
