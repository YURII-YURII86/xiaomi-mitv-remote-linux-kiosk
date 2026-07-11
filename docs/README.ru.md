# Xiaomi MiTV Remote SDK для Linux-киосков

**Xiaomi MiTV Remote SDK for Linux Kiosks** — это набор Python-инструментов, который превращает физический Bluetooth-пульт Xiaomi/MiTV/Android TV в нормальный контроллер для Linux-киоска, локальной ТВ-панели, browser dashboard, digital signage или любого локального приложения.

Проект не управляет Android TV. Он не использует ADB, Android TV Remote Protocol, Home Assistant или облачные сервисы. Он работает ниже и проще: Linux видит Bluetooth-пульт как HID/input device, а SDK читает события кнопок из `/dev/input/event*`, превращает их в понятные действия и отдаёт приложению через JS/JSON/HTTP-мосты.

```text
Пульт Xiaomi / MiTV / Android TV
        ↓
Bluetooth HID на Linux
        ↓
/dev/input/event*
        ↓
EV_KEY reader + keymap + debounce + optional EVIOCGRAB
        ↓
JS file bridge / JSON state / localhost long-poll endpoint
        ↓
Firefox kiosk, Chromium kiosk, Electron, Python, Node, static HTML dashboard
```

## Зачем это нужно

У Linux-киосков часто есть проблема: экран стоит на телевизоре или мониторе, мышь/клавиатура неудобны, тачскрина нет, а хочется управлять интерфейсом обычным диванным пультом. Пульты Xiaomi/MiTV дешёвые, привычные и хорошо лежат в руке, но после подключения к Linux начинаются типичные грабли:

- `/dev/input/eventN` меняется после ребута;
- один физический пульт может появиться как несколько HID-интерфейсов;
- кнопки могут дублироваться;
- браузер или оконный менеджер перехватывает Back/Home/Volume;
- непонятно, какие Linux key codes реально отправляет конкретный пульт;
- приложение должно как-то получить “up”, “down”, “center”, “back”, а не сырые bytes из input event.

Этот SDK закрывает именно этот путь: **пульт → Linux input → стабильные actions → приложение/киоск**.

## Почему в названии Xiaomi/MiTV

Название специально оставлено конкретным: **Xiaomi/MiTV** понятнее людям, чем абстрактный “Bluetooth HID remote”. Проект писался и тестировался вокруг пульта Xiaomi/MiTV-style.

При этом внутри ядро сделано generic: любой Bluetooth HID-пульт может работать, если он отдаёт Linux `EV_KEY` события и под него есть JSON keymap. Xiaomi/MiTV — это первая и главная целевая семья устройств, а не искусственное ограничение архитектуры.

## Что уже есть

В составе проекта:

```text
src/linux_kiosk_remote/input_daemon.py      основной daemon чтения кнопок
src/linux_kiosk_remote/status_exporter.py   exporter статуса Bluetooth/input/daemon
src/linux_kiosk_remote/capture.py           capture/generate keymap helper
src/linux_kiosk_remote/setup_wizard.py      setup helper для локального проекта
src/linux_kiosk_remote/keymap.py            генерация keymap из action→code
src/linux_kiosk_remote/common.py            общие парсеры и конфиг
examples/mi-remote-keymap.example.json      пример keymap
examples/systemd/*.service                  systemd-примеры
examples/static-html-kiosk/index.html       мини-demo для браузера
scripts/smoke_test.sh                       локальный smoke-test
docs/api.md                                 контракты JS/JSON/HTTP
docs/troubleshooting.md                     типовые проблемы
docs/security.md                            security model
docs/hardware-validation.md                 чеклист реальной проверки железа
```

CLI после установки:

```text
xiaomi-mitv-remote-input
xiaomi-mitv-remote-status
xiaomi-mitv-remote-capture
xiaomi-mitv-remote-setup
```

## Главные возможности

- Автопоиск текущих `/dev/input/eventN` через `/proc/bus/input/devices`.
- Матчинг пульта по Bluetooth MAC/Uniq или regex имени устройства.
- Чтение Linux `EV_KEY` событий напрямую.
- JSON keymap: сырые key codes превращаются в `up`, `down`, `center`, `back`, `home`, `volume_up` и т.д.
- Debounce, чтобы один физический клик не срабатывал дважды.
- Optional `EVIOCGRAB`, чтобы Firefox/Chromium/оконный менеджер не забирали кнопки себе.
- JS bridge для браузера: `window.KIOSK_REMOTE_ACTION`.
- JSON state files для локальных приложений.
- Localhost long-poll HTTP endpoint: `GET /action?since=...`.
- Status exporter для dashboard card или диагностики.
- Systemd-примеры для appliance/kiosk режима.
- Capture helper для генерации keymap под конкретный пульт.
- Setup helper для первичной подготовки локального проекта.
- CI и smoke tests.

## Текущий статус проверки

Уже проверено в standalone-репозитории:

