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
