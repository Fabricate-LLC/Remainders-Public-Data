#!/usr/bin/env python3
"""Validate the production Remainders public-event catalog without dependencies."""

from __future__ import annotations

import json
import math
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EVENTS_PATH = REPOSITORY_ROOT / "PublicEvents.json"
SCHEMA_PATH = REPOSITORY_ROOT / "PublicEvents.schema.json"
REQUIRED_LOCALES = {"en", "es", "it"}
MAXIMUM_CATALOG_BYTE_COUNT = 1_048_576
IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*-([0-9]{4})$")


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build a JSON object while rejecting duplicate field names."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def reject_nonstandard_number(value: str) -> None:
    """Reject non-standard JSON constants such as NaN and Infinity."""
    raise ValueError(f"non-standard JSON number {value!r}")


def load_json(path: Path) -> Any:
    """Load strict UTF-8 JSON without duplicate keys or non-standard numbers."""
    with path.open("r", encoding="utf-8") as input_file:
        return json.load(
            input_file,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_nonstandard_number,
        )


def is_number_or_none(value: Any) -> bool:
    """Return whether a reminder value is null or a finite, non-Boolean number."""
    return value is None or (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def validate_localized_text(value: Any, field_path: str, errors: list[str]) -> None:
    """Validate exact English, Spanish, and Italian localized string entries."""
    if not isinstance(value, dict):
        errors.append(f"{field_path} must be an object")
        return

    locales = set(value)
    if locales != REQUIRED_LOCALES:
        errors.append(
            f"{field_path} locales must be exactly {sorted(REQUIRED_LOCALES)}; "
            f"found {sorted(locales)}"
        )

    for locale, text in value.items():
        if not isinstance(text, str) or not text.strip():
            errors.append(f"{field_path}.{locale} must be a nonempty string")


def validate_event(
    event: Any,
    index: int,
    event_schema: dict[str, Any],
    seen_identifiers: set[str],
    errors: list[str],
) -> None:
    """Validate one event against the published contract and semantic rules."""
    event_path = f"event[{index}]"
    if not isinstance(event, dict):
        errors.append(f"{event_path} must be an object")
        return

    required_fields = set(event_schema["required"])
    actual_fields = set(event)
    missing_fields = sorted(required_fields - actual_fields)
    unexpected_fields = sorted(actual_fields - required_fields)

    if missing_fields:
        errors.append(f"{event_path} is missing fields: {missing_fields}")
    if unexpected_fields:
        errors.append(f"{event_path} has undocumented fields: {unexpected_fields}")
    if missing_fields:
        return

    identifier = event["id"]
    identifier_match = IDENTIFIER_PATTERN.fullmatch(identifier) if isinstance(identifier, str) else None
    if identifier_match is None:
        errors.append(f"{event_path}.id must be lowercase kebab-case ending in a four-digit year")
    elif identifier in seen_identifiers:
        errors.append(f"{event_path}.id duplicates {identifier!r}")
    else:
        seen_identifiers.add(identifier)

    date_value: date | None = None
    due_date = event["dueDate"]
    if not isinstance(due_date, str):
        errors.append(f"{event_path}.dueDate must be a YYYY-MM-DD string")
    else:
        try:
            date_value = date.fromisoformat(due_date)
        except ValueError:
            errors.append(f"{event_path}.dueDate is not a real calendar date: {due_date!r}")

    if identifier_match is not None and date_value is not None:
        identifier_year = int(identifier_match.group(1))
        if identifier_year != date_value.year:
            errors.append(
                f"{event_path}.id year {identifier_year} does not match dueDate year {date_value.year}"
            )

    properties = event_schema["properties"]
    for field_name in ("category", "icon", "color", "repeatEvent"):
        allowed_values = properties[field_name]["enum"]
        if event[field_name] not in allowed_values:
            errors.append(
                f"{event_path}.{field_name} must be one of {allowed_values}; "
                f"found {event[field_name]!r}"
            )

    validate_localized_text(event["localizedNames"], f"{event_path}.localizedNames", errors)
    validate_localized_text(event["localizedNotes"], f"{event_path}.localizedNotes", errors)

    if not isinstance(event["allDay"], bool):
        errors.append(f"{event_path}.allDay must be a Boolean")
    if not isinstance(event["notifications"], bool):
        errors.append(f"{event_path}.notifications must be a Boolean")

    for reminder_field in ("primaryReminderSeconds", "secondaryReminderSeconds"):
        if not is_number_or_none(event[reminder_field]):
            errors.append(f"{event_path}.{reminder_field} must be finite numeric or null")


def main() -> int:
    """Validate the catalog and return a process exit status."""
    if len(sys.argv) > 2:
        print("Usage: validate_public_events.py [PublicEvents.json]", file=sys.stderr)
        return 2

    events_path = Path(sys.argv[1]) if len(sys.argv) == 2 else EVENTS_PATH
    try:
        catalog_byte_count = events_path.stat().st_size
        if catalog_byte_count > MAXIMUM_CATALOG_BYTE_COUNT:
            print(
                f"PublicEvents.json is {catalog_byte_count} bytes; "
                f"the app limit is {MAXIMUM_CATALOG_BYTE_COUNT} bytes",
                file=sys.stderr,
            )
            return 1

        events = load_json(events_path)
        schema = load_json(SCHEMA_PATH)
    except (OSError, ValueError) as error:
        print(f"Unable to load repository data: {error}", file=sys.stderr)
        return 1

    errors: list[str] = []
    if not isinstance(events, list) or not events:
        print("PublicEvents.json must contain a nonempty top-level array", file=sys.stderr)
        return 1

    event_schema = schema["$defs"]["event"]
    seen_identifiers: set[str] = set()
    for index, event in enumerate(events):
        validate_event(event, index, event_schema, seen_identifiers, errors)

    if errors:
        print("PublicEvents.json validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Validated {len(events)} public events.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
