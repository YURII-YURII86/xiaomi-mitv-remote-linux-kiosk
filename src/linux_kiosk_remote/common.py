from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in {"yes", "true", "1", "on"}:
        return True
    if lowered in {"no", "false", "0", "off"}:
        return False
    return None


def run(cmd: list[str], timeout: float = 2.0) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        return proc.returncode, (proc.stdout + proc.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except Exception as exc:
        return 1, f"{type(exc).__name__}: {exc}"


def read_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def normalize_mac(value: str) -> str:
    return value.strip().lower()


@dataclass(frozen=True)
class RemoteConfig:
    root: Path
    keymap: Path
    action_js: Path
    state_json: Path
    debug_log: Path
    status_json: Path
    status_js: Path
    remote_mac: str
    device_name_regex: str
    event_host: str
    event_port: int
    js_global: str
    status_js_global: str
    grab: bool
    volume_pactl: bool
    debug_log_max_bytes: int
    nav_debounce_sec: float
    button_debounce_sec: float

    @classmethod
    def from_env(cls) -> "RemoteConfig":
        root = Path(os.environ.get("LKR_ROOT", os.getcwd())).expanduser().resolve()
        data = root / "data"
        return cls(
            root=root,
            keymap=Path(os.environ.get("LKR_KEYMAP", str(data / "mi-remote-keymap.json"))).expanduser(),
            action_js=Path(os.environ.get("LKR_ACTION_JS", str(data / "remote-action.js"))).expanduser(),
            state_json=Path(os.environ.get("LKR_STATE_JSON", str(data / "remote-daemon-state.json"))).expanduser(),
            debug_log=Path(os.environ.get("LKR_DEBUG_LOG", str(data / "remote-action-debug.jsonl"))).expanduser(),
            status_json=Path(os.environ.get("LKR_STATUS_JSON", str(data / "remote-status.json"))).expanduser(),
            status_js=Path(os.environ.get("LKR_STATUS_JS", str(data / "remote-status.js"))).expanduser(),
            remote_mac=normalize_mac(os.environ.get("LKR_REMOTE_MAC", "")),
            device_name_regex=os.environ.get("LKR_DEVICE_NAME_REGEX", r"xiaomi|mi rc|android.*remote|remote"),
            event_host=os.environ.get("LKR_EVENT_HOST", "127.0.0.1"),
            event_port=int(os.environ.get("LKR_EVENT_PORT", "8793")),
            js_global=os.environ.get("LKR_JS_GLOBAL", "KIOSK_REMOTE_ACTION"),
            status_js_global=os.environ.get("LKR_STATUS_JS_GLOBAL", "KIOSK_REMOTE_STATUS"),
            grab=parse_bool(os.environ.get("LKR_GRAB", "1")) is not False,
            volume_pactl=parse_bool(os.environ.get("LKR_VOLUME_PACTL", "0")) is True,
            debug_log_max_bytes=int(os.environ.get("LKR_DEBUG_LOG_MAX_BYTES", "300000")),
            nav_debounce_sec=float(os.environ.get("LKR_NAV_DEBOUNCE_SEC", "0.45")),
            button_debounce_sec=float(os.environ.get("LKR_BUTTON_DEBOUNCE_SEC", "0.30")),
        )


def parse_input_devices(text: str, *, remote_mac: str = "", device_name_regex: str = r"xiaomi|mi rc|android.*remote|remote") -> list[dict[str, str]]:
    matcher = re.compile(device_name_regex, re.I) if device_name_regex else None
    mac = normalize_mac(remote_mac)
    events: list[dict[str, str]] = []
    seen: set[str] = set()
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        name_match = re.search(r'N: Name="([^"]+)"', block)
        uniq_match = re.search(r'U: Uniq=([^\n]+)', block)
        handlers_match = re.search(r'H: Handlers=(.+)', block)
        name = name_match.group(1) if name_match else "unknown"
        uniq = normalize_mac(uniq_match.group(1)) if uniq_match else ""
        block_lower = block.lower()
        matched = False
        if mac and (mac in uniq or mac in block_lower):
            matched = True
        if not matched and matcher and matcher.search(name):
            matched = True
        if not matched or not handlers_match:
            continue
        for event_name in re.findall(r"event\d+", handlers_match.group(1)):
            path = "/dev/input/" + event_name
            if path in seen:
                continue
            seen.add(path)
            events.append({"path": path, "name": name, "uniq": uniq})
    return events


def parse_bluetooth_info(text: str) -> dict[str, Any]:
    info: dict[str, Any] = {"raw": text}
    for line in text.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower().replace(" ", "_")
        value = value.strip()
        if key in {"paired", "bonded", "trusted", "blocked", "connected", "wakeallowed"}:
            info[key] = parse_bool(value)
        elif key == "uuid" and "human interface" in value.lower():
            info["hid_uuid"] = True
        elif key in {"name", "alias", "rssi", "battery_percentage"}:
            info[key] = value
    return info


def parse_controller(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        # Header lines look like `Controller AA:BB:... host` and contain
        # colons only because of the MAC address; they are not key/value rows.
        if not line or line.startswith("Controller ") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower().replace(" ", "_")
        value = value.strip()
        if key in {"powered", "discoverable", "pairable", "discovering"}:
            out[key] = parse_bool(value)
        else:
            out[key] = value
    return out
