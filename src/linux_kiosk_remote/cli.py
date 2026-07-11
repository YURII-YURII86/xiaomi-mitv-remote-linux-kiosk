#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from contextlib import contextmanager
from typing import Callable

from . import __version__

LANGS = {"en", "ru"}

TEXT = {
    "en": {
        "prog_desc": "Native CLI for Xiaomi/MiTV Bluetooth remotes on Linux kiosks.",
        "epilog": "Typical flow: setup → profiles → capture → lab → daemon → status. Use --lang ru for Russian.",
        "cmd_help": "Show this product-oriented help.",
        "cmd_setup": "Prepare/check a local kiosk project folder.",
        "cmd_profiles": "List compatibility profiles.",
        "cmd_capture": "Capture/generate a keymap.",
        "cmd_lab": "Run validation lab and hardware report flow.",
        "cmd_doctor": "Create a redacted diagnostics report.",
        "cmd_daemon": "Run the input daemon.",
        "cmd_status": "Export Bluetooth/input/daemon status.",
        "cmd_flow": "Print the recommended setup flow.",
        "flow_title": "Recommended Xiaomi/MiTV remote setup flow",
        "flow_steps": [
            "1. Pair the remote in your desktop/Bluetooth UI or bluetoothctl.",
            "2. Run: xiaomi-remote setup --init-keymap --dry-run",
            "3. Run: xiaomi-remote profiles",
            "4. Capture real buttons: xiaomi-remote capture --output data/mi-remote-keymap.json",
            "5. Validate: LKR_GRAB=0 xiaomi-remote lab --output hardware-validation-report.json",
            "6. Run daemon in observe mode first: LKR_GRAB=0 xiaomi-remote daemon",
            "7. Switch to LKR_GRAB=1 only after browser/app integration is confirmed.",
        ],
        "safety": "Safety: no production kiosk mutation is done by setup/doctor/profiles/flow. Capture/lab write files only when output flags are explicitly passed.",
    },
    "ru": {
        "prog_desc": "Нативный CLI для Bluetooth-пультов Xiaomi/MiTV на Linux-киосках.",
        "epilog": "Типовой путь: setup → profiles → capture → lab → daemon → status. Используй --lang en для английского.",
        "cmd_help": "Показать продуктовую справку.",
        "cmd_setup": "Подготовить/проверить локальную папку kiosk-проекта.",
        "cmd_profiles": "Показать профили совместимости.",
        "cmd_capture": "Поймать кнопки и сгенерировать keymap.",
        "cmd_lab": "Запустить validation lab и создать hardware report.",
        "cmd_doctor": "Создать безопасный redacted diagnostics report.",
        "cmd_daemon": "Запустить input daemon.",
        "cmd_status": "Экспортировать статус Bluetooth/input/daemon.",
        "cmd_flow": "Показать рекомендуемый путь настройки.",
        "flow_title": "Рекомендуемый путь настройки Xiaomi/MiTV пульта",
        "flow_steps": [
            "1. Спарь пульт через Bluetooth UI или bluetoothctl.",
            "2. Запусти: xiaomi-remote setup --init-keymap --dry-run",
            "3. Запусти: xiaomi-remote profiles",
            "4. Поймай реальные кнопки: xiaomi-remote capture --output data/mi-remote-keymap.json",
            "5. Проверь: LKR_GRAB=0 xiaomi-remote lab --output hardware-validation-report.json",
            "6. Сначала daemon в observe mode: LKR_GRAB=0 xiaomi-remote daemon",
            "7. Включай LKR_GRAB=1 только после проверки browser/app integration.",
        ],
        "safety": "Безопасность: setup/doctor/profiles/flow не мутируют production kiosk. Capture/lab пишут файлы только когда явно переданы output-флаги.",
    },
}

