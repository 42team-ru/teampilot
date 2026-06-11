# voice-rvc — локальный мем-TTS (edge-tts → RVC)

Self-hosted, OpenAI-совместимый TTS с **мем-голосами**. Drop-in замена облачного
TTS для нашего `llm-worker`: переключается одной env-переменной, без правок кода
воркера.

## Как работает

Пайплайн в два шага:

```
text → edge-tts (нейтральный русский голос) → RVC voice conversion (тембр персонажа) → mp3/wav
```

RVC (Retrieval-based Voice Conversion) перекрашивает **тембр** уже готовой речи
(audio→audio), поэтому сначала генерируется базовый голос через `edge-tts`
(`ru-RU-DmitryNeural` по умолчанию), а потом он «перекрашивается» голосом
персонажа моделью `.pth`.

## API (OpenAI-совместимый)

- `POST /v1/audio/speech` — тело `{"model","input","voice","response_format"}`:
  - `model` — имя RVC-модели = имя папки в `rvc_models/` (например `prigozhin`).
  - `input` — текст для озвучки.
  - `voice` — опционально, базовый edge-tts голос; пусто → `BASE_TTS_VOICE`.
  - `response_format` — `mp3` (дефолт) или `wav`.
  - Заголовок `Authorization` игнорируется (аутентификация не нужна).
- `GET /v1/models` — список доступных RVC-моделей (папки с `.pth`).
- `GET /health` → `{"status":"ok"}`.

**Graceful degradation:** если RVC-модель не найдена или конвертация упала —
сервис вернёт базовый edge-tts голос (с предупреждением в логах), а не 500.

## Как добавить голос (модель)

1. Скачай RVC-модель персонажа (zip с `.pth` и, желательно, `.index`):
   - [weights.gg](https://www.weights.gg/) или [voice-models.com](https://voice-models.com/)
2. Распакуй в отдельную папку внутри `rvc_models/`, имя папки = имя модели в API:
   ```
   voice-rvc/rvc_models/
     prigozhin/
       prigozhin.pth      # обязательно
       added_xxx.index    # опционально, заметно улучшает сходство тембра
   ```
3. Имя папки (`prigozhin`) и передаётся как `model` в запросе / `TTS_MODEL` воркера.

Веса (`*.pth`, `*.index`) в git **не коммитятся** (см. `.gitignore`).

## Как переключить llm-worker на этот сервис

В `llm-worker/.env`:

```bash
TTS_API_BASE=http://voice-rvc:5050/v1   # в докере; локально http://localhost:5050/v1
TTS_MODEL=prigozhin                     # имя папки в rvc_models
# TTS_FORMAT=mp3                        # уже дефолт; формат воркера не меняем
# TTS_API_KEY не нужен — auth сервис игнорирует
```

Воркер уже шлёт `POST {TTS_API_BASE}/audio/speech` через OpenAI SDK — больше
ничего менять не надо.

## CPU vs GPU

- По умолчанию `RVC_DEVICE=cpu:0` — работает везде, инференс несколько секунд на
  короткую фразу.
- Для GPU: `RVC_DEVICE=cuda:0` + образ с CUDA-torch + проброс GPU в контейнер
  (nvidia-container-toolkit, см. закомментированную `deploy.resources` в
  `docker-compose.services.yml`).

## Запуск

В докере (из корня репозитория):

```bash
docker compose -f infrastructure/docker/docker-compose.services.yml up -d voice-rvc
```

Локально:

```bash
cd voice-rvc
pip install -r requirements.txt        # тянет torch — тяжело и долго
RVC_MODELS_DIR=$(pwd)/rvc_models uvicorn app:app --host 0.0.0.0 --port 5050
```

## Пример curl

```bash
curl -s http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model":"prigozhin","input":"Привет, это голосовой ассистент Пилот.","response_format":"mp3"}' \
  --output reply.mp3

curl -s http://localhost:5050/v1/models
curl -s http://localhost:5050/health
```