- `pip install -e .` в чистом virtualenv;
- CLI help для основных команд;
- unit tests парсеров `/proc/bus/input/devices`, `bluetoothctl info`, `bluetoothctl show`;
- генерация keymap из action→code;
- smoke-test из fresh clone;
- GitHub Actions CI;
- privacy scan: в репе нет приватных Slane-путей, Tailnet-имён, реального MAC пульта, diagnostics dump или GitHub token.

Пока честно **не заявлено как завершённое**:

- end-to-end hardware validation именно standalone-пакета на реальном пульте Xiaomi/MiTV после выноса из Slane;
- полноценный interactive pairing wizard;
- udev guide для non-root режима.

Это не значит, что проект “не работает”. Это значит, что публичная документация не врёт: код вырос из живого kiosk-проекта, но standalone-релиз ещё нужно отдельно прогнать на реальном пульте и записать результат в `docs/hardware-validation.md`.

## Установка

```bash
git clone https://github.com/YURII-YURII86/xiaomi-mitv-remote-linux-kiosk.git
cd xiaomi-mitv-remote-linux-kiosk
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

Проверить, что CLI доступны:

```bash
xiaomi-mitv-remote-input --help
xiaomi-mitv-remote-status --help
xiaomi-mitv-remote-capture --help
xiaomi-mitv-remote-setup --help
```

## Быстрый старт

Создать локальный keymap из примера:

```bash
mkdir -p data
cp examples/mi-remote-keymap.example.json data/mi-remote-keymap.json
```

Запустить input daemon в debug-режиме без grab, чтобы кнопки всё ещё доходили до desktop/browser:

```bash
sudo \
  LKR_ROOT="$PWD" \
  LKR_GRAB=0 \
  LKR_REMOTE_MAC="AA:BB:CC:DD:EE:FF" \
  LKR_DEVICE_NAME_REGEX="xiaomi|mi rc|android.*remote|remote" \
  xiaomi-mitv-remote-input
```

Для kiosk/appliance режима, где браузер не должен перехватывать кнопки, включить grab:

```bash
sudo \
  LKR_ROOT="$PWD" \
  LKR_GRAB=1 \
  LKR_REMOTE_MAC="AA:BB:CC:DD:EE:FF" \
  xiaomi-mitv-remote-input
