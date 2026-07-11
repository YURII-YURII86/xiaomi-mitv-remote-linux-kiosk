# Hardware validation checklist

This standalone package has parser/unit tests, but a real remote should be validated before claiming hardware support for a specific model.

## Checklist

1. Pair the remote through your normal Linux Bluetooth flow.
2. Confirm `bluetoothctl info <MAC>` shows the remote as paired and connected after pressing a button.
3. Confirm `/proc/bus/input/devices` contains one or more matching input devices.
4. Copy `examples/mi-remote-keymap.example.json` to `data/mi-remote-keymap.json`.
5. Run the daemon with `LKR_GRAB=0` first:

```bash
sudo LKR_ROOT="$PWD" LKR_GRAB=0 LKR_REMOTE_MAC="AA:BB:CC:DD:EE:FF" xiaomi-mitv-remote-input
```

6. Press directional, center, back, home, menu, and volume buttons.
7. Check `data/remote-action.js` and `data/remote-daemon-state.json`.
8. Open `examples/static-html-kiosk/index.html` and verify the visible action changes.
9. Repeat with `LKR_GRAB=1` in kiosk mode and verify the browser/window manager no longer steals buttons.
10. Run the status exporter and inspect `data/remote-status.json`.

## What to record

- Remote brand/model.
- Linux distribution and kernel.
- Bluetooth adapter/chipset.
- Whether the remote exposes one or multiple `/dev/input/event*` nodes.
- Any key codes that differ from the example keymap.
