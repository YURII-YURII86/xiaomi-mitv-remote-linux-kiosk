# Changelog

## 0.2.6 - 2026-07-11

- Added `scripts/repo_quality_gate.sh` for reproducible repository presentation/quality review.
- Added CI quality gate step and explicit read-only GitHub Actions permissions.
- Pinned CI runner to `ubuntu-24.04` instead of floating `ubuntu-latest`.

## 0.2.5 - 2026-07-11

- Added unified `xiaomi-remote` native CLI with subcommands for setup, profiles, capture, lab, doctor, daemon, status, and flow.
- Added English/Russian language selection with `--lang en|ru` and `XMR_LANG`.
- Kept existing `xiaomi-mitv-remote-*` commands for backward compatibility.

## 0.2.4 - 2026-07-11

- Added `xiaomi-mitv-remote-lab` guided validation/report CLI.
- Added hardware validation report schema and example report.
- Reworked hardware validation docs around lab-generated artifacts.
- Extended smoke tests to cover lab report and explicit keymap generation.

## 0.2.3 - 2026-07-11

- Added compatibility profile registry and `xiaomi-mitv-remote-profiles` CLI.
- Added Xiaomi/MiTV and generic Bluetooth HID remote profile examples.
- Added cautious udev/non-root guide.
- Added `linux-tv-kiosk-shell` integration notes.
- Removed generated runtime `data/remote-action.js` from source tracking.

## 0.2.2 - 2026-07-11

- Added `xiaomi-mitv-remote-doctor` safe redacted diagnostics report CLI.
- Added keymap validation helper and warnings for missing/duplicate mappings.
- Extended smoke tests to cover diagnostics report generation.

## 0.2.1 - 2026-07-11

- Added full Russian README at `docs/README.ru.md`.
- Linked Russian documentation from the main README.

## 0.2.0 - 2026-07-11

- Added `xiaomi-mitv-remote-setup` setup helper.
- Added `xiaomi-mitv-remote-capture` keymap capture/conversion helper.
- Added API, troubleshooting, and security docs.
- Added GitHub Actions smoke-test workflow.

## 0.1.0 - 2026-07-11

- Initial public release.
- Added Linux HID input daemon for Xiaomi/MiTV-style Bluetooth remotes.
- Added status exporter for kiosk dashboards.
- Added browser JS bridge and localhost long-poll endpoint.
- Added example keymap and systemd service files.
- Added smoke tests for parsers and example keymap validation.
