# Integration with linux-tv-kiosk-shell

This project can drive `linux-tv-kiosk-shell` through the file bridge.

Expected shell files:

```text
linux-tv-kiosk-shell/
  index.html
  data/live.js
  data/remote-action.js   <-- written by this daemon
```

Run the remote daemon with the shell folder as `LKR_ROOT`:

```bash
sudo \
  LKR_ROOT=/path/to/linux-tv-kiosk-shell \
  LKR_GRAB=0 \
  LKR_REMOTE_MAC="AA:BB:CC:DD:EE:FF" \
  xiaomi-mitv-remote-input
```

First validate with `LKR_GRAB=0`. Use `LKR_GRAB=1` only after the action bridge is confirmed.

The shell consumes:

```js
window.KIOSK_REMOTE_ACTION = { seq: 1, action: "down" };
```

Supported shell actions:

```text
up, down, left, right, center, back, home
```

For diagnostics:

```bash
LKR_ROOT=/path/to/linux-tv-kiosk-shell xiaomi-mitv-remote-doctor --output remote-doctor.json
```
