#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from .common import RemoteConfig, parse_input_devices, run


def copy_example_keymap(root: Path, target: Path, overwrite: bool) -> bool:
    candidates = [
        root / "examples" / "mi-remote-keymap.example.json",
        Path(__file__).resolve().parents[2] / "examples" / "mi-remote-keymap.example.json",
    ]
    src = next((p for p in candidates if p.exists()), None)
    if src is None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"device": "Xiaomi / MiTV Bluetooth remote", "mac": "AA:BB:CC:DD:EE:FF", "keys": {}}, indent=2) + "\n")
        return True
    if target.exists() and not overwrite:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, target)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a local Xiaomi/MiTV remote Linux kiosk project folder.")
    parser.add_argument("--root", default=None, help="Project root. Defaults to LKR_ROOT or current directory.")
    parser.add_argument("--mac", default=None, help="Remote MAC to show/write in .env example.")
    parser.add_argument("--init-keymap", action="store_true", help="Copy example keymap to data/mi-remote-keymap.json if missing.")
    parser.add_argument("--overwrite-keymap", action="store_true", help="Overwrite existing keymap when used with --init-keymap.")
    parser.add_argument("--print-systemd", action="store_true", help="Print systemd install hints.")
    parser.add_argument("--dry-run", action="store_true", help="Print checks without writing files.")
    args = parser.parse_args()

    config = RemoteConfig.from_env()
    root = Path(args.root).expanduser().resolve() if args.root else config.root
    keymap = root / "data" / "mi-remote-keymap.json"
    mac = args.mac or config.remote_mac or "AA:BB:CC:DD:EE:FF"

    print(f"root: {root}")
    print(f"keymap: {keymap}")
    print(f"remote mac: {mac}")

    for cmd in (["bluetoothctl", "show"], ["python3", "--version"]):
        rc, out = run(cmd, timeout=3)
        print(f"check {' '.join(cmd)}: rc={rc}")
        if out:
            print("  " + out.splitlines()[0][:160])

    try:
        devices_text = Path("/proc/bus/input/devices").read_text(encoding="utf-8", errors="replace")
        events = parse_input_devices(devices_text, remote_mac=mac if mac != "AA:BB:CC:DD:EE:FF" else "", device_name_regex=config.device_name_regex)
        print(f"matching input events now: {len(events)}")
        for event in events:
            print(f"  {event['path']} {event['name']} {event.get('uniq') or ''}")
    except Exception as exc:
        print(f"input device scan unavailable: {type(exc).__name__}: {exc}")

    if args.init_keymap:
        if args.dry_run:
            print(f"dry-run: would create/copy {keymap}")
        else:
            changed = copy_example_keymap(root, keymap, args.overwrite_keymap)
            print(("created/updated" if changed else "already exists") + f": {keymap}")

    env_text = "\n".join([
        f"LKR_ROOT={root}",
        f"LKR_REMOTE_MAC={mac}",
        "LKR_DEVICE_NAME_REGEX=xiaomi|mi rc|android.*remote|remote",
        "LKR_EVENT_HOST=127.0.0.1",
        "LKR_EVENT_PORT=8793",
        "LKR_GRAB=1",
        "",
    ])
    print("\nSuggested .env:")
    print(env_text)

    print("Next commands:")
    print(f"  sudo LKR_ROOT='{root}' LKR_REMOTE_MAC='{mac}' LKR_GRAB=0 xiaomi-mitv-remote-input")
    print("  open examples/static-html-kiosk/index.html in your kiosk browser")

    if args.print_systemd:
        print("\nSystemd examples are in examples/systemd/. Copy them to /etc/systemd/system/ after editing WorkingDirectory and LKR_REMOTE_MAC.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
