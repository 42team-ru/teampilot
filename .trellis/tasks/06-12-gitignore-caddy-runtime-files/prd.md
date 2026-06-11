# gitignore: caddy runtime files

## Goal

Добавить в `.gitignore` runtime-файлы Caddy, которые создаются Docker-контейнером и мешают `git rebase`.

## Requirements

* Добавить паттерны для `infrastructure/caddy/config/caddy/` и `infrastructure/caddy/data/caddy/`

## Acceptance Criteria

* [ ] `git status` не показывает caddy runtime-файлы как untracked

## Out of Scope

* Изменение самих caddy-конфигов
