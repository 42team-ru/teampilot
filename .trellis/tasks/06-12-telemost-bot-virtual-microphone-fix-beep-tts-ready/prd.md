# PRD: telemost-bot — Virtual Microphone (fix beep + TTS-ready)

## Проблема

Бот заходит в Telemost-звонок с флагом Chrome `--use-fake-device-for-media-stream`
(`session_manager.py`). Фейковое аудио-устройство Chrome генерирует периодический «пик»
(~1 кГц синусоида раз в секунду), который транслируется всем участникам звонка как
микрофон бота. Неприятно.

## Цель

Заменить фейковый микрофон на **виртуальный PulseAudio-микрофон**, который:
1. По умолчанию отдаёт **тишину** → «пик» исчезает.
2. Telemost видит как живое устройство (вход не ломается).
3. Готов под TTS: чтобы бот заговорил, достаточно проиграть WAV в этот sink
   (зависимость из задачи `06-11-meeting-bot-voice-qa-agent`, которая обещала
   «virtual source из Task 1» — его фактически не было).

Бот остаётся пассивным слушателем; захват чужого звука (existing capture sink +
`.monitor`) не трогаем.

## Архитектура

```
              ┌─ paplay/ffmpeg tts.wav ─┐  ← позже, когда бот отвечает голосом
bot_mic_<id>  ◄──────────────────────────┤
 (null-sink)                              └─ по умолчанию никто не пишет → тишина
   │
   └─ bot_mic_<id>.monitor ──► PULSE_SOURCE для Chrome ──► «микрофон» в Telemost
```

Существующий поток захвата (что говорят другие) не меняется:
`bot_sink_<id>` + `bot_sink_<id>.monitor` → ffmpeg → чанки.

## Изменения в коде (`telemost-bot/session_manager.py`)

1. **`TelemostSession`**: добавить поля `mic_sink_name`, `mic_module_id`.
2. **`start_session`**: создать второй null-sink `bot_mic_<id>` через тот же
   `_create_virtual_sink` (description = `TeamPilotBotMic`). Если не создался — RuntimeError + откат уже созданного capture-sink.
3. **`_browser_task`**:
   - Убрать `--use-fake-device-for-media-stream` из `args`.
   - Оставить `--use-fake-ui-for-media-stream` (авто-grant разрешений).
   - В `env` добавить `PULSE_SOURCE=f"{session.mic_sink_name}.monitor"`.
4. **`stop_session`**: выгрузить оба модуля (capture sink + mic sink).
5. Хелпер для будущего TTS не реализуем в этой задаче, но оставляем sink с известным
   именем (`session.mic_sink_name`), чтобы voice-агент мог в него писать.

## Scope

- [x] Виртуальный микрофон (null-sink + monitor как PULSE_SOURCE)
- [x] Убрать фейковое аудио-устройство → нет «пика»
- [x] Корректная очистка обоих sink в stop_session
- [ ] Проверить, что Telemost пускает в звонок без камеры (камера НЕ нужна сейчас)

## Out of scope

- TTS-воспроизведение / wake word / voice Q&A (задача `06-11-meeting-bot-voice-qa-agent`)
- Вывод видео/картинки в звонок (будущее — архитектуру оставляем расширяемой,
  но фейк-камеру/виртуальную камеру сейчас не делаем)

## Риски / проверки

- Если Telemost требует камеру для входа — фолбэк: вернуть фейк-видео отдельным
  способом (но не фейк-аудио). Пользователь подтвердил: камера сейчас не нужна.
- Headless без Xvfb: аудио-роутинг PulseAudio может не работать — уже есть
  предупреждение в коде; виртуальный mic это не меняет.

## Стек

Python 3.12, PulseAudio (pactl module-null-sink), Playwright + Chrome.
