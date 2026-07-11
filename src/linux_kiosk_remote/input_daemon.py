#!/usr/bin/env python3
from __future__ import annotations

import fcntl
import json
import os
import select
import signal
import struct
import subprocess
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .common import RemoteConfig, atomic_write, now, parse_input_devices

EV_KEY = 1
EVIOCGRAB = 0x40044590
INPUT_EVENT_FMT = "llHHI"
INPUT_EVENT_SIZE = struct.calcsize(INPUT_EVENT_FMT)
NAV_ACTIONS = {"up", "down", "left", "right"}

running = True
opened: list[tuple[int, dict[str, str]]] = []
opened_signature: tuple[str, ...] = ()
seq = 0
reverse_by_event: dict[tuple[str, int], dict[str, Any]] = {}
reverse_by_code: dict[int, dict[str, Any]] = {}
latest_payload: dict[str, Any] = {"seq": 0, "action": "idle", "label": "idle", "ts": ""}
latest_cond = threading.Condition()
config = RemoteConfig.from_env()


def append_debug(kind: str, payload: dict[str, Any] | None = None) -> None:
    try:
        if config.debug_log.exists() and config.debug_log.stat().st_size > config.debug_log_max_bytes:
            config.debug_log.replace(config.debug_log.with_suffix(config.debug_log.suffix + ".1"))
        row: dict[str, Any] = {"time": now(), "kind": kind}
        if payload:
            row.update(payload)
        config.debug_log.parent.mkdir(parents=True, exist_ok=True)
        with config.debug_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    except Exception:
        pass


def publish_payload(payload: dict[str, Any]) -> None:
    global latest_payload
    with latest_cond:
        latest_payload = dict(payload)
        latest_cond.notify_all()


