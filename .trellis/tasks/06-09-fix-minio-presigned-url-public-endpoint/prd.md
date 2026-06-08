# fix-minio-presigned-url-public-endpoint

## Goal

Сделать так, чтобы ссылка «⬇️ Скачать файл» в боте открывалась у пользователя в браузере.
Сейчас presigned URL содержит внутренний адрес MinIO (`http://localhost:9000` или `http://minio:9000`),
который недоступен снаружи Docker-сети → файл нельзя скачать.

## What I already know

* `S3Properties` (s3-common) уже имеет поле `presignedEndpoint` — отдельный публичный URL для presigner.
* `S3AutoConfiguration` уже использует его: если `presignedEndpoint` не задан → фолбэк на `endpoint`.
* `application.yml` **не экспортирует** `presignedEndpoint` через env-переменную → поле всегда пустое.
* `docker-compose.services.yml` содержит `APP_S3_PRESIGNED_ENDPOINT: ${S3_SERVER_URL}` — но только для
  `auth-service`, не для monolith.
* `.env.example` имеет `S3_SERVER_URL=https://s3.42team.ru` — задуманный публичный URL MinIO.
* Caddyfile: маршрут `s3.42team.ru → minio:9000` **закомментирован** — пока недоступен через домен.
* MinIO порт `9000` проброшен напрямую: `"${S3_PORT:-9000}:9000"`.
* Presigned URL истекает через 15 минут (`presigned-url-expiry: 15m`).
* Monolith в prod-Caddyfile проксируется как `monolith:8080` — значит в prod он в Docker.
  В dev запускается локально через `./gradlew bootRun`.

## Requirements

* `application.yml` принимает `S3_PRESIGNED_ENDPOINT` env-переменную для `app.s3.presigned-endpoint`.
* Monolith (docker-compose) получает `APP_S3_PRESIGNED_ENDPOINT: ${S3_SERVER_URL}`.
* `.env.example` документирует переменную.
* Presigned URL в ответе API содержит публичный хост (не `localhost`, не `minio`).

## Acceptance Criteria

* [ ] Пользователь Telegram нажимает «⬇️ Скачать файл» → браузер открывает файл (или скачивает).
* [ ] В dev: `S3_PRESIGNED_ENDPOINT=http://<IP>:9000` работает.
* [ ] В prod: при раскомментированном `s3.42team.ru` в Caddyfile — URL `https://s3.42team.ru/...` открывается.

## Decision (ADR-lite)

**Context**: presigned URL нужен публичный хост; Caddyfile маршрут `s3.42team.ru` закомментирован.
**Decision**: использовать прямой порт MinIO `http://SERVER_IP:9000`. Caddyfile не трогаем.
**Consequences**: нет HTTPS для ссылок на скачивание; для prod можно позже включить Caddy-маршрут.

## Technical Approach

1. `application.yml` — добавить:
   ```yaml
   presigned-endpoint: ${S3_PRESIGNED_ENDPOINT:}
   ```
2. `.env.example` — добавить переменную с пояснением:
   ```bash
   # Публичный URL MinIO для presigned download-ссылок (что увидит браузер пользователя)
   # В dev: http://<IP-сервера>:9000 ; в prod с Caddy: https://s3.42team.ru
   S3_PRESIGNED_ENDPOINT=http://localhost:9000
   ```

## Out of Scope

* Раскомментирование `s3.42team.ru` в Caddyfile.
* Изменение логики генерации presigned URL в S3Service.
* Увеличение времени жизни URL.

## Technical Notes

* `S3AutoConfiguration.java`: `builder.endpointOverride(URI.create(presignEndpoint))` — уже готово.
* `TeamService.java:231`: `s3Service.presignDownload(file.getBucket(), file.getS3Key())`.
* `bot/handlers/member.py:490-491`: отображает `downloadUrl` из API-ответа.
* Файлы для изменения:
  - `backend/monolith/src/main/resources/application.yml`
  - `infrastructure/docker/docker-compose.*.yml` (где monolith)
  - `.env.example`
  - `infrastructure/caddy/Caddyfile` (опционально)
