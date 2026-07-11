# Hardware validation

This repository separates parser/CI verification from real hardware verification.

Use `xiaomi-mitv-remote-lab` to produce a machine-readable validation artifact before claiming a remote/host combination is hardware-verified.

## Safe first run

Do not start with grab mode. First validation should use:

```bash
LKR_ROOT="$PWD" LKR_GRAB=0 xiaomi-mitv-remote-lab --output hardware-validation-report.json
```

This does not mutate the device or write a keymap unless `--write-keymap` is explicitly passed.

## Real capture flow

After pairing the remote and pressing a button to wake it:

```bash
sudo   LKR_ROOT="$PWD"   LKR_GRAB=0   LKR_REMOTE_MAC="AA:BB:CC:DD:EE:FF"   xiaomi-mitv-remote-lab   --capture   --output hardware-validation-report.json   --write-keymap data/mi-remote-keymap.json
```

Recommended captured actions before claiming compatibility:

```text
up, down, left, right, center, back
```

## CI/manual conversion flow

If you already know key codes:

```bash
xiaomi-mitv-remote-lab   --from-codes-json '{"up":103,"down":108,"left":105,"right":106,"center":353,"back":158}'   --output hardware-validation-report.json   --write-keymap data/mi-remote-keymap.json
```

## Report meaning

The lab report has schema:

```text
xiaomi-mitv-remote-linux-kiosk.lab-report.v1
```

Important fields:

- `checks.bluetoothctlAvailable`
- `checks.profileKnown`
- `checks.keymapValid`
- `checks.paired`
- `checks.connected`
- `checks.inputEvent`
- `checks.capturedRecommendedActions`
- `checks.firstRunGrabSafe`
- `safeToClaimHardwareVerified`
- `capturedActions`
- embedded redacted `doctor` report

`safeToClaimHardwareVerified=true` should only appear after the remote is paired, connected, exposes a matching input event, has a valid keymap, and captures the recommended actions.

## What to record in docs/README later

- Remote brand/model.
- Linux distribution and kernel.
- Bluetooth adapter/chipset.
- Whether the remote exposes one or multiple `/dev/input/event*` nodes.
- Generated keymap or deviations from the example.
- Lab report summary.

Example redacted report: `examples/reports/hardware-validation-report.example.json`.
