# Seed users on startup: SYSTEM_ADMIN + USER

## Goal

При старте Spring-приложения создавать двух seed-пользователей (если их ещё нет):
один с ролью `SYSTEM_ADMIN`, один с `USER`. Нужно для разработки и тестирования бота.

## Requirements

- `ApplicationRunner` компонент проверяет при старте: существуют ли seed-пользователи
- Если нет — создаёт, если есть — пропускает (идемпотентно)
- Seed SYSTEM_ADMIN: `telegramId = 1`, `telegramLogin = "seed_admin"`, `firstName = "Seed Admin"`
- Seed USER: `telegramId = 2`, `telegramLogin = "seed_user"`, `firstName = "Seed User"`
- Роли из актуального `User.Role`: `SYSTEM_ADMIN`, `USER`
- Логировать факт создания (info-лог)

## Acceptance Criteria

- [ ] При первом старте в БД появляются два пользователя
- [ ] При повторном старте дублей нет
- [ ] Компилируется

## Technical Approach

`DataSeeder.java` — `@Component implements ApplicationRunner`  
Использует `UserRepository.findByTelegramId`, если пусто — `userRepository.save(new User(...))`

## Out of Scope

- Никаких паролей/JWT — seed только для тестов, аутентификация через бот-инвайты
