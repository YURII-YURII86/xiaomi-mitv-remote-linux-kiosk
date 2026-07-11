#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import select
import struct
import time
from pathlib import Path
from typing import Any

from .common import RemoteConfig, now, parse_input_devices, run
from .doctor import build_report, redact_obj
from .keymap import DEFAULT_ACTION_SEQUENCE, build_keymap_from_codes, validate_keymap, write_keymap
from .profiles import load_profiles

EV_KEY = 1
INPUT_EVENT_FMT = "llHHI"
INPUT_EVENT_SIZE = struct.calcsize(INPUT_EVENT_FMT)
RECOMMENDED_ACTIONS = ["up", "down", "left", "right", "center", "back"]


def read_proc_events(config: RemoteConfig) -> list[dict[str, str]]:
    try:
        text = Path("/proc/bus/input/devices").read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    return parse_input_devices(text, remote_mac=config.remote_mac, device_name_regex=config.device_name_regex)


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


def read_next_keycode(fds: list[int], timeout: float) -> int | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        readable, _, _ = select.select(fds, [], [], min(0.5, max(0.05, deadline - time.monotonic())))
        for fd in readable:
            raw = os.read(fd, INPUT_EVENT_SIZE * 64)
            for offset in range(0, len(raw) - INPUT_EVENT_SIZE + 1, INPUT_EVENT_SIZE):
                _sec, _usec, event_type, code, value = struct.unpack(INPUT_EVENT_FMT, raw[offset:offset + INPUT_EVENT_SIZE])
                if event_type == EV_KEY and value == 1:
                    return int(code)
    return None


def capture_interactive(events: list[dict[str, str]], actions: list[str], timeout: float) -> dict[str, int]:
    fds = open_event_fds(events)
    codes: dict[str, int] = {}
    labels = dict(DEFAULT_ACTION_SEQUENCE)
    try:
        for action in actions:
            input(f"Press {labels.get(action, action)} ({action}), then Enter to arm capture... ")
            print(f"Waiting for {action} for up to {timeout:.0f}s...")
            code = read_next_keycode(fds, timeout)
            if code is None:
                print(f"  skipped {action}: timeout")
                continue
            codes[action] = code
            print(f"  captured {action}: code={code}")
    finally:
        close_fds(fds)
    return codes


def check_status(value: bool, ok: str, bad: str) -> dict[str, Any]:
    return {"ok": bool(value), "message": ok if value else bad}


def build_lab_report(config: RemoteConfig, *, codes: dict[str, int] | None = None, profile_id: str = "xiaomi-mitv-remote", include_journal: bool = False) -> dict[str, Any]:
    doctor = build_report(config, include_journal=include_journal)
    events = read_proc_events(config)
    profiles = load_profiles()
    selected_profile = next((p for p in profiles if p.get("id") == profile_id), None)

    captured_keymap: dict[str, Any] | None = None
    captured_validation: dict[str, Any] | None = None
    captured_actions: list[str] = []
    if codes:
        captured_keymap = build_keymap_from_codes(codes, mac=config.remote_mac)
        captured_validation = validate_keymap(captured_keymap)
        captured_actions = sorted(codes)

    bt_device = doctor.get("bluetooth", {}).get("device", {}) if isinstance(doctor.get("bluetooth"), dict) else {}
    checks = {
        "bluetoothctlAvailable": check_status(bool(doctor.get("environment", {}).get("commands", {}).get("bluetoothctl")), "bluetoothctl found", "bluetoothctl not found"),
        "profileKnown": check_status(selected_profile is not None, "profile found", f"profile not found: {profile_id}"),
        "keymapValid": check_status(bool(doctor.get("keymap", {}).get("ok")), "configured keymap valid", "configured keymap missing or invalid"),
        "paired": check_status(bt_device.get("paired") is True or bt_device.get("bonded") is True, "remote paired/bonded", "remote not confirmed paired/bonded"),
        "connected": check_status(bt_device.get("connected") is True, "remote connected", "remote not confirmed connected"),
        "inputEvent": check_status(bool(events), "matching input event found", "no matching input event found"),
        "capturedRecommendedActions": check_status(all(a in captured_actions for a in RECOMMENDED_ACTIONS), "recommended actions captured", "recommended actions not fully captured"),
        "firstRunGrabSafe": check_status(config.grab is False, "LKR_GRAB=0 for first validation", "set LKR_GRAB=0 for first validation"),
    }
    safe_to_claim = all(checks[k]["ok"] for k in ["bluetoothctlAvailable", "profileKnown", "keymapValid", "paired", "connected", "inputEvent", "capturedRecommendedActions"])
    report = {
        "schema": "xiaomi-mitv-remote-linux-kiosk.lab-report.v1",
        "createdAt": now(),
        "profileId": profile_id,
        "selectedProfile": selected_profile,
        "mode": "hardware-validation" if codes else "diagnostic-only",
        "checks": checks,
        "capturedActions": captured_actions,
        "capturedKeymapValidation": captured_validation,
        "safeToClaimHardwareVerified": bool(safe_to_claim),
        "recommendations": lab_recommendations(checks, doctor),
        "doctor": doctor,
    }
    if captured_keymap is not None:
        report["capturedKeymap"] = captured_keymap
    return redact_obj(report)