```

## Профили совместимости

Показать встроенные профили:

```bash
xiaomi-mitv-remote-profiles
```

Профили лежат в `profiles/*.profile.json`. Проект остаётся Xiaomi/MiTV-first, но другие Bluetooth HID-пульты можно валидировать через capture mode и doctor report. Подробнее: `docs/compatibility.md`.

## Setup helper

Команда:

```bash
xiaomi-mitv-remote-setup --init-keymap --print-systemd
```

Она:

- показывает root проекта;
- показывает путь keymap;
- проверяет `bluetoothctl show`;
- проверяет Python;
- сканирует matching input events;
- может создать `data/mi-remote-keymap.json` из примера;
- печатает suggested `.env`;
- печатает следующие команды для запуска daemon.

Безопасная проверка без записи файлов:

```bash
xiaomi-mitv-remote-setup --init-keymap --dry-run
```

## Capture keymap

Если key codes конкретного пульта неизвестны, используется capture helper:

```bash
sudo LKR_ROOT="$PWD" LKR_GRAB=0 xiaomi-mitv-remote-capture
```

Он попросит нажать кнопки:

```text
Press Up...
Press Down...
Press OK...
Press Back...
...
```

И сохранит JSON keymap.

Если коды уже известны, можно сгенерировать keymap без интерактива:

```bash
xiaomi-mitv-remote-capture \
  --from-codes-json '{"up":103,"down":108,"center":353}' \
  --output data/mi-remote-keymap.json
```

## Интеграция с браузером

Daemon по умолчанию пишет:

```text
data/remote-action.js
```

Пример содержимого:

```js
window.KIOSK_REMOTE_ACTION = {
  seq: 12,
  action: "up",
  label: "Up",
  source: {
    code: 103,
    code_text: "KEY_UP"
  },
  ts: "2026-07-11T12:00:00"
};
```

Статический HTML kiosk может подключать или периодически перечитывать этот файл. Другой вариант — использовать local HTTP endpoint:

```js
let seq = 0;

async function pollRemote() {
  const res = await fetch(`http://127.0.0.1:8793/action?since=${seq}&timeout=15`);
  const data = await res.json();

  if (data.ok && data.seq > seq) {
    seq = data.seq;
    handleRemoteAction(data.payload.action);
  }

  pollRemote();
}

pollRemote();
```

Мини-demo лежит тут:

```text
examples/static-html-kiosk/index.html
```

## Status exporter

Разовый запуск:

```bash
LKR_ROOT="$PWD" LKR_REMOTE_MAC="AA:BB:CC:DD:EE:FF" xiaomi-mitv-remote-status
```

Loop-режим:

```bash
LKR_ROOT="$PWD" LKR_REMOTE_MAC="AA:BB:CC:DD:EE:FF" xiaomi-mitv-remote-status --loop --interval 5
```

Он пишет:

```text
data/remote-status.json
data/remote-status.js
```

Статус показывает:

- paired/bonded/trusted/connected;
- есть ли HID UUID;
- есть ли input event;
- состояние daemon;
- controller flags: powered/discoverable/pairable/discovering;
- high-level state: `ok`, `press_to_wake`, `pair_required`, `daemon_waiting`, `scan_active` и т.д.

## Переменные окружения

| Variable | Default | Meaning |
| --- | --- | --- |
| `LKR_ROOT` | current working directory | Корень проекта/дашборда. |
| `LKR_KEYMAP` | `$LKR_ROOT/data/mi-remote-keymap.json` | Путь к keymap. |
| `LKR_ACTION_JS` | `$LKR_ROOT/data/remote-action.js` | JS bridge для браузера. |
| `LKR_STATE_JSON` | `$LKR_ROOT/data/remote-daemon-state.json` | State-файл daemon. |
| `LKR_DEBUG_LOG` | `$LKR_ROOT/data/remote-action-debug.jsonl` | Debug log. |
| `LKR_STATUS_JSON` | `$LKR_ROOT/data/remote-status.json` | Status JSON. |
| `LKR_STATUS_JS` | `$LKR_ROOT/data/remote-status.js` | Status JS. |
| `LKR_REMOTE_MAC` | empty | MAC/Uniq пульта. Рекомендуется для стабильных appliance-инсталляций. |
| `LKR_DEVICE_NAME_REGEX` | `xiaomi\|mi rc\|android.*remote\|remote` | Fallback match по имени input device. |
| `LKR_EVENT_HOST` | `127.0.0.1` | Host для long-poll HTTP endpoint. |
| `LKR_EVENT_PORT` | `8793` | Port для long-poll HTTP endpoint. |
| `LKR_JS_GLOBAL` | `KIOSK_REMOTE_ACTION` | Имя JS global для action bridge. |
| `LKR_STATUS_JS_GLOBAL` | `KIOSK_REMOTE_STATUS` | Имя JS global для status bridge. |
| `LKR_GRAB` | `1` | Использовать `EVIOCGRAB`. `0` = observe/debug mode. |
| `LKR_VOLUME_PACTL` | `0` | Если `1`, volume actions вызывают `pactl`. |
| `LKR_NAV_DEBOUNCE_SEC` | `0.45` | Debounce для навигационных кнопок. |
| `LKR_BUTTON_DEBOUNCE_SEC` | `0.30` | Debounce для остальных кнопок. |

## Systemd

Примеры:

```text
examples/systemd/linux-kiosk-remote-input.service
examples/systemd/linux-kiosk-remote-status.service
```

Обычно input daemon в kiosk/appliance режиме проще запускать от root, потому что нужны права на `/dev/input/event*` и `EVIOCGRAB`. Для desktop-friendly сценария лучше позже добавить udev rule под конкретный remote/device id.

## Документация

- `docs/api.md` — контракты JS/JSON/HTTP.
- `docs/troubleshooting.md` — типовые проблемы Bluetooth/HID/kiosk.
- `docs/compatibility.md` — профили совместимости и правила валидации.
- `docs/udev-non-root.md` — осторожный non-root доступ к input devices.
- `docs/security.md` — security model, root/input access, localhost endpoint.
- `docs/hardware-validation.md` — чеклист реальной проверки пульта.

## Тесты

```bash
./scripts/smoke_test.sh
```

Smoke test проверяет:

- Python syntax;
- unit tests;
- example keymap JSON;
- capture helper;
- setup helper.

CI на GitHub прогоняет smoke test на Python 3.10, 3.11 и 3.12.

## Безопасность

- Проект не использует облако.
- HTTP endpoint по умолчанию слушает только `127.0.0.1`.
- Не выставляйте endpoint в сеть без своей модели авторизации.
- Raw diagnostics могут содержать MAC-адреса, имена устройств и локальные пути.
- `EVIOCGRAB` полезен для kiosk, но требует аккуратной отладки.
- Bluetooth scan не стоит держать включённым постоянно на слабых Wi-Fi/BT combo-чипах.

## Когда этот проект подходит

Подходит, если у вас:

- Linux kiosk;
- Firefox/Chromium kiosk mode;
- digital signage;
- local dashboard;
- Electron app на телевизоре;
- Python/Node локальное приложение;
- физический Bluetooth-пульт, который Linux видит как HID input.

Не подходит, если вам нужно:

- управлять Android TV по сети;
- отправлять команды в телевизор через ADB;
- интеграция именно в Home Assistant;
- cloud remote control;
- мобильное приложение-пульт.

## Roadmap

- Реальная hardware validation таблица после прогона standalone-пакета на Xiaomi/MiTV remote.
- Более полноценный interactive pairing wizard.
- udev guide для non-root режима.
- Electron/Node/Python integration examples.
- WebSocket/MQTT bridge как опциональные adapters.
- Профили для других Bluetooth HID-пультов.
- GIF/video demo.

## Лицензия

MIT.
