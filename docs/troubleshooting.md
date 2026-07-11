# Troubleshooting

## The remote is paired but no input event appears

Press a button after pairing. Many Bluetooth HID remotes sleep and only create an input node after wake.

Check:

```bash
bluetoothctl info AA:BB:CC:DD:EE:FF
cat /proc/bus/input/devices
```

If the device is connected but no `/dev/input/event*` appears, reconnect the remote or restart Bluetooth. Avoid leaving Bluetooth scan running forever on weak Wi-Fi/BT combo adapters.

## `/dev/input/eventN` changes after reboot

That is normal. Do not hardcode event numbers in app logic. The daemon discovers matching event nodes at runtime and falls back to key codes from the JSON keymap.

## Buttons trigger twice

Some remotes expose multiple HID interfaces. The daemon debounces both per action and per event/code pair. Tune:

```bash
LKR_NAV_DEBOUNCE_SEC=0.45
LKR_BUTTON_DEBOUNCE_SEC=0.30
```

## Browser or window manager still receives Back/Home

Use grab mode:

```bash
LKR_GRAB=1
```

Run with permissions that allow `EVIOCGRAB`, usually root in appliance deployments. During debugging, use `LKR_GRAB=0`.

## Permission denied for `/dev/input/event*`

The simplest kiosk/appliance setup is running the daemon as root through systemd. A more desktop-friendly setup is a udev rule that gives a specific group access to matching input devices; this project does not ship a universal udev rule yet because device IDs vary.

## Volume buttons do not change system volume

By default the daemon only emits actions. To let volume actions call `pactl`:

```bash
LKR_VOLUME_PACTL=1
```

The host must have PulseAudio/PipeWire compatibility and `pactl` available.

## I do not know the key codes

Use capture mode:

```bash
sudo LKR_ROOT="$PWD" LKR_GRAB=0 xiaomi-mitv-remote-capture
```

Or non-interactive conversion if you already know codes:

```bash
xiaomi-mitv-remote-capture --from-codes-json '{"up":103,"down":108,"center":353}'
```

## The status exporter says `scan_active`

Bluetooth discovery is active. That is useful for pairing, but should not be left on forever on fragile adapters.

```bash
bluetoothctl scan off
```


## Generate a safe diagnostics report

Run:

```bash
LKR_ROOT="$PWD" xiaomi-mitv-remote-doctor --output remote-doctor.json
```

The report is redacted by default and is the preferred first artifact for bug reports and hardware validation notes. Review it before sharing if you used `--include-journal`.
