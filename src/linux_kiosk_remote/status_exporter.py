#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import time
from pathlib import Path
from typing import Any

from .common import RemoteConfig, atomic_write, parse_bluetooth_info, parse_controller, parse_input_devices, read_json, run


def input_events(config: RemoteConfig) -> list[dict[str, str]]:
    try:
        text = Path("/proc/bus/input/devices").read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    return parse_input_devices(text, remote_mac=config.remote_mac, device_name_regex=config.device_name_regex)


def bluetooth_journal(config: RemoteConfig) -> list[str]:
    rc, text = run(["journalctl", "-u", "bluetooth", "-b", "--since", "20 minutes ago", "--no-pager", "-o", "short-iso"], timeout=3.5)
    terms = ["connect", "disconnect", "hog", "hid", "gatt", "input", "failed", "error", "AuthenticationFailed"]
    if config.remote_mac:
        terms.append(re.escape(config.remote_mac.upper()))
    if config.device_name_regex:
        terms.append(config.device_name_regex)
    patterns = re.compile("|".join(terms), re.I)
    return [re.sub(r"^\d{4}-\d{2}-\d{2}T", "", line)[-220:] for line in text.splitlines() if patterns.search(line)][-10:]


def decide(info: dict[str, Any], controller: dict[str, Any], events: list[dict[str, str]], daemon: dict[str, Any], log: list[str]) -> dict[str, str]:
    daemon_events = daemon.get("events") or []
    paired = info.get("paired") is True or info.get("bonded") is True
    connected = info.get("connected") is True
    has_input = bool(events)
    log_text = "\n".join(log).lower()
    if daemon.get("status") in {"running", "action"} and daemon_events:
        return {"state": "ok", "headline": "REMOTE OK", "badge": "RUNNING", "instruction": "Remote input daemon is receiving events.", "severity": "ok"}
    if has_input and not daemon_events:
        return {"state": "daemon_waiting", "headline": "INPUT EVENT PRESENT", "badge": "RESTART", "instruction": "Input event exists; restart or inspect the input daemon.", "severity": "warn"}
    if not paired and info:
        return {"state": "pair_required", "headline": "PAIR REQUIRED", "badge": "PAIR", "instruction": "Remote is known but not paired/bonded.", "severity": "bad"}
    if paired and connected and not has_input:
        return {"state": "hid_wait", "headline": "BLUETOOTH CONNECTED, NO INPUT", "badge": "HID", "instruction": "Press a remote button and wait for the HID input node.", "severity": "warn"}
    if "authenticationfailed" in log_text:
        return {"state": "auth_failed", "headline": "PAIRING REJECTED", "badge": "AUTH", "instruction": "Pairing failed; put the remote in pairing mode again.", "severity": "bad"}
    if paired and not connected:
        return {"state": "press_to_wake", "headline": "PRESS TO WAKE", "badge": "WAKE", "instruction": "Remote is paired but not connected. Press any button.", "severity": "warn"}
    if controller.get("discovering") is True:
        return {"state": "scan_active", "headline": "SCAN ACTIVE", "badge": "SCAN", "instruction": "Bluetooth scan is active; avoid leaving it on forever on fragile adapters.", "severity": "warn"}
    return {"state": "unknown", "headline": "REMOTE NOT READY", "badge": "CHECK", "instruction": "Check bluetoothctl info, input nodes, and daemon state.", "severity": "warn"}


def build_status(config: RemoteConfig) -> dict[str, Any]:
    info: dict[str, Any] = {}
    if config.remote_mac:
        _, info_text = run(["bluetoothctl", "info", config.remote_mac.upper()], timeout=2.5)
        info = parse_bluetooth_info(info_text)
    _, controller_text = run(["bluetoothctl", "show"], timeout=2.5)
    controller = parse_controller(controller_text)
    events = input_events(config)
    daemon = read_json(config.state_json, {})
    timestamp = dt.datetime.now().isoformat(timespec="seconds")
    facts = f"{timestamp} facts: paired={info.get('paired')} connected={info.get('connected')} input={bool(events)} daemon={daemon.get('status')}"
    log = (bluetooth_journal(config) + [facts])[-14:]
    decision = decide(info, controller, events, daemon, log)
    return {
        "updated": timestamp,
        "remote_mac_configured": bool(config.remote_mac),
        **decision,
        "device": {"name": info.get("name") or info.get("alias"), "paired": info.get("paired"), "bonded": info.get("bonded"), "trusted": info.get("trusted"), "blocked": info.get("blocked"), "connected": info.get("connected"), "hid_uuid": bool(info.get("hid_uuid")), "rssi": info.get("rssi")},
        "controller": {"powered": controller.get("powered"), "discoverable": controller.get("discoverable"), "pairable": controller.get("pairable"), "discovering": controller.get("discovering")},
        "input": {"present": bool(events), "events": events},
        "daemon": {"status": daemon.get("status"), "events": daemon.get("events") or [], "seq": daemon.get("seq"), "updated": daemon.get("updated")},
        "log": log,
    }


def write_status(config: RemoteConfig, status: dict[str, Any]) -> None:
    atomic_write(config.status_json, json.dumps(status, ensure_ascii=False, indent=2) + "\n")
    atomic_write(config.status_js, f"window.{config.status_js_global} = " + json.dumps(status, ensure_ascii=False, separators=(",", ":")) + ";\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--interval", type=float, default=5.0)
    args = parser.parse_args()
    config = RemoteConfig.from_env()
    while True:
        status = build_status(config)
        write_status(config, status)
        print(f"remote-status {status['updated']} {status['state']} {status['headline']}", flush=True)
        if not args.loop:
            return 0
        time.sleep(max(2.0, args.interval))

if __name__ == "__main__":
    raise SystemExit(main())
