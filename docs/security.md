# Security model

This project is designed for local Linux kiosk and appliance deployments.

## Defaults

- The daemon reads local Linux input devices.
- The HTTP action endpoint binds to `127.0.0.1` by default.
- There is no cloud service and no external telemetry.
- Browser-facing output is a local JS/JSON file or a localhost endpoint.

## Sensitive local data

Raw diagnostics can include:

- Bluetooth MAC addresses;
- input device names;
- hostnames or local paths if you capture shell output;
- button timing logs.

Do not publish raw diagnostics from a real installation without reviewing them.

## Root and input access

Reading `/dev/input/event*` and using `EVIOCGRAB` require elevated permissions on many systems. Running the daemon as root under systemd is simple and common for appliance-style kiosks, but it is not the only possible model.

For multi-user desktops, prefer a narrow udev/group setup once you know the exact device identity.

## Network exposure

Do not expose the long-poll endpoint outside localhost unless you add your own authentication and threat model.

Keep:

```text
LKR_EVENT_HOST=127.0.0.1
```

unless you know why you need a different bind address.
