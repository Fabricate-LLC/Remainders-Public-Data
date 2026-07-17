# Remainders Public Data

Public, version-controlled event suggestions consumed by the Remainders app.

## Published file

After GitHub Pages is enabled for this repository, the production endpoint is:

```text
https://fabricate-llc.github.io/Remainders-Public-Data/PublicEvents.json
```

The published data is intentionally public. Do not add secrets, private user data, unpublished product information, or credentials.

## Updating events

1. Create a branch from `main`.
2. Edit `PublicEvents.json` while preserving its top-level array structure.
3. Provide English, Spanish, and Italian names and notes for every event.
4. Run the validator:

   ```bash
   python3 scripts/validate_public_events.py
   ```

5. Open a pull request and merge it after the `Validate public events` check passes.

GitHub Pages republishes the file after changes reach `main`. Git history provides the audit trail and rollback mechanism.

## Repository files

- `PublicEvents.json`: production event catalog.
- `PublicEvents.schema.json`: machine-readable JSON Schema for editors and agents.
- `scripts/validate_public_events.py`: dependency-free semantic validation.
- `AGENTS.md`: editing instructions for AI agents and contributors.

The Remainders app should retain a bundled fallback and only replace its cached catalog after a downloaded file validates and decodes successfully.
