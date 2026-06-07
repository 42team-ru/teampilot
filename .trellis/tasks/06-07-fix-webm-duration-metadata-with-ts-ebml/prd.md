# fix: WebM Duration metadata for recorded audio chunks

## Goal

MediaRecorder записывает "стриминговый" WebM без Duration-элемента и Cues (seek-индекса).
Файлы в MinIO выглядят как "сломанные" в большинстве плееров. Нужно добавить корректный
Duration после каждой записи чанка, чтобы файлы были seekable и отображали длительность.

## Research References

* [`research/webm-duration-fixup.md`](research/webm-duration-fixup.md) — `fix-webm-duration` рекомендован: чистый браузерный JS, 23KB, 0 deps; ts-ebml не работает в browser без Buffer polyfill

## Decision (ADR-lite)

**Context**: ts-ebml падает в extension-контексте (Buffer is not defined, CJS-only). Нужна браузерная альтернатива.

**Decision**: `fix-webm-duration@1.0.6` — `const fixed = await fixWebmDuration(blob, durationMs, { logger: false })`

**Consequences**: требует отслеживания `durationMs` вокруг каждого `recordSingleChunk`. Безопасен для Chrome 138+ (библиотека no-op если Duration уже есть).

## Requirements

* Добавить `fix-webm-duration` в `extention/package.json`
* В `recordSingleChunk` замерять время до/после записи → передавать `durationMs` в fixup
* Применять fixup к каждому blob перед `resolve()` в `recorder.onstop`
* Применять и к финальному 250ms чанку в `stopCapture`

## Acceptance Criteria

* [ ] Скачанный из MinIO .webm-файл показывает корректную длительность в Chrome/VLC
* [ ] `blob.size` остаётся ненулевым после fixup
* [ ] TypeScript компилируется без ошибок
* [ ] Нет регрессии: аудио по-прежнему слышно

## Out of Scope

* ts-ebml / Cues (полная seekable таблица) — overkill для этих чанков
* Fixup на стороне бэкенда (Spring/ffmpeg)
* Изменение формата хранения в MinIO

## Technical Notes

- Файл: `extention/entrypoints/offscreen/main.ts`, функции `recordSingleChunk` и `recordFinalChunk` / `stopCapture`
- `durationMs` = timestamp после `recorder.stop()` - timestamp перед `recorder.start(timeslice)`
- Для финального 250ms чанка в `stopCapture` → отдельный `recordSingleChunk(FINAL_CHUNK_DURATION_MS)`
- Chrome 138+ пишет Duration нативно; `fix-webm-duration` корректно no-op в таком случае
