# Xiaomi MiTV Remote SDK for Linux Kiosks

A small, dependency-free Python SDK/toolkit that turns a Xiaomi MiTV / Android TV Bluetooth remote into safe input events for a local Linux kiosk or TV dashboard.

It was written and tested around a Xiaomi/MiTV-style Bluetooth remote, but the core is generic Linux HID input handling: other Bluetooth remotes can work if they expose EV_KEY events and have a keymap.


## Naming

This project keeps Xiaomi/MiTV in the name on purpose: that is the concrete, recognizable remote family it was built for and tested with. Internally, the SDK is intentionally generic and can support other Bluetooth HID remotes through device matching and JSON keymaps.

## What it does

- Discovers current `/dev/input/eventN` nodes from `/proc/bus/input/devices`.
- Matches remotes by Bluetooth MAC/Uniq, device name regex, or vendor/product tokens.
- Reads Linux `EV_KEY` events directly.
- Optionally grabs devices with `EVIOCGRAB` so Firefox/Chromium/window manager do not also consume the buttons.
- Debounces duplicate button events across multiple HID interfaces.
- Writes a browser-friendly action bridge file such as `data/remote-action.js`.
- Exposes a local long-poll HTTP endpoint for apps that prefer fetch/WebSocket-like polling.
- Exports status JSON/JS for a dashboard card.

## Install from source

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

No third-party Python package is required for the daemon itself.

## Minimal keymap

```bash
mkdir -p data
cp examples/mi-remote-keymap.example.json data/mi-remote-keymap.json
```

Event node numbers in the example are placeholders. At runtime the daemon resolves by key code fallback so `/dev/input/eventN` can change after reboot.

## Run in the foreground

```bash
sudo \
  LKR_ROOT="$PWD" \
  LKR_REMOTE_MAC="AA:BB:CC:DD:EE:FF" \
  LKR_DEVICE_NAME_REGEX="xiaomi|mi rc|android.*remote|remote" \
  python3 -m linux_kiosk_remote.input_daemon
```

Your kiosk page can include `data/remote-action.js` or poll the local endpoint:

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

## Status exporter

```bash
LKR_ROOT="$PWD" LKR_REMOTE_MAC="AA:BB:CC:DD:EE:FF" python3 -m linux_kiosk_remote.status_exporter
```

Writes `data/remote-status.json` and `data/remote-status.js`.

## Environment variables

| Variable | Default | Meaning |
| --- | --- | --- |
| `LKR_ROOT` | current working directory | Project/dashboard root. |
| `LKR_KEYMAP` | `$LKR_ROOT/data/mi-remote-keymap.json` | Keymap JSON path. |
| `LKR_ACTION_JS` | `$LKR_ROOT/data/remote-action.js` | Browser action bridge path. |
| `LKR_STATE_JSON` | `$LKR_ROOT/data/remote-daemon-state.json` | Daemon state file. |
| `LKR_DEBUG_LOG` | `$LKR_ROOT/data/remote-action-debug.jsonl` | Rotating debug log. |
| `LKR_REMOTE_MAC` | empty | Bluetooth MAC/Uniq to match. Recommended. |
| `LKR_DEVICE_NAME_REGEX` | `xiaomi|mi rc|android.*remote|remote` | Name fallback matcher. |
| `LKR_EVENT_HOST` | `127.0.0.1` | Long-poll HTTP host. |
| `LKR_EVENT_PORT` | `8793` | Long-poll HTTP port. |
| `LKR_JS_GLOBAL` | `KIOSK_REMOTE_ACTION` | Global variable name in action JS. |
| `LKR_GRAB` | `1` | Use EVIOCGRAB. Set `0` to observe only. |
| `LKR_VOLUME_PACTL` | `0` | If `1`, volume actions call `pactl`. |

## Systemd

See `examples/systemd/linux-kiosk-remote-input.service` and `examples/systemd/linux-kiosk-remote-status.service`.

The input daemon usually needs root or membership/udev permissions for `/dev/input/event*`; root is simplest for kiosk appliances.

## Safety notes

- The daemon reads local Linux input devices only; it does not open network sockets except the localhost status/action endpoint.
- Do not keep Bluetooth scanning enabled forever on fragile Wi-Fi/BT chipsets. Pair interactively, then run the daemon against already-paired devices.
- Use `LKR_GRAB=0` during debugging if you want the desktop/session to still receive remote buttons.
- Treat captured raw logs as local diagnostics; they may contain MAC addresses or device names.

## License

MIT.
