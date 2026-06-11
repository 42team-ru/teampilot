# Исправить тему Mini App — использовать Telegram CSS переменные

## Goal

В тёмной теме Telegram фон сливается с кнопками и текстом из-за малого контраста oklch-значений. Решение: использовать нативные CSS-переменные Telegram (`--tg-theme-*`) как первичные значения с oklch-fallback для браузера.

## Decision

**Approach**: Telegram CSS vars (`var(--tg-theme-bg-color, <oklch>)`)
- `:root` — Telegram vars + light oklch fallback
- `.dark` — Telegram vars + dark oklch fallback (для тестирования в браузере)

## Requirements

- `mini-app/src/index.css` — переписать `:root` и `.dark` чтобы использовать `var(--tg-theme-*, oklch-fallback)`
- Маппинг:
  - `--background` → `var(--tg-theme-bg-color, ...)`
  - `--card/--popover` → `var(--tg-theme-secondary-bg-color, ...)`
  - `--foreground` → `var(--tg-theme-text-color, ...)`
  - `--muted-foreground` → `var(--tg-theme-hint-color, ...)`
  - `--primary` → `var(--tg-theme-button-color, ...)`
  - `--primary-foreground` → `var(--tg-theme-button-text-color, ...)`

## Out of Scope

- Исправление бага OnboardingPage (вызов неправильного auth endpoint) — отдельная задача

## Technical Notes

- Telegram vars инжектируются `telegram-web-app.js` в `:root` при открытии в Telegram
- В браузере без Telegram vars нет → работают oklch fallback
