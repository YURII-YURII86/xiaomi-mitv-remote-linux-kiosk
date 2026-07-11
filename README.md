# Xiaomi MiTV Remote SDK for Linux Kiosks

[![CI](https://github.com/YURII-YURII86/xiaomi-mitv-remote-linux-kiosk/actions/workflows/ci.yml/badge.svg)](https://github.com/YURII-YURII86/xiaomi-mitv-remote-linux-kiosk/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](pyproject.toml)

Use a physical Xiaomi MiTV / Android TV Bluetooth remote as a first-class controller for a Linux kiosk, local dashboard, browser app, signage screen, or appliance UI.

This is not an Android TV remote-control client. It does **not** use ADB and it does **not** require Android TV. It reads the remote as a Linux HID input device and turns button presses into app-friendly actions.

```text
Xiaomi / MiTV Bluetooth remote
        ↓
Linux /dev/input/event*
        ↓
EV_KEY reader + keymap + debounce + optional EVIOCGRAB
        ↓
JS file bridge / JSON state / localhost long-poll endpoint
        ↓
Firefox kiosk, Chromium kiosk, Electron, Python, Node, or any local app
```

## Why this exists

Linux kiosk projects often need a real couch-friendly remote, not a keyboard, mouse, touchscreen, Android TV API, or Home Assistant automation. Xiaomi/MiTV remotes are cheap and familiar, but once paired to Linux they can appear as changing `/dev/input/eventN` devices and may send duplicate events through multiple HID interfaces.

This SDK handles that boring but important glue:

- finds the current input event nodes after reboot;
- maps raw Linux key codes to semantic actions such as `up`, `center`, `back`, `home`;
- debounces duplicate HID events;
- optionally grabs the input device so the browser/window manager does not steal buttons;
- exposes button presses to browser and local apps through simple files and a local HTTP endpoint;
- exports status for health cards and diagnostics.

## Naming

Xiaomi/MiTV stays in the name on purpose because that is the concrete remote family this was built around. Internally, the code is generic Linux HID handling: other Bluetooth remotes can work if they expose `EV_KEY` events and have a JSON keymap.

## Current verification status

Verified in this standalone repo:

- Python syntax check for package modules.
- Parser/unit tests for Linux input discovery and Bluetooth status parsing.
- Example keymap JSON validation.
- Privacy scan before publication: no private Slane paths, Tailnet names, real remote MAC, or local diagnostics are included.

Not yet verified after extraction:

- End-to-end hardware test with a real Xiaomi/MiTV remote using this standalone package.
- udev non-root setup. The documented systemd examples use root, which is common for appliance-style kiosks but not ideal for every desktop.

## Features

- Discovers current `/dev/input/eventN` nodes from `/proc/bus/input/devices`.
- Matches remotes by Bluetooth MAC/Uniq or device name regex.
- Reads Linux `EV_KEY` events directly.
- Supports optional `EVIOCGRAB` to keep Firefox/Chromium/window manager from also consuming buttons.
- Debounces duplicate button events across multiple HID interfaces.
- Writes a browser-friendly JS bridge such as `data/remote-action.js`.
- Exposes a localhost long-poll endpoint for apps that prefer `fetch()`.
- Exports status JSON/JS for dashboards and diagnostics.
- Ships systemd service examples.
- No third-party Python runtime dependencies.

## Install from source

```bash
git clone https://github.com/YURII-YURII86/xiaomi-mitv-remote-linux-kiosk.git
cd xiaomi-mitv-remote-linux-kiosk
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

The install command above was tested locally before publishing. Real input access still depends on Linux permissions for `/dev/input/event*`.

## Quick start

Create a keymap from the example:

```bash
mkdir -p data
cp examples/mi-remote-keymap.example.json data/mi-remote-keymap.json
```

Run the input daemon in observe/grab mode. Replace the MAC address with your remote MAC, or leave `LKR_REMOTE_MAC` empty and rely on `LKR_DEVICE_NAME_REGEX` while testing.

```bash
sudo \
  LKR_ROOT="$PWD" \
  LKR_REMOTE_MAC="AA:BB:CC:DD:EE:FF" \
  LKR_DEVICE_NAME_REGEX="xiaomi|mi rc|android.*remote|remote" \
  xiaomi-mitv-remote-input
```

During debugging, set `LKR_GRAB=0` so the desktop/browser can still receive the buttons:

```bash
sudo \
  LKR_ROOT="$PWD" \
  LKR_GRAB=0 \
  LKR_DEVICE_NAME_REGEX="xiaomi|mi rc|android.*remote|remote" \
  xiaomi-mitv-remote-input
```


## Compatibility profiles

List built-in compatibility profiles:

```bash
xiaomi-mitv-remote-profiles
```

Profiles live in `profiles/*.profile.json`. The project is Xiaomi/MiTV-first, but generic Bluetooth HID remotes can be validated through capture mode and a doctor report. See `docs/compatibility.md`.

## Setup wizard

Prepare a local project folder and print the exact next commands:

```bash
xiaomi-mitv-remote-setup --init-keymap --print-systemd
```

Use `--dry-run` to inspect what would be written without changing files.

## Keymap capture

Capture a keymap interactively from a real remote:

```bash
sudo LKR_ROOT="$PWD" LKR_GRAB=0 xiaomi-mitv-remote-capture
```

Or generate a keymap non-interactively if you already know Linux key codes:

```bash
xiaomi-mitv-remote-capture --from-codes-json '{"up":103,"down":108,"center":353}'
```

## Browser integration

The daemon writes a JavaScript bridge file by default:

```text
data/remote-action.js
```

It contains:

```js
window.KIOSK_REMOTE_ACTION = {
  seq: 1,
  action: "up",
  label: "Up",
  source: { code: 103, code_text: "KEY_UP" },
  ts: "2026-07-11T12:00:00"
};
```

A static kiosk can include or reload that file, or use the localhost long-poll endpoint:

```js
let seq = 0;
async function pollRemote() {
  const res = await fetch(`http://127.0.0.1:8793/action?since=${seq}&timeout=15`);
  const data = await res.json();
  if (data.ok && data.seq > seq) {
    seq = data.seq;
    handleRemoteAction(data.payload.action);
  }
  pollRemote();
}
pollRemote();
```

See `examples/static-html-kiosk/index.html` for a tiny browser demo. For stack integration, see `examples/integration/linux-tv-kiosk-shell/`.

## Doctor / safe diagnostics

Generate a redacted diagnostics report for issues, hardware validation, or kiosk handoff without mutating the device:

```bash
LKR_ROOT="$PWD" LKR_REMOTE_MAC="AA:BB:CC:DD:EE:FF" xiaomi-mitv-remote-doctor --output remote-doctor.json
```

The report includes environment facts, keymap validation, Bluetooth controller/device status, matching input events, daemon state, and recommendations. By default it redacts MAC addresses, hostnames, and local paths. Use `--include-journal` only when you are ready to review the redacted Bluetooth journal excerpt before sharing it.

## Status exporter

Run once:

```bash
LKR_ROOT="$PWD" LKR_REMOTE_MAC="AA:BB:CC:DD:EE:FF" xiaomi-mitv-remote-status
xiaomi-mitv-remote-doctor
```

Run as a loop:

```bash
LKR_ROOT="$PWD" LKR_REMOTE_MAC="AA:BB:CC:DD:EE:FF" xiaomi-mitv-remote-status --loop --interval 5
```

The exporter writes:

```text
data/remote-status.json
data/remote-status.js
```

## Environment variables

| Variable | Default | Meaning |
| --- | --- | --- |
| `LKR_ROOT` | current working directory | Project/dashboard root. |
| `LKR_KEYMAP` | `$LKR_ROOT/data/mi-remote-keymap.json` | Keymap JSON path. |
| `LKR_ACTION_JS` | `$LKR_ROOT/data/remote-action.js` | Browser action bridge path. |
| `LKR_STATE_JSON` | `$LKR_ROOT/data/remote-daemon-state.json` | Daemon state file. |
| `LKR_DEBUG_LOG` | `$LKR_ROOT/data/remote-action-debug.jsonl` | Rotating debug log. |
| `LKR_STATUS_JSON` | `$LKR_ROOT/data/remote-status.json` | Status JSON path. |
| `LKR_STATUS_JS` | `$LKR_ROOT/data/remote-status.js` | Status JS path. |
| `LKR_REMOTE_MAC` | empty | Bluetooth MAC/Uniq to match. Recommended for stable appliances. |
| `LKR_DEVICE_NAME_REGEX` | `xiaomi\|mi rc\|android.*remote\|remote` | Name fallback matcher. |
| `LKR_EVENT_HOST` | `127.0.0.1` | Long-poll HTTP host. |
| `LKR_EVENT_PORT` | `8793` | Long-poll HTTP port. |
| `LKR_JS_GLOBAL` | `KIOSK_REMOTE_ACTION` | Global variable name in action JS. |
| `LKR_STATUS_JS_GLOBAL` | `KIOSK_REMOTE_STATUS` | Global variable name in status JS. |
| `LKR_GRAB` | `1` | Use `EVIOCGRAB`. Set `0` to observe only. |
| `LKR_VOLUME_PACTL` | `0` | If `1`, volume actions call `pactl`. |
| `LKR_NAV_DEBOUNCE_SEC` | `0.45` | Debounce for directional actions. |
| `LKR_BUTTON_DEBOUNCE_SEC` | `0.30` | Debounce for non-directional actions. |

## Documentation

- `docs/README.ru.md` — full Russian README.
- `docs/api.md` — JS/JSON/HTTP contracts.
- `docs/troubleshooting.md` — common Bluetooth/HID/kiosk issues.
- `docs/compatibility.md` — compatibility profiles and validation notes.
- `docs/udev-non-root.md` — cautious non-root input permissions guide.
- `docs/security.md` — local security model and root/input access notes.
- `docs/hardware-validation.md` — checklist for confirming a real remote.

## Systemd

Example services:

- `examples/systemd/linux-kiosk-remote-input.service`
- `examples/systemd/linux-kiosk-remote-status.service`

The input daemon usually needs root or udev permissions for `/dev/input/event*` and `EVIOCGRAB`. Root is the simplest appliance setup; a future version should include a udev-rule guide.

## Test

```bash
./scripts/smoke_test.sh
```

This runs Python syntax checks, parser/unit tests, and example keymap validation.

## Safety notes

- The daemon reads local Linux input devices only.
- The only network listener is the local endpoint on `127.0.0.1` by default.
- Do not keep Bluetooth scanning enabled forever on fragile Wi-Fi/BT chipsets. Pair interactively, then run the daemon against already-paired devices.
- Use `LKR_GRAB=0` during debugging if you want the desktop/session to still receive remote buttons.
- Treat captured raw logs as local diagnostics; they may contain MAC addresses or device names.

## Part of Linux Kiosk Stack

This project is one layer of the [Linux Kiosk Stack](https://github.com/YURII-YURII86/linux-kiosk-stack): a local-first toolkit for Linux TV kiosks, dashboards, signage screens, and appliance panels.

## Roadmap

- Hardware validation checklist for Xiaomi/MiTV remote after standalone extraction.
- More polished pair/detect/generate-keymap wizard with optional systemd installer.
- udev permissions guide for non-root operation.
- More integration examples: Electron, Python callback, Node local app.
- Device profiles for additional Bluetooth HID remotes.

## License

MIT.