def lab_recommendations(checks: dict[str, Any], doctor: dict[str, Any]) -> list[str]:
    out: list[str] = []
    if not checks["firstRunGrabSafe"]["ok"]:
        out.append("Run first validation with LKR_GRAB=0; enable grab only after event/action flow is confirmed.")
    if not checks["inputEvent"]["ok"]:
        out.append("Pair the remote, press a button to wake it, then rerun lab/doctor.")
    if not checks["capturedRecommendedActions"]["ok"]:
        out.append("Capture at least up/down/left/right/center/back before claiming hardware validation.")
    out.extend(doctor.get("recommendations", []))
    # Preserve order while removing duplicates.
    deduped: list[str] = []
    for item in out:
        if item not in deduped:
            deduped.append(item)
    return deduped


def parse_codes_json(value: str) -> dict[str, int]:
    raw = json.loads(value)
    if not isinstance(raw, dict):
        raise ValueError("codes JSON must be an object action->code")
    return {str(k): int(v) for k, v in raw.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Guided validation lab for Xiaomi/MiTV Bluetooth remotes on Linux kiosks.")
    parser.add_argument("--output", default="hardware-validation-report.json", help="Report output path.")
    parser.add_argument("--profile", default="xiaomi-mitv-remote", help="Compatibility profile id.")
    parser.add_argument("--from-codes-json", help="Non-interactive action->code JSON for CI/manual conversion.")
    parser.add_argument("--capture", action="store_true", help="Interactively capture key codes from matching input events.")
    parser.add_argument("--actions", default=",".join(RECOMMENDED_ACTIONS + ["home", "menu", "volume_up", "volume_down"]), help="Comma-separated actions for --capture.")
    parser.add_argument("--timeout", type=float, default=20.0, help="Seconds to wait for each captured action.")
    parser.add_argument("--write-keymap", help="Write captured/generated keymap to this path. Not used unless explicitly set.")
    parser.add_argument("--include-journal", action="store_true", help="Include redacted recent bluetooth journal lines in embedded doctor report.")
    args = parser.parse_args()

    config = RemoteConfig.from_env()
    codes: dict[str, int] | None = None
    if args.from_codes_json:
        codes = parse_codes_json(args.from_codes_json)
    elif args.capture:
        events = read_proc_events(config)
        if not events:
            print("No matching input events found. Pair/wake the remote or tune LKR_REMOTE_MAC / LKR_DEVICE_NAME_REGEX.")
            codes = {}
        else:
            actions = [a.strip() for a in args.actions.split(",") if a.strip()]
            codes = capture_interactive(events, actions, args.timeout)

    report = build_lab_report(config, codes=codes, profile_id=args.profile, include_journal=args.include_journal)
    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output}")
    print(f"safeToClaimHardwareVerified={report['safeToClaimHardwareVerified']}")

    if args.write_keymap:
        if not codes:
            print("not writing keymap: no captured/generated codes")
        else:
            keymap = build_keymap_from_codes(codes, mac=config.remote_mac)
            validate_keymap(keymap)
            write_keymap(Path(args.write_keymap).expanduser(), keymap)
            print(f"wrote keymap {args.write_keymap}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
