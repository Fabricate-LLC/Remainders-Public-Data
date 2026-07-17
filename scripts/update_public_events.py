#!/usr/bin/env python3
"""Extend recurring public events so the catalog stays current.

This script is intentionally conservative: it only derives future entries from
existing `Every Year` events in PublicEvents.json, preserves the existing entry
shape, and leaves one-off or manually dated events untouched.
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVENTS_PATH = ROOT / "PublicEvents.json"
HORIZON_DAYS = 365
YEAR_SUFFIX_RE = re.compile(r"^(?P<base>.+)-(?P<year>\d{4})$")


def load_events() -> list[dict[str, Any]]:
    with EVENTS_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise TypeError("PublicEvents.json must contain a top-level array")
    return data



def event_base_id(event: dict[str, Any]) -> str:
    match = YEAR_SUFFIX_RE.fullmatch(str(event["id"]))
    if not match:
        raise ValueError(f"Event id does not end with a four-digit year: {event['id']}")
    return match.group("base")


def replace_year_suffix(event_id: str, year: int) -> str:
    match = YEAR_SUFFIX_RE.fullmatch(event_id)
    if not match:
        raise ValueError(f"Event id does not end with a four-digit year: {event_id}")
    return f"{match.group('base')}-{year}"


def add_year(due_date: str) -> str | None:
    date = dt.date.fromisoformat(due_date)
    try:
        return date.replace(year=date.year + 1).isoformat()
    except ValueError:
        # Avoid inventing a policy for February 29 observances. Add these
        # manually when they are relevant to the catalog horizon.
        return None


def recurring_events_by_base(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        if event.get("repeatEvent") != "Every Year":
            continue
        grouped.setdefault(event_base_id(event), []).append(event)
    for group in grouped.values():
        group.sort(key=lambda item: item["dueDate"])
    return grouped


def build_future_events(events: list[dict[str, Any]], today: dt.date) -> list[dict[str, Any]]:
    horizon = today + dt.timedelta(days=HORIZON_DAYS)
    existing_ids = {event["id"] for event in events}
    additions: list[dict[str, Any]] = []

    for group in recurring_events_by_base(events).values():
        latest = group[-1]
        while dt.date.fromisoformat(latest["dueDate"]) < horizon:
            next_due_date = add_year(latest["dueDate"])
            if next_due_date is None:
                break
            next_year = int(next_due_date[:4])
            next_id = replace_year_suffix(latest["id"], next_year)
            if next_id in existing_ids:
                latest = next(event for event in group if event["id"] == next_id)
                continue

            next_event = copy.deepcopy(latest)
            next_event["id"] = next_id
            next_event["dueDate"] = next_due_date
            additions.append(next_event)
            existing_ids.add(next_id)
            group.append(next_event)
            latest = next_event

    additions.sort(key=lambda item: (item["dueDate"], item["id"]))
    return additions


def write_events(events: list[dict[str, Any]]) -> None:
    with EVENTS_PATH.open("w", encoding="utf-8") as handle:
        json.dump(events, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main() -> int:
    events = load_events()
    additions = build_future_events(events, dt.date.today())
    if not additions:
        print("PublicEvents.json is already current; no events added.")
        return 0

    events.extend(additions)
    write_events(events)
    print(f"Added {len(additions)} recurring public event(s).")
    for event in additions:
        print(f"- {event['id']} ({event['dueDate']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