def log_state(status: str, extra: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {"updated": now(), "status": status, "events": [event for _, event in opened], "seq": seq}
    if extra:
        payload.update(extra)
    atomic_write(config.state_json, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def write_action(action: str, label: str, source: dict[str, Any]) -> None:
    global seq
    seq += 1
    payload = {"seq": seq, "action": action, "label": label, "source": source, "ts": now()}
    atomic_write(config.action_js, f"window.{config.js_global} = " + json.dumps(payload, ensure_ascii=False) + ";\n")
    publish_payload(payload)
    append_debug("accepted", payload)
    log_state("action", payload)


def run_volume(action: str) -> None:
    if not config.volume_pactl:
        return
    cmd = ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+5%" if action == "volume_up" else "-5%"]
    try:
        subprocess.run(cmd, timeout=2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def load_keymap() -> None:
    if not config.keymap.exists():
        raise FileNotFoundError(f"keymap not found: {config.keymap}")
    data = json.loads(config.keymap.read_text(encoding="utf-8"))
    for action, item in data.get("keys", {}).items():
        code = item.get("code")
        if code is None:
            continue
        mapped = {"action": action, "label": item.get("label") or action, "code_text": item.get("code_text"), "event": item.get("event"), "code": int(code)}
        reverse_by_code[int(code)] = mapped
        if item.get("event"):
            reverse_by_event[(str(item["event"]), int(code))] = mapped


def find_events() -> list[dict[str, str]]:
    text = Path("/proc/bus/input/devices").read_text(encoding="utf-8", errors="replace")
    return parse_input_devices(text, remote_mac=config.remote_mac, device_name_regex=config.device_name_regex)


def event_signature(events: list[dict[str, str]]) -> tuple[str, ...]:
    return tuple(sorted(event.get("path", "") for event in events))


def open_events(events: list[dict[str, str]]) -> None:
    global opened_signature
    opened_signature = event_signature(events)
    for event in events:
        fd = os.open(event["path"], os.O_RDONLY | os.O_NONBLOCK)
        if config.grab:
            fcntl.ioctl(fd, EVIOCGRAB, 1)
        opened.append((fd, event))


def close_events() -> None:
    global opened_signature
    for fd, _ in list(opened):
        try:
            if config.grab:
                fcntl.ioctl(fd, EVIOCGRAB, 0)
        except Exception:
            pass
        try:
            os.close(fd)
        except Exception:
            pass
    opened.clear()
    opened_signature = ()


class RemoteEventHandler(BaseHTTPRequestHandler):
    server_version = "LinuxKioskRemoteInput/0.1"
    def log_message(self, fmt: str, *args: object) -> None: return
    def _headers(self, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Content-Type", "application/json; charset=utf-8")
    def do_OPTIONS(self) -> None:
        self._headers(204); self.end_headers()
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/health":
            body = json.dumps({"ok": True, "seq": latest_payload.get("seq", 0), "time": now()}, ensure_ascii=False).encode()
            self._headers(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        if parsed.path != "/action":
            body = b'{"ok":false,"error":"not_found"}\n'
            self._headers(404); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        query = urllib.parse.parse_qs(parsed.query)
        try: since = int((query.get("since") or ["-1"])[0])
        except Exception: since = -1
        try: timeout = max(0.1, min(15.0, float((query.get("timeout") or ["10"])[0])))
        except Exception: timeout = 10.0
        deadline = time.monotonic() + timeout
        with latest_cond:
            while running and int(latest_payload.get("seq") or 0) <= since:
                left = deadline - time.monotonic()
                if left <= 0: break
                latest_cond.wait(timeout=left)
            payload = dict(latest_payload)
        body = json.dumps({"ok": True, "payload": payload, "seq": payload.get("seq", 0), "time": now()}, ensure_ascii=False).encode()
        self._headers(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)


def start_event_server() -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((config.event_host, config.event_port), RemoteEventHandler)
    thread = threading.Thread(target=server.serve_forever, name="linux-kiosk-remote-http", daemon=True)
    thread.start()
    return server


def handle_stop(signum: int, frame: object) -> None:
    global running
    running = False


def main() -> int:
    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)
    idle = {"seq": 0, "action": "idle", "label": "idle", "ts": now()}
    atomic_write(config.action_js, f"window.{config.js_global} = " + json.dumps(idle, ensure_ascii=False) + ";\n")
    publish_payload(idle)
    load_keymap()
    httpd = start_event_server()
    last_by_event: dict[tuple[str, int], float] = {}
    last_by_action: dict[str, float] = {}
    last_rebind_check = 0.0
    try:
        while running:
            events = find_events()
            if not events:
                log_state("waiting-events", {"code_count": len(reverse_by_code), "event_count": 0})
                time.sleep(2); continue
            try:
                open_events(events)
            except Exception as exc:
                log_state("open-error-waiting", {"error": repr(exc), "events": events})
                close_events(); time.sleep(2); continue
            log_state("running", {"code_count": len(reverse_by_code), "event_count": len(events)})
            try:
                while running and opened:
                    monotonic = time.monotonic()
                    if monotonic - last_rebind_check > 2.0:
                        last_rebind_check = monotonic
                        current = find_events(); signature = event_signature(current)
                        if signature != opened_signature:
                            log_state("events-changed-reopen", {"old_signature": list(opened_signature), "new_signature": list(signature), "new_events": current})
                            close_events(); break
                    readable, _, _ = select.select([fd for fd, _ in opened], [], [], 0.5)
                    for fd in readable:
                        event_info = next((event for opened_fd, event in opened if opened_fd == fd), {"path": "?", "name": "?"})
                        try: raw = os.read(fd, INPUT_EVENT_SIZE * 64)
                        except BlockingIOError: continue
                        except Exception as exc:
                            log_state("read-error-reopen", {"error": repr(exc)}); close_events(); break
                        for offset in range(0, len(raw) - INPUT_EVENT_SIZE + 1, INPUT_EVENT_SIZE):
                            _sec, _usec, event_type, code, value = struct.unpack(INPUT_EVENT_FMT, raw[offset:offset + INPUT_EVENT_SIZE])
                            if event_type != EV_KEY or value != 1: continue
                            key = (event_info["path"], int(code))
                            item = reverse_by_event.get(key) or reverse_by_code.get(int(code))
                            if not item:
                                append_debug("unknown", {"event": event_info.get("path"), "device": event_info.get("name"), "code": int(code)})
                                continue
                            action = str(item["action"]); debounce = config.nav_debounce_sec if action in NAV_ACTIONS else config.button_debounce_sec
                            dt_action = monotonic - last_by_action.get(action, 0); dt_event = monotonic - last_by_event.get(key, 0)
                            if dt_action < debounce or dt_event < debounce:
                                append_debug("suppressed", {"action": action, "event": event_info.get("path"), "code": int(code), "dt_action": round(dt_action, 4), "dt_event": round(dt_event, 4)})
                                continue
                            last_by_action[action] = monotonic; last_by_event[key] = monotonic
                            if action in {"volume_up", "volume_down"}: run_volume(action)
                            write_action(action, str(item.get("label") or action), item)
            finally:
                close_events()
            if running: time.sleep(1)
    finally:
        try: httpd.shutdown()
        except Exception: pass
        log_state("stopped")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
