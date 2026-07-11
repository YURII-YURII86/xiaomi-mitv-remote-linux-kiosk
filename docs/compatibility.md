# Compatibility profiles

This project is Xiaomi/MiTV-first but internally works with Linux HID remotes that expose `EV_KEY` events.

Profiles live in `profiles/*.profile.json` and describe:

- device family name;
- matching hints;
- keymap strategy;
- validation status;
- safety notes.

List profiles:

```bash
xiaomi-mitv-remote-profiles
```

Machine-readable output:

```bash
xiaomi-mitv-remote-profiles --json
```

## Current profiles

| Profile | Status | Notes |
| --- | --- | --- |
| `xiaomi-mitv-remote` | primary target | Built around the Xiaomi/MiTV remote family. Hardware validation after standalone extraction is still pending. |
| `generic-bluetooth-hid-remote` | experimental | Use capture mode and doctor report before claiming compatibility. |

## Adding a profile

A useful profile should include:

- redacted doctor report;
- generated keymap;
- host OS/kernel/Bluetooth adapter notes;
- whether duplicate events were seen;
- whether `EVIOCGRAB` was tested;
- whether browser shell integration was tested.
