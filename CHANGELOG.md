# Changelog

All notable changes to this project are documented in this file.

## [0.1.0] - 2026-10-10

### Added
- Command line toolkit, run as `python -m chorekit <command>`.
- `sort`: moves files into subfolders by type (Images, Documents, Videos, Audio, Archives, Code, Others) or by modification month; `--dry-run`, `--recursive`; name collisions become `name_1`, `name_2`, ...
- `undo`: reverts the last `sort` using the `.chorekit_moves.json` log and removes folders that became empty.
- `report`: file count and size per category plus the largest files; output as Markdown, CSV or JSON.
- `rates`: current exchange rates from `open.er-api.com` (no API key); retries on network errors, HTTP 429 and HTTP 5xx; `--symbols`, `--convert` with `--to`, JSON or CSV output.
- Unit tests with mocked network calls.
- README with banner, diagram and example run.
