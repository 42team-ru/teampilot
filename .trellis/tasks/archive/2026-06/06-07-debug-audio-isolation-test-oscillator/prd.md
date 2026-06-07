# debug: audio isolation test — audible oscillator

## Goal

Добавить временный диагностический тон (440 Hz) в `startCapture`, подключённый напрямую к `destination`. Цель — изолировать проблему: если после добавления `blob.size > 10000`, то `AudioContext` + `MediaRecorder` исправны, и проблема только в стримах (`tabCapture` / `getUserMedia` возвращают пустые треки).

## What I already know

- Файл: `extention/entrypoints/offscreen/main.ts`, функция `startCapture` (строки 62–155)
- Уже есть паттерн silent oscillator (строки 88–98): `gain.value = 0` → destination
- Нужно добавить **слышимый** вариант: `gain.value = 0.3`, `frequency = 440`
- Точный код предоставлен пользователем

## Requirements

* Добавить `testOsc` (440 Hz, gain 0.3) в `startCapture` после создания `AudioContext`
* Подключить к `destination` (чтобы попасть в `mixedStream` и `MediaRecorder`)
* Оставить диагностический `console.log` для отслеживания `blob.size`

## Acceptance Criteria

* [ ] При запуске записи в аудио слышен тон 440 Hz
* [ ] Первый чанк (30 сек) имеет `blob.size > 10000` байт
* [ ] Код компилируется без TS-ошибок

## Decision

Оформить как отдельную функцию `injectDebugTone(ctx, destination)` — легко grep'ается (`injectDebugTone`) и удаляется одной строкой вызова + одной функцией.

## Out of Scope

* Постоянная фича — это сугубо временный диагностический код
* Изменения в UI, background.ts, RecordingScreen

## Technical Notes

- `extention/entrypoints/offscreen/main.ts:67` — место вставки (после `audioContext = new AudioContext(...)`)
- Существующий silent oscillator на строках 88–98 — хороший шаблон
