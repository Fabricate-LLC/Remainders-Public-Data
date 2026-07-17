# Remainders Public Data Agent Guide

This repository publishes the public event suggestions used by Remainders. Treat `PublicEvents.json` as production data.

## Required workflow

1. Make focused changes on a branch and use a pull request.
2. Edit only the events relevant to the request. Do not reformat or reorder unrelated entries.
3. Run `python3 scripts/validate_public_events.py` before committing.
4. Do not merge changes unless the `Validate public events` GitHub check passes.

## Data contract

- Keep the JSON document as a top-level array. Do not wrap it in a manifest object unless the app decoder is updated first.
- Keep every `id` unique, lowercase, kebab-cased, and suffixed with the event year.
- Format `dueDate` as a real Gregorian calendar date using `YYYY-MM-DD`.
- Ensure the year suffix in `id` matches the year in `dueDate`.
- Provide nonempty `en`, `es`, and `it` values in both `localizedNames` and `localizedNotes`.
- Use only category, color, and recurrence values accepted by `PublicEvents.schema.json`.
- Use an SF Symbol raw value supported by the Remainders `AppSymbols` enum. Unsupported symbols fall back to the calendar icon in the app.
- Reminder values are seconds before the event and must be numeric or `null`.
- Do not add JSON comments, duplicate fields, or undocumented properties.

## Content standards

- Verify dates and official names against reliable primary sources whenever practical.
- Translate meaning naturally; do not merely preserve English phrasing in Spanish or Italian.
- Avoid political advocacy, promotional copy, sensitive personal data, and speculative observances.
- Avoid somewhat generic "days"" like "International Literacy Day" or "World Tourism Day".
- Keep descriptions concise and factual.
- Categorize events into the correct category (e.g. Video Game releases in "Games" or Movies in "Movies")
- This repository is published publicly. Never add credentials, tokens, private URLs, or user information.
- Clean up the file and remove sale singular events that are in the past.

When the format itself must change, update the app decoder, JSON Schema, validator, documentation, and fallback data together before publishing the new format.
