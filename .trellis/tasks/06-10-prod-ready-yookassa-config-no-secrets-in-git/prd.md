# Prod-ready config: убрать секреты из git

## Goal

Убрать hardcoded тестовые кредиты YooKassa (и Telegram bot token) из `application.yml`,
чтобы они не попали в git при деплое. Сохранить удобство локальной разработки.

## Что уже известно

- `.gitignore` уже включает `.env` и `.env.*` — реальные ключи в безопасности
- `application.yml` строки 25-26 содержат `${YOOKASSA_SHOP_ID:1380700}` и `${YOOKASSA_SECRET_KEY:test_...}` — попадут в git
- `application.yml` строка 8 содержит реальный Telegram bot token как дефолт — тоже проблема
- Для прода: docker-compose уже прокидывает `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY` через env
- Spring Boot профиль по умолчанию: `dev` (строка 40 application.yml)
- `.env` уже содержит правильные кредиты, но Spring Boot не читает его автоматически

## Проблема

Для локального запуска `./gradlew bootRun` нужны кредиты — Spring не читает `.env` без доп. зависимостей.

## Варианты для локальной разработки

**Вариант A: `application-local.yml` (gitignored)**
- Создать файл `backend/monolith/src/main/resources/application-local.yml` с кредами
- Добавить `application-local.yml` в `.gitignore`
- Разработчик создаёт его один раз из `.env`
- Плюс: нет новых зависимостей, стандартный Spring подход

**Вариант B: `spring-dotenv` library**
- Добавить зависимость `me.paulschwarz:spring-dotenv`
- Spring Boot автоматически читает `.env` при старте
- Плюс: `.env` уже есть, ничего нового создавать не нужно
- Минус: новая зависимость

## Open Questions

- Какой вариант для локального дева предпочитаешь?

## Requirements (draft)

- [ ] Убрать hardcoded YooKassa shopId/secretKey из application.yml
- [ ] Убрать hardcoded Telegram bot token из application.yml
- [ ] Локальный дев по-прежнему работает без docker
- [ ] Прод работает через docker-compose env vars (уже работает)

## Out of Scope

- Миграция других секретов (JWT secret, MinIO) — они safe-to-default для локала
- Rotation/vault интеграция
