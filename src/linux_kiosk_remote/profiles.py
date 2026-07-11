#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROFILE_SCHEMA = "xiaomi-mitv-remote-linux-kiosk.profile.v1"


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def profile_dir() -> Path:
    return project_root() / "profiles"


def validate_profile(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("profile must be an object")
    if data.get("schema") != PROFILE_SCHEMA:
        raise ValueError(f"profile.schema must be {PROFILE_SCHEMA}")
    for key in ["id", "name", "status", "match", "validation"]:
        if key not in data:
            raise ValueError(f"profile.{key} is required")
    if not isinstance(data["id"], str) or not data["id"]:
        raise ValueError("profile.id must be a non-empty string")
    match = data["match"]
    if not isinstance(match, dict) or not isinstance(match.get("nameRegex"), str) or not match["nameRegex"]:
        raise ValueError("profile.match.nameRegex must be a non-empty string")
    validation = data["validation"]
    if not isinstance(validation, dict):
        raise ValueError("profile.validation must be an object")
    return {"id": data["id"], "name": data["name"], "status": data["status"]}


def load_profiles(root: Path | None = None) -> list[dict[str, Any]]:
    root = root or profile_dir()
    out: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.profile.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        validate_profile(data)
        data["_path"] = str(path)
        out.append(data)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="List and validate remote compatibility profiles.")
    parser.add_argument("--json", action="store_true", help="Print full profiles as JSON.")
    args = parser.parse_args()
    profiles = load_profiles()
    if args.json:
        print(json.dumps(profiles, ensure_ascii=False, indent=2))
    else:
        print(f"profiles: {len(profiles)}")
        for p in profiles:
            print(f"  {p['id']:32} {p['status']:16} {p['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
