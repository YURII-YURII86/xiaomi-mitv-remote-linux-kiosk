#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
from pathlib import Path
from typing import Any

from .common import RemoteConfig, parse_bluetooth_info, parse_controller, parse_input_devices, read_json, run
from .keymap import validate_keymap

MAC_RE = re.compile(r"\b[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}\b")
PATH_RE = re.compile(r"(/(?:home|mnt|media|Users|opt|srv|var|tmp)/[^\s\"']+)")


def redact_text(text: str) -> str:
    text = MAC_RE.sub("AA:BB:CC:DD:EE:FF", text)
    text = text.replace(platform.node(), "HOSTNAME") if platform.node() else text
    text = PATH_RE.sub("/REDACTED/PATH", text)
    return text


def redact_obj(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: redact_obj(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_obj(v) for v in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def safe_read(path: Path, *, max_bytes: int = 200_000) -> str:
    try:
        if not path.exists() or not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")[:max_bytes]
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"


def file_summary(path: Path) -> dict[str, Any]:
    try:
        return {"path": str(path), "exists": path.exists(), "is_file": path.is_file(), "size": path.stat().st_size if path.exists() else None}
    except Exception as exc:
        return {"path": str(path), "error": f"{type(exc).__name__}: {exc}"}


def check_keymap(config: RemoteConfig) -> dict[str, Any]:
    try:
        data = json.loads(config.keymap.read_text(encoding="utf-8"))
        result = validate_keymap(data)
        return {"ok": True, **result}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def build_report(config: RemoteConfig, *, include_journal: bool = False) -> dict[str, Any]:
    proc_text = safe_read(Path("/proc/bus/input/devices"))
    events = parse_input_devices(proc_text, remote_mac=config.remote_mac, device_name_regex=config.device_name_regex) if proc_text else []
    bt_show_rc, bt_show = run(["bluetoothctl", "show"], timeout=3)
    info: dict[str, Any] = {}
    bt_info_rc = None
    if config.remote_mac:
        bt_info_rc, bt_info = run(["bluetoothctl", "info", config.remote_mac.upper()], timeout=3)
        info = parse_bluetooth_info(bt_info)
    journal: list[str] = []
    if include_journal:
        rc, text = run(["journalctl", "-u", "bluetooth", "-b", "--since", "30 minutes ago", "--no-pager", "-o", "short-iso"], timeout=5)
        journal = text.splitlines()[-80:] if rc == 0 else [text]
    report = {
        "schema": "xiaomi-mitv-remote-linux-kiosk.doctor.v1",
        "package": "xiaomi-mitv-remote-linux-kiosk",
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "hostname": platform.node(),
            "commands": {name: shutil.which(name) for name in ["bluetoothctl", "journalctl", "pactl", "python3"]},
        },
        "config": {
            "root": str(config.root),
            "keymap": str(config.keymap),
            "remoteMacConfigured": bool(config.remote_mac),
            "deviceNameRegex": config.device_name_regex,
            "grab": config.grab,
            "eventHost": config.event_host,
            "eventPort": config.event_port,
        },
        "files": {
            "keymap": file_summary(config.keymap),
            "stateJson": file_summary(config.state_json),
            "actionJs": file_summary(config.action_js),
            "statusJson": file_summary(config.status_json),
        },
        "keymap": check_keymap(config),
        "bluetooth": {
            "showReturnCode": bt_show_rc,
            "controller": parse_controller(bt_show),
            "infoReturnCode": bt_info_rc,
            "device": info,
        },
        "input": {
            "procReadable": bool(proc_text),
            "matchingEvents": events,
        },
        "daemonState": read_json(config.state_json, {}),
        "journal": journal,
        "recommendations": recommendations(config, events, info),
    }
    return redact_obj(report)


def recommendations(config: RemoteConfig, events: list[dict[str, str]], info: dict[str, Any]) -> list[str]:
    out: list[str] = []
    if not config.remote_mac:
        out.append("Set LKR_REMOTE_MAC for stable appliance installs; name regex is useful for discovery but less deterministic.")
    if not config.keymap.exists():
        out.append("Create a keymap with xiaomi-mitv-remote-setup --init-keymap or xiaomi-mitv-remote-capture.")
    if info and info.get("paired") is not True and info.get("bonded") is not True:
        out.append("Remote appears not paired/bonded; pair it before running the input daemon.")
    if info and info.get("connected") is not True:
        out.append("Remote is not connected; press a button to wake it after pairing.")
    if not events:
        out.append("No matching input events found; press a button, check /proc/bus/input/devices, or tune LKR_DEVICE_NAME_REGEX.")
    if config.grab:
        out.append("For first validation use LKR_GRAB=0; switch to LKR_GRAB=1 only after confirming events.")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a safe redacted diagnostics report for Xiaomi/MiTV Linux kiosk remote setups.")
    parser.add_argument("--output", help="Write report JSON to this path instead of stdout.")
    parser.add_argument("--include-journal", action="store_true", help="Include redacted recent bluetooth journal lines.")
    parser.add_argument("--no-redact", action="store_true", help="Do not redact MAC/host/path values. Use only for private local debugging.")
    args = parser.parse_args()
    config = RemoteConfig.from_env()
    report = build_report(config, include_journal=args.include_journal)
    if args.no_redact:
        report = build_report(config, include_journal=args.include_journal)
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).expanduser().write_text(text, encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
