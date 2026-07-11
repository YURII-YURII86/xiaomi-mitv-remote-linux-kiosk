#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import select
import struct
import sys
import time
from pathlib import Path

from .common import RemoteConfig, parse_input_devices
from .keymap import DEFAULT_ACTION_SEQUENCE, build_keymap_from_codes, write_keymap

EV_KEY = 1
INPUT_EVENT_FMT = "llHHI"
INPUT_EVENT_SIZE = struct.calcsize(INPUT_EVENT_FMT)


def discover_events(config: RemoteConfig) -> list[dict[str, str]]:
    text = Path("/proc/bus/input/devices").read_text(encoding="utf-8", errors="replace")
    return parse_input_devices(text, remote_mac=config.remote_mac, device_name_regex=config.device_name_regex)


def read_next_keycode(fds: list[int], timeout: float) -> int | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        readable, _, _ = select.select(fds, [], [], min(0.5, max(0.05, deadline - time.monotonic())))
        for fd in readable:
            try:
                raw = os.read(fd, INPUT_EVENT_SIZE * 64)
            except BlockingIOError:
                continue
            for offset in range(0, len(raw) - INPUT_EVENT_SIZE + 1, INPUT_EVENT_SIZE):
                _sec, _usec, event_type, code, value = struct.unpack(INPUT_EVENT_FMT, raw[offset:offset + INPUT_EVENT_SIZE])
                if event_type == EV_KEY and value == 1:
                    return int(code)
    return None


def open_event_fds(events: list[dict[str, str]]) -> list[int]:
    fds: list[int] = []
    for event in events:
        fds.append(os.open(event["path"], os.O_RDONLY | os.O_NONBLOCK))
    return fds


def close_fds(fds: list[int]) -> None:
    for fd in fds:
        try:
            os.close(fd)
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture a Xiaomi/MiTV remote keymap from Linux EV_KEY events.")
    parser.add_argument("--output", default=None, help="Output keymap path. Defaults to LKR_KEYMAP or data/mi-remote-keymap.json.")
    parser.add_argument("--timeout", type=float, default=20.0, help="Seconds to wait for each button.")
    parser.add_argument("--mac", default=None, help="Remote MAC/Uniq override for this run.")
    parser.add_argument("--device-name-regex", default=None, help="Input device name regex override.")
    parser.add_argument("--actions", default=None, help="Comma-separated action list to capture.")
    parser.add_argument("--from-codes-json", default=None, help="Non-interactive mode: JSON object action->code for tests/manual conversion.")
    args = parser.parse_args()

    config = RemoteConfig.from_env()
    if args.mac is not None:
        os.environ["LKR_REMOTE_MAC"] = args.mac
        config = RemoteConfig.from_env()
    if args.device_name_regex is not None:
        os.environ["LKR_DEVICE_NAME_REGEX"] = args.device_name_regex
        config = RemoteConfig.from_env()

    output = Path(args.output).expanduser() if args.output else config.keymap

    if args.from_codes_json:
        codes = {str(k): int(v) for k, v in json.loads(args.from_codes_json).items()}
        keymap = build_keymap_from_codes(codes, mac=config.remote_mac)
        write_keymap(output, keymap)
        print(f"wrote {output}")
        return 0

    action_labels = DEFAULT_ACTION_SEQUENCE
    if args.actions:
        wanted = {a.strip() for a in args.actions.split(",") if a.strip()}
        action_labels = [(a, label) for a, label in DEFAULT_ACTION_SEQUENCE if a in wanted]

    events = discover_events(config)
    if not events:
        print("No matching input events found. Pair the remote, press a button, or set LKR_REMOTE_MAC / LKR_DEVICE_NAME_REGEX.", file=sys.stderr)
        return 2

    print("Matching input events:")
    for event in events:
        print(f"  {event['path']}  {event['name']}  {event.get('uniq') or ''}")

    fds = open_event_fds(events)
    codes: dict[str, int] = {}
    try:
        for action, label in action_labels:
            input(f"Press {label} ({action}), then Enter to arm capture... ")
            print(f"Waiting for {action} for up to {args.timeout:.0f}s...")
            code = read_next_keycode(fds, args.timeout)
            if code is None:
                print(f"  skipped {action}: timeout")
                continue
            codes[action] = code
            print(f"  captured {action}: code={code}")
    finally:
        close_fds(fds)

    if not codes:
        print("No keys captured; not writing keymap.", file=sys.stderr)
        return 3
    keymap = build_keymap_from_codes(codes, mac=config.remote_mac)
    write_keymap(output, keymap)
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
