# udev and non-root operation

The simplest appliance setup is running `xiaomi-mitv-remote-input` as root under systemd. That is common for kiosks, but not ideal for every system.

A non-root setup needs permission to read `/dev/input/event*` and, if used, permission for `EVIOCGRAB`.

## Safe process

1. Pair the remote.
2. Press a button to wake it.
3. Run a redacted report:

```bash
LKR_ROOT="$PWD" xiaomi-mitv-remote-doctor --output remote-doctor.json
```

4. Locally inspect exact device identity:

```bash
cat /proc/bus/input/devices
udevadm info --attribute-walk --name=/dev/input/eventN
```

5. Create the narrowest udev rule you can.
6. Add the daemon user to the selected group.
7. Replug/reconnect the remote.
8. Test with `LKR_GRAB=0` first.

## Why this repo does not ship a universal rule

A broad input rule can grant access to keyboards and other sensitive devices. Bluetooth remote identities vary by revision and Linux Bluetooth stack. A universal rule would be convenient but unsafe.

See `examples/udev/99-xiaomi-mitv-remote.rules.example` for a starting point, not a copy-paste answer.
