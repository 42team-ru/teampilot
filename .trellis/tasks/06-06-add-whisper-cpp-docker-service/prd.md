# Add Whisper Docker Service

## Goal

Добавить локальный Whisper ASR-сервер в Docker-инфраструктуру.
`make whisper-up` — поднимает сервис; `WHISPER_API_BASE=http://whisper:8000/v1` — подключает LLM Worker.

## Requirements

- Образ: `ghcr.io/fedirz/faster-whisper-server:latest-cpu` (OpenAI-compatible `/v1/audio/transcriptions`)
- Новый файл `docker-compose.ai.yml`
- Makefile: `whisper-up`, `whisper-down`, `whisper-logs`
- Модель кешируется в volume (не качать при каждом рестарте)
- Входит в ту же сеть `microservices-network`
- Порт `8000` (внутри сети) / `8002` (снаружи, чтобы не конфликтовать)

## Out of Scope

- GPU-версия (отдельный compose при необходимости)
- Автовключение в `dev-up` (опционально)
