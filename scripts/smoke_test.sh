#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m py_compile src/linux_kiosk_remote/*.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 - <<'PY'
import json
from pathlib import Path
p = Path('examples/mi-remote-keymap.example.json')
data = json.loads(p.read_text())
assert 'keys' in data and 'up' in data['keys']
assert data['mac'] == 'AA:BB:CC:DD:EE:FF'
print('example keymap ok')
PY
rm -rf /tmp/xiaomi-mitv-remote-smoke
mkdir -p /tmp/xiaomi-mitv-remote-smoke
LKR_ROOT=/tmp/xiaomi-mitv-remote-smoke xiaomi-mitv-remote-capture --from-codes-json '{"up":103,"down":108,"center":353}' --output /tmp/xiaomi-mitv-remote-smoke/keymap.json >/tmp/xiaomi-mitv-remote-smoke/capture.log
python3 - <<'PY'
import json
data=json.load(open('/tmp/xiaomi-mitv-remote-smoke/keymap.json'))
assert data['keys']['up']['code'] == 103
assert data['keys']['center']['code_text'] == 'KEY_SELECT'
print('capture helper ok')
PY
LKR_ROOT=/tmp/xiaomi-mitv-remote-smoke xiaomi-mitv-remote-setup --root /tmp/xiaomi-mitv-remote-smoke --mac AA:BB:CC:DD:EE:FF --init-keymap --dry-run >/tmp/xiaomi-mitv-remote-smoke/setup.log
grep -q 'Suggested .env' /tmp/xiaomi-mitv-remote-smoke/setup.log
echo 'setup helper ok'