COMMANDS: dict[str, tuple[str, str]] = {
    "setup": ("linux_kiosk_remote.setup_wizard", "main"),
    "profiles": ("linux_kiosk_remote.profiles", "main"),
    "capture": ("linux_kiosk_remote.capture", "main"),
    "lab": ("linux_kiosk_remote.lab", "main"),
    "doctor": ("linux_kiosk_remote.doctor", "main"),
    "daemon": ("linux_kiosk_remote.input_daemon", "main"),
    "status": ("linux_kiosk_remote.status_exporter", "main"),
}

ALIASES = {
    "input": "daemon",
    "run": "daemon",
    "validate": "lab",
    "diagnose": "doctor",
    "profile": "profiles",
}


def choose_lang(argv: list[str]) -> str:
    env = os.environ.get("XMR_LANG", "").strip().lower()
    lang = env if env in LANGS else "en"
    for i, item in enumerate(argv):
        if item == "--lang" and i + 1 < len(argv) and argv[i + 1] in LANGS:
            return argv[i + 1]
        if item.startswith("--lang=") and item.split("=", 1)[1] in LANGS:
            return item.split("=", 1)[1]
    return lang


def strip_global_args(argv: list[str]) -> list[str]:
    out: list[str] = []
    skip = False
    for item in argv:
        if skip:
            skip = False
            continue
        if item == "--lang":
            skip = True
            continue
        if item.startswith("--lang="):
            continue
        out.append(item)
    return out


def build_parser(lang: str) -> argparse.ArgumentParser:
    t = TEXT[lang]
    parser = argparse.ArgumentParser(
        prog="xiaomi-remote",
        description=t["prog_desc"],
        epilog=t["epilog"],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--lang", choices=sorted(LANGS), default=lang, help="UI language / язык интерфейса")
    parser.add_argument("--version", action="version", version=f"xiaomi-remote {__version__}")
    sub = parser.add_subparsers(dest="command")
    for name in ["help", "flow", "setup", "profiles", "capture", "lab", "doctor", "daemon", "status"]:
        if name in {"help", "flow"}:
            sub.add_parser(name, help=t[f"cmd_{name}"])
        else:
            p = sub.add_parser(name, help=t[f"cmd_{name}"], add_help=False)
            p.add_argument("args", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    return parser


def print_flow(lang: str) -> int:
    t = TEXT[lang]
    print(t["flow_title"])
    print("=" * len(t["flow_title"]))
    for step in t["flow_steps"]:
        print(step)
    print()
    print(t["safety"])
    return 0


@contextmanager
def patched_argv(prog: str, args: list[str]):
    old = sys.argv[:]
    sys.argv = [prog] + args
    try:
        yield
    finally:
        sys.argv = old


def load_main(module_name: str, func_name: str) -> Callable[[], int]:
    module = __import__(module_name, fromlist=[func_name])
    return getattr(module, func_name)


def delegate(command: str, args: list[str]) -> int:
    command = ALIASES.get(command, command)
    if command not in COMMANDS:
        raise SystemExit(f"unknown command: {command}")
    module_name, func_name = COMMANDS[command]
    func = load_main(module_name, func_name)
    with patched_argv(f"xiaomi-remote {command}", args):
        result = func()
    return int(result or 0)


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    lang = choose_lang(raw)
    cleaned = strip_global_args(raw)
    if cleaned and cleaned[0] == "--version":
        print(f"xiaomi-remote {__version__}")
        return 0
    if not cleaned or cleaned[0] in {"help", "--help", "-h"}:
        build_parser(lang).print_help()
        print()
        print_flow(lang)
        return 0
    command = ALIASES.get(cleaned[0], cleaned[0])
    if command == "flow":
        return print_flow(lang)
    if command not in COMMANDS:
        build_parser(lang).print_help()
        print(f"\nunknown command: {cleaned[0]}", file=sys.stderr)
        return 2
    return delegate(command, cleaned[1:])


if __name__ == "__main__":
    raise SystemExit(main())
