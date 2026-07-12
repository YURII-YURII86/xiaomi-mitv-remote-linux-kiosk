# Hardware validation submission flow

Real Xiaomi/MiTV remote support should be claimed only after a lab report is reviewed.

This repo includes a submission helper that validates and anonymizes `xiaomi-remote lab` output before you attach it to a GitHub issue or PR.

## 1. Run lab in observe mode

```bash
LKR_GRAB=0 xiaomi-remote lab --output hardware-validation-report.json
```

For first validation, keep `LKR_GRAB=0`. Do not grab the input device until browser/app integration is confirmed.

## 2. Prepare a redacted submission package

```bash
xiaomi-remote submit hardware-validation-report.json \
  --output hardware-submission.json \
  --markdown hardware-submission.md
```

The submission helper checks:

- report schema;
- required checks;
- required actions: `up`, `down`, `left`, `right`, `center`, `back`;
- `safeToClaimHardwareVerified`;
- private marker findings after redaction.

## 3. Attach only redacted files

Attach these files:

```text
hardware-submission.json
hardware-submission.md
```

Do not attach raw local logs. Do not include real MAC addresses, hostnames, private paths, or tokens.

## Example files

```text
examples/reports/hardware-validation-report.example.json
examples/reports/hardware-submission.example.json
examples/reports/hardware-submission.example.md
```

## Maintainer interpretation

- `readyForMaintainerReview=true`: the report is structurally complete and redacted.
- `safeToClaimHardwareVerified=true`: the submission is complete enough to claim this profile/hardware combo as validated.
- `readyForMaintainerReview=false`: the report can still be useful for troubleshooting, but should not be used as a verified compatibility claim.
