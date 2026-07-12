#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf 'repo quality gate: xiaomi-mitv-remote-linux-kiosk\n'

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

printf '\n[1/10] git/publication cleanliness\n'
tracked_bad="$(git ls-files | grep -E '(^|/)(__pycache__|\.ai_context|AGENTS\.md|CLAUDE\.md|\.egg-info|data/remote-action\.js|data/remote-status\.(js|json)|data/remote-daemon-state\.json|debug.*\.jsonl)' || true)"
if [[ -n "$tracked_bad" ]]; then
  printf '%s\n' "$tracked_bad"
  fail 'tracked generated/private files found'
fi
printf 'ok\n'

printf '\n[2/10] version consistency\n'
python3 - <<'PY'
import re
from pathlib import Path
pyproject = Path('pyproject.toml').read_text()
version_match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M)
assert version_match, 'project version missing'
project_version = version_match.group(1)
init=Path('src/linux_kiosk_remote/__init__.py').read_text()
match=re.search(r'__version__\s*=\s*"([^"]+)"', init)
assert match, '__version__ missing'
assert match.group(1) == project_version, (match.group(1), project_version)
changelog = Path('CHANGELOG.md').read_text()
assert f'## {project_version}' in changelog or f'## [{project_version}]' in changelog, 'CHANGELOG missing current version section'
print('ok', project_version)
PY

printf '\n[3/10] entry points import\n'
PYTHONPATH=src python3 - <<'PY'
import importlib
import re
from pathlib import Path
text = Path('pyproject.toml').read_text()
block = re.search(r'\[project\.scripts\](.*?)(?:\n\[|\Z)', text, re.S)
assert block, 'project.scripts missing'
scripts = {}
for line in block.group(1).splitlines():
    line = line.strip()
    if not line or line.startswith('#'):
        continue
    key, value = line.split('=', 1)
    scripts[key.strip()] = value.strip().strip('"')
for name, target in scripts.items():
    mod, func = target.split(':')
    obj = getattr(importlib.import_module(mod), func)
    assert callable(obj), (name, target)
print('ok', len(scripts))
PY

printf '\n[4/10] smoke test\n'
./scripts/smoke_test.sh

printf '\n[5/10] native CLI language smoke\n'
PYTHONPATH=src python3 -m linux_kiosk_remote.cli --version | grep -q '0.2.'
PYTHONPATH=src python3 -m linux_kiosk_remote.cli --lang ru help >/tmp/xiaomi-quality-ru-help.txt
grep -q 'Нативный CLI' /tmp/xiaomi-quality-ru-help.txt
XMR_LANG=ru PYTHONPATH=src python3 -m linux_kiosk_remote.cli flow >/tmp/xiaomi-quality-ru-flow.txt
grep -q 'Рекомендуемый путь' /tmp/xiaomi-quality-ru-flow.txt
printf 'ok\n'

printf '\n[6/10] README/docs required sections\n'
python3 - <<'PY'
from pathlib import Path
readme=Path('README.md').read_text()
required = [
    'Native bilingual CLI',
    'Validation lab',
    'Doctor / safe diagnostics',
    'Compatibility profiles',
    'Quick start',
    'Current verification status',
    'Part of Linux Kiosk Stack',
    'Hardware validation submission',
]
missing=[item for item in required if item not in readme]
assert not missing, missing
ru=Path('docs/README.ru.md').read_text()
for marker in ['Нативный двуязычный CLI','Validation lab','Профили совместимости','Hardware validation submission']:
    assert marker in ru, marker
print('ok')
PY

printf '\n[7/10] hardware submission flow\n'
PYTHONPATH=src python3 -m linux_kiosk_remote.submission examples/reports/hardware-validation-report.example.json --output /tmp/xiaomi-quality-submission.json --markdown /tmp/xiaomi-quality-submission.md --strict
python3 - <<'PY'
import json
sub=json.load(open('/tmp/xiaomi-quality-submission.json'))
assert sub['schema'] == 'xiaomi-mitv-remote-linux-kiosk.hardware-submission.v1'
assert sub['readyForMaintainerReview'] is True
assert sub['safeToClaimHardwareVerified'] is True
assert sub['privateFindings'] == []
assert 'Hardware validation submission' in open('/tmp/xiaomi-quality-submission.md').read()
print('ok')
PY

printf '\n[8/10] local markdown links\n'
python3 - <<'PY'
from pathlib import Path
import re
root=Path('.').resolve()
errors=[]
for p in root.rglob('*'):
    if not p.is_file() or '.git' in p.parts or '.ai_context' in p.parts or '__pycache__' in p.parts:
        continue
    if p.suffix.lower() != '.md' and not p.name.startswith('README') and p.name != 'CHANGELOG.md':
        continue
    text=p.read_text(errors='replace')
    for m in re.finditer(r'(?<!!)\[[^\]]+\]\(([^)]+)\)', text):
        target=m.group(1).strip().split()[0].strip('<>')
        if not target or target.startswith(('#','http://','https://','mailto:','tel:')):
            continue
        rel=target.split('#',1)[0]
        if rel and not (p.parent / rel).resolve().exists():
            errors.append(f'{p}:{text.count(chr(10),0,m.start())+1}:{target}')
if errors:
    print('\n'.join(errors))
    raise SystemExit(1)
print('ok')
PY

printf '\n[9/10] public privacy scan\n'
python3 - <<'PY'
from pathlib import Path
needles = [
    '14' + ':ab',
    '14' + ':AB',
    'tail' + 'ad',
    '/mnt/' + 'slane',
    'Мои ' + 'приложения',
    'Сл' + 'ейн',
    'SL' + 'ANE',
    'slane' + '-stick',
    'yu' + 'rii',
    'yu' + 'rii86',
    'gh' + 'p_',
]
hits=[]
for p in Path('.').rglob('*'):
    if not p.is_file() or '.git' in p.parts or '__pycache__' in p.parts or '.ai_context' in p.parts or p.name in {'AGENTS.md', 'CLAUDE.md'}:
        continue
    text=p.read_text(errors='ignore')
    for n in needles:
        if n in text:
            hits.append((str(p), n))
if hits:
    print('bad hits', hits[:50])
    raise SystemExit(1)
print('ok')
PY

printf '\n[10/10] profile/report examples parse\n'
python3 - <<'PY'
import json
from pathlib import Path
for p in Path('profiles').glob('*.json'):
    data=json.loads(p.read_text())
    assert data['schema'] == 'xiaomi-mitv-remote-linux-kiosk.profile.v1'
report=json.loads(Path('examples/reports/hardware-validation-report.example.json').read_text())
assert report['schema'] == 'xiaomi-mitv-remote-linux-kiosk.lab-report.v1'
submission=json.loads(Path('examples/reports/hardware-submission.example.json').read_text())
assert submission['schema'] == 'xiaomi-mitv-remote-linux-kiosk.hardware-submission.v1'
assert submission['readyForMaintainerReview'] is True
print('ok')
PY

printf '\nrepo quality gate ok\n'
