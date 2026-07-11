# API contract

This SDK exposes remote button presses through small local contracts, not through a cloud service.

## Action payload

All bridges use the same action shape:

```json
{
  "seq": 12,
  "action": "up",
  "label": "Up",
  "source": {
    "action": "up",
    "label": "Up",
    "code_text": "KEY_UP",
    "event": "auto",
    "code": 103
  },
  "ts": "2026-07-11T12:00:00"
}
```

`seq` is monotonically increasing while the daemon runs. Apps should ignore payloads with a sequence number they have already handled.

## JavaScript file bridge

Default path:

```text
data/remote-action.js
```

Default global:

```js
window.KIOSK_REMOTE_ACTION = {...};
```

Override with:

```text
LKR_ACTION_JS=/path/to/remote-action.js
LKR_JS_GLOBAL=MY_REMOTE_ACTION
```

## Long-poll HTTP bridge

Default endpoint:

```text
GET http://127.0.0.1:8793/action?since=<last_seq>&timeout=15
```

Response:

```json
{
  "ok": true,
  "payload": {"seq": 13, "action": "center"},
  "seq": 13,
  "time": "2026-07-11T12:00:02"
}
```

Health endpoint:

```text
GET http://127.0.0.1:8793/health
```

Response:

```json
{"ok": true, "seq": 13, "time": "2026-07-11T12:00:03"}
```

Keep the endpoint on `127.0.0.1` unless you have a deliberate local-network security model.

## Daemon state

Default path:

```text
data/remote-daemon-state.json
```

Useful for debugging service state and discovered event nodes.

## Status exporter

Default files:

```text
data/remote-status.json
data/remote-status.js
```

Status payload includes:

- high-level state: `ok`, `press_to_wake`, `pair_required`, `daemon_waiting`, etc.;
- Bluetooth controller flags;
- paired/connected/HID facts when a MAC is configured;
- input event discovery result;
- daemon state summary.
