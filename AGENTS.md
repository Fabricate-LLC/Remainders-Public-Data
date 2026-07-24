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
- Use only an SF Symbol raw value listed in **Valid event symbols** below. A symbol may exist in SF Symbols but still be unsupported by Remainders. One unsupported value invalidates its record and causes the app to reject the entire downloaded catalog.
- Reminder values are seconds before the event and must be numeric or `null`.
- Do not add JSON comments, duplicate fields, or undocumented properties.

## Content standards

- Verify dates and official names against reliable primary sources whenever practical.
- Do not add an event unless a verified official English title is available. Reject database identifiers and label fallbacks such as `Q126912601`, as well as untranslated or romanized-only titles that have no official English release title; do not invent a translation. Numbers remain allowed when they are intrinsic to a verified title.
- Translate meaning naturally; do not merely preserve English phrasing in Spanish or Italian.
- Avoid political advocacy, promotional copy, sensitive personal data, and speculative observances.
- Use `Other` for generic awareness and observance events, including names such as "International Day of X", "World X Day", and similar non-holiday observances. Reserve `Special Event` for distinct scheduled happenings such as tournaments, championships, launches, or ceremonies.
- For a fixed-date annual historical holiday or observance with an authoritative founding or declaration year, set `dueDate` to the observed month and day in that historical year (for example, `1776-07-04` for American Independence Day), set `repeatEvent` to `Every Year`, and suffix the `id` with that historical year.
- Keep only one record for a fixed-date annual event. If no authoritative founding or declaration year exists, use one verified occurrence date rather than inventing a historical year.
- Keep moving holidays whose dates cannot be represented by the supported recurrence values as occurrence-specific records with `repeatEvent` set to `Never`.
- Keep descriptions concise and factual.
- Do not include calendar dates or occurrence years in `localizedNames`. Use the base event title, such as `Masters` instead of `Masters Tournament 2027` and `Kentucky Derby` instead of `Kentucky Derby 2027`; record the occurrence in `dueDate`, the `id` year suffix, and `localizedNotes`. Preserve numbers only when they are intrinsic to the official base title, such as a movie or game title or a numbered event like `Super Bowl LXI`.
- Categorize events using the app's exact singular raw values. Assign video game releases only to `Game` and movie releases only to `Movie`; never categorize either as `Special Event`.
- For video game events, use only the game's official base title in every `localizedNames` value. Do not append gaming platforms or platform-specific qualifiers such as `(Nintendo Switch 2)`, `(PlayStation 5)`, `(Xbox Series X|S)`, or `(PC)`. Put platform availability in `localizedNotes` only when it is relevant and verified.
- This repository is published publicly. Never add credentials, tokens, private URLs, or user information.
- Clean up the file and remove sale singular events that are in the past.

## Valid event symbols

The `icon` field must exactly match one of these raw values from the Remainders `AppSymbols` enum:

```text
clock.fill
clock.badge.questionmark.fill
clock.badge.questionmark
alarm.fill
calendar
party.popper.fill
balloon.2.fill
wineglass.fill
birthday.cake.fill
figure.walk
airplane
graduationcap.fill
car.fill
bus
tram.fill
cablecar.fill
ferry.fill
sailboat.fill
bicycle
box.truck.fill
bed.double.fill
beach.umbrella.fill
pills.fill
testtube.2
hare.fill
tortoise.fill
ladybug.fill
fish.fill
lizard.fill
bird.fill
leaf.fill
mountain.2.fill
tree.fill
camera
gamecontroller.fill
popcorn.fill
film.fill
paintpalette.fill
fork.knife
waveform.path.ecg.rectangle.fill
trash.fill
folder.fill
bookmark.fill
ticket.fill
person.circle.fill
power.circle.fill
globe.americas.fill
globe.europe.africa.fill
globe.central.south.asia.fill
globe.asia.australia.fill
sun.and.horizon.fill
sun.max.fill
moon.stars.fill
cloud.rain.fill
snowflake
play.circle.fill
mic.fill
heart.fill
star.fill
flag.fill
location.fill
bell.fill
bolt.fill
eye.fill
tshirt.fill
phone.fill
video.fill
gear
bag.fill
gift.fill
cart.fill
creditcard.fill
hammer.fill
briefcase.fill
list.bullet.rectangle.fill
rectangle.inset.filled.and.person.filled
person.3.fill
house.fill
tent.fill
sportscourt.fill
mappin.and.ellipse
desktopcomputer
laptopcomputer
iphone
ipad.landscape
vision.pro
applewatch
camera.macro
ipod
fireworks
laser.burst
```

Use `film.fill` or `popcorn.fill` for movies, `gamecontroller.fill` for video games, and `sportscourt.fill` for sporting events. Do not substitute sport-specific symbols such as `soccerball` or `football.fill` unless those raw values are first added to the app's `AppSymbols` enum and released to users. When `AppSymbols` changes, update this allowlist, the JSON Schema, the validator, and fallback data together.

When the format itself must change, update the app decoder, JSON Schema, validator, documentation, and fallback data together before publishing the new format.
