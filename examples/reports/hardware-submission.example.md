# Hardware validation submission

- Ready for maintainer review: `True`
- Safe to claim hardware verified: `True`
- Profile: `xiaomi-mitv-remote`
- Mode: `hardware-validation`
- Captured actions: `back, center, down, left, right, up`
- Failed checks: `none`
- Validation errors: `none`
- Private findings after redaction: `none`

## Checks

| Check | Status | Message |
| --- | --- | --- |
| `bluetoothctlAvailable` | ✅ | bluetoothctl found |
| `profileKnown` | ✅ | profile found |
| `keymapValid` | ✅ | configured keymap valid |
| `paired` | ✅ | remote paired/bonded |
| `connected` | ✅ | remote connected |
| `inputEvent` | ✅ | matching input event found |
| `capturedRecommendedActions` | ✅ | recommended actions captured |
| `firstRunGrabSafe` | ✅ | LKR_GRAB=0 for first validation |

## Notes for issue/PR

Attach the generated redacted submission JSON, not raw local logs. Do not include real MAC addresses, hostnames, private paths, or tokens.
