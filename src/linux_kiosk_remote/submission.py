#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from .doctor import redact_obj

REPORT_SCHEMA = "xiaomi-mitv-remote-linux-kiosk.lab-report.v1"
SUBMISSION_SCHEMA = "xiaomi-mitv-remote-linux-kiosk.hardware-submission.v1"
REQUIRED_CHECKS = [
    "bluetoothctlAvailable",
    "profileKnown",
    "keymapValid",
    "paired",
    "connected",
    "inputEvent",
    "capturedRecommendedActions",
    "firstRunGrabSafe",
]
REQUIRED_ACTIONS = ["up", "down", "left", "right", "center", "back"]
PRIVATE_PATTERNS = {
    "mac-address": re.compile(r"\b(?!AA:BB:CC:DD:EE:FF\b)[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}\b"),
    "absolute-path": re.compile(r"/(?:home|mnt|media|Users|opt|srv|var|tmp)/[^\s\"']+"),
    "github-token": re.compile(("gh" + "p_") + r"[A-Za-z0-9_]{20,}|" + ("github" + "_pat_") + r"[A-Za-z0-9_]{20,}"),
}


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON {path}: {exc}")


def inspect_private_markers(value: Any) -> list[str]:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    findings = [name for name, pattern in PRIVATE_PATTERNS.items() if pattern.search(text)]
    return sorted(findings)


def validate_lab_report(report: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if report.get("schema") != REPORT_SCHEMA:
        errors.append(f"schema must be {REPORT_SCHEMA}")
    if not isinstance(report.get("checks"), dict):
        errors.append("checks must be an object")
    else:
        checks = report["checks"]
        for key in REQUIRED_CHECKS:
            item = checks.get(key)
            if not isinstance(item, dict) or "ok" not in item:
                errors.append(f"checks.{key}.ok missing")
    actions = report.get("capturedActions", [])
    if not isinstance(actions, list):
        errors.append("capturedActions must be a list")
        actions = []
    missing_actions = [action for action in REQUIRED_ACTIONS if action not in actions]
    if missing_actions:
        errors.append("missing required actions: " + ", ".join(missing_actions))
    if "safeToClaimHardwareVerified" not in report:
        errors.append("safeToClaimHardwareVerified missing")
    return not errors, errors


def build_submission(report: dict[str, Any]) -> dict[str, Any]:
    redacted = redact_obj(report)
    valid, errors = validate_lab_report(redacted)
    checks = redacted.get("checks", {}) if isinstance(redacted.get("checks"), dict) else {}
    failed_checks = [key for key in REQUIRED_CHECKS if not bool(checks.get(key, {}).get("ok"))]
    private_findings = inspect_private_markers(redacted)
    ready = bool(valid and not failed_checks and not private_findings and redacted.get("safeToClaimHardwareVerified") is True)
    return {
        "schema": SUBMISSION_SCHEMA,
        "readyForMaintainerReview": ready,
        "safeToClaimHardwareVerified": bool(redacted.get("safeToClaimHardwareVerified") is True and ready),
        "profileId": redacted.get("profileId"),
        "mode": redacted.get("mode"),
        "capturedActions": redacted.get("capturedActions", []),
        "failedChecks": failed_checks,
        "validationErrors": errors,
        "privateFindings": private_findings,
        "redactedReport": redacted,
    }


def markdown_summary(submission: dict[str, Any]) -> str:
    checks = submission.get("redactedReport", {}).get("checks", {})
    rows = []
    for key in REQUIRED_CHECKS:
        item = checks.get(key, {}) if isinstance(checks, dict) else {}
        icon = "✅" if item.get("ok") else "❌"
        rows.append(f"| `{key}` | {icon} | {item.get('message', '')} |")
    actions = ", ".join(submission.get("capturedActions", [])) or "none"
    failed = ", ".join(submission.get("failedChecks", [])) or "none"
    errors = ", ".join(submission.get("validationErrors", [])) or "none"
    private = ", ".join(submission.get("privateFindings", [])) or "none"
    return "\n".join([
        "# Hardware validation submission",
        "",
        f"- Ready for maintainer review: `{submission['readyForMaintainerReview']}`",
        f"- Safe to claim hardware verified: `{submission['safeToClaimHardwareVerified']}`",
        f"- Profile: `{submission.get('profileId')}`",
        f"- Mode: `{submission.get('mode')}`",
        f"- Captured actions: `{actions}`",
        f"- Failed checks: `{failed}`",
        f"- Validation errors: `{errors}`",
        f"- Private findings after redaction: `{private}`",
        "",
        "## Checks",
        "",
        "| Check | Status | Message |",
        "| --- | --- | --- |",
        *rows,
        "",
        "## Notes for issue/PR",
        "",
        "Attach the generated redacted submission JSON, not raw local logs. Do not include real MAC addresses, hostnames, private paths, or tokens.",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate/anonymize Xiaomi/MiTV remote hardware lab reports for maintainer review.")
    parser.add_argument("report", help="Path to hardware-validation-report.json produced by xiaomi-remote lab.")
    parser.add_argument("--output", help="Write redacted submission JSON to this path.")
    parser.add_argument("--markdown", help="Write GitHub issue/PR markdown summary to this path.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero unless the submission is ready for maintainer review.")
    args = parser.parse_args()

    report = read_json(Path(args.report).expanduser())
    if not isinstance(report, dict):
        raise SystemExit("report root must be an object")
    submission = build_submission(report)
    if args.output:
        out = Path(args.output).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(submission, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {out}")
    else:
        print(json.dumps(submission, ensure_ascii=False, indent=2))
    if args.markdown:
        md = Path(args.markdown).expanduser()
        md.parent.mkdir(parents=True, exist_ok=True)
        md.write_text(markdown_summary(submission), encoding="utf-8")
        print(f"wrote {md}")
    print(f"readyForMaintainerReview={submission['readyForMaintainerReview']}")
    if args.strict and not submission["readyForMaintainerReview"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
