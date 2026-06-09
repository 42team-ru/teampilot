# ============================================================
# Configuration
# ============================================================

ifneq (,$(wildcard .env))
  include .env
  export
endif

DOCKER_DIR   := infrastructure/docker
PROJECT_DIR  := .
ENV_FILE     := .env
BACKEND_DIR  := $(CURDIR)/backend

REGISTRY     := ghcr.io
OWNER        := 42team-ru
SERVICES     := monolith

COMPOSE := docker compose --project-directory $(PROJECT_DIR) --env-file $(ENV_FILE)

CORE_CFG     := -f $(DOCKER_DIR)/docker-compose.core.yml
OBS_CFG      := -f $(DOCKER_DIR)/docker-compose.observability.yml
SERVICES_CFG := -f $(DOCKER_DIR)/docker-compose.services.yml
AI_CFG       := -f $(DOCKER_DIR)/docker-compose.ai.yml

# ============================================================
# Help
# ============================================================

.PHONY: help
help:
	@echo ""
	@echo "  Core"
	@echo "    make core-up          — запустить core (БД, Kafka и т.д.)"
	@echo "    make core-down        — остановить core"
	@echo "    make core-logs        — логи core"
	@echo ""
	@echo "  Observability"
	@echo "    make obs-up           — запустить observability (Grafana, Loki и т.д.)"
	@echo "    make obs-down         — остановить observability"
	@echo "    make obs-logs         — логи observability"
	@echo ""
	@echo "  Services"
	@echo "    make services-up      — запустить сервисы"
	@echo "    make services-down    — остановить сервисы"
	@echo "    make services-logs    — логи сервисов"
	@echo ""
	@echo "  Dev  (core + services, без observability)"
	@echo "    make dev-up           — поднять dev окружение"
	@echo "    make dev-down         — остановить dev окружение"
	@echo "    make dev-logs         — логи dev окружения"
	@echo ""
	@echo "  Staging  (core + observability + services)"
	@echo "    make staging-up       — поднять staging окружение"
	@echo "    make staging-down     — остановить staging окружение"
	@echo ""
	@echo "  Images (backend)"
	@echo "    make build            — собрать образы локально (jibDockerBuild)"
	@echo "    make push             — запушить образы в $(REGISTRY)"
	@echo "    make release          — собрать и запушить (jib)"
	@echo ""
	@echo "  Frontend"
	@echo "    make frontend-build   — собрать Docker-образ frontend локально"
	@echo "    make frontend-push    — запушить образ frontend в $(REGISTRY)"
	@echo "    make frontend-release — собрать и запушить frontend"
	@echo ""
	@echo "  AI (Whisper ASR)"
	@echo "    make whisper-up       — поднять Whisper ASR (faster-whisper-server, порт 8002)"
	@echo "    make whisper-down     — остановить Whisper"
	@echo "    make whisper-logs     — логи Whisper"
	@echo ""
	@echo "  Other"
	@echo "    make seed             — заполнить БД тестовыми данными (DataFaker)"
	@echo "    make ps               — статус контейнеров"
	@echo "    make clean            — удалить все контейнеры и volumes"
	@echo ""

# ============================================================
# Core
# ============================================================

.PHONY: core-up core-down core-logs

core-up:
	$(COMPOSE) $(CORE_CFG) up -d

core-down:
	$(COMPOSE) $(CORE_CFG) down

core-logs:
	$(COMPOSE) $(CORE_CFG) logs -f

# ============================================================
# Observability
# ============================================================

.PHONY: obs-up obs-down obs-logs

obs-up:
	$(COMPOSE) $(OBS_CFG) up -d

obs-down:
	$(COMPOSE) $(OBS_CFG) down

obs-logs:
	$(COMPOSE) $(OBS_CFG) logs -f

# ============================================================
# Services
# ============================================================

.PHONY: services-up services-down services-logs

services-up:
	$(COMPOSE) $(SERVICES_CFG) up -d

services-down:
	$(COMPOSE) $(SERVICES_CFG) down

services-logs:
	$(COMPOSE) $(SERVICES_CFG) logs -f

# ============================================================
# AI (Whisper ASR)
# ============================================================

.PHONY: whisper-up whisper-down whisper-logs

whisper-up:
	$(COMPOSE) $(AI_CFG) up -d

whisper-down:
	$(COMPOSE) $(AI_CFG) down

whisper-logs:
	$(COMPOSE) $(AI_CFG) logs -f

# ============================================================
# Dev (core + services)
# ============================================================

.PHONY: dev-up dev-down dev-logs

dev-up: core-up services-up
	@echo "Dev окружение запущено"

dev-down:
	$(COMPOSE) $(CORE_CFG) $(SERVICES_CFG) down

dev-logs:
	$(COMPOSE) $(CORE_CFG) $(SERVICES_CFG) logs -f

# ============================================================
# Staging (core + observability + services)
# ============================================================

.PHONY: staging-up staging-down

staging-up: core-up obs-up services-up
	@echo "Staging окружение запущено"

staging-down:
	$(COMPOSE) $(CORE_CFG) $(OBS_CFG) $(SERVICES_CFG) down

# ============================================================
# Frontend
# ============================================================

.PHONY: frontend-build frontend-push frontend-release

frontend-build:
	@echo "Сборка образа frontend..."
	docker build -t $(FRONTEND_IMAGE):latest $(FRONTEND_DIR)

frontend-push:
	@echo "Пуш образа frontend в $(REGISTRY)/$(OWNER)..."
	docker push $(FRONTEND_IMAGE):latest

frontend-release: frontend-build frontend-push
	@echo "Frontend выпущен: $(FRONTEND_IMAGE):latest"

# ============================================================
# Images
# ============================================================

.PHONY: build push release

build:
	@echo "Сборка образов локально через Jib..."
	cd $(BACKEND_DIR) && chmod +x gradlew && ./gradlew --no-daemon --parallel clean
	@for svc in $(SERVICES); do \
		echo ">>> Сборка $$svc"; \
		cd $(BACKEND_DIR) && ./gradlew --no-daemon --parallel :$$svc:jibDockerBuild; \
	done

push:
	@echo "Пуш образов в $(REGISTRY)/$(OWNER)..."
	@for svc in $(SERVICES); do \
		IMAGE=$(REGISTRY)/$(OWNER)/$$svc:latest; \
		echo ">>> Push $$IMAGE"; \
		docker push "$$IMAGE"; \
	done

release:
	@echo "Сборка и пуш в $(REGISTRY)/$(OWNER)..."
	cd $(BACKEND_DIR) && chmod +x gradlew && ./gradlew --no-daemon --parallel clean
	@for svc in $(SERVICES); do \
		echo ">>> Release $$svc"; \
		cd $(BACKEND_DIR) && ./gradlew --no-daemon --parallel :$$svc:jib; \
	done

# ============================================================
# Other
# ============================================================

.PHONY: seed seed-docker

# Локально (postgres должен быть доступен на localhost:5432)
# SPRING_DATASOURCE_URL переопределяем явно — .env экспортирует Docker-hostname "postgres"
seed:
	cd backend && SPRING_DATASOURCE_URL="jdbc:postgresql://localhost:$(DB_PORT)/$(DB_NAME)?currentSchema=auth_schema" \
		./gradlew :data-seeder:run

# В Docker (требует собранного образа: make build)
seed-docker:
	$(COMPOSE) $(CORE_CFG) -f $(DOCKER_DIR)/docker-compose.seed.yml run --rm data-seeder

# ============================================================
# Proto
# ============================================================

PROTO_SRC    := backend/core/kafka-proto-common/src/main/proto
PROTO_PY_OUT := llm-worker/proto_generated

.PHONY: proto-gen

proto-gen:
	@echo "Генерация Python proto классов из $(PROTO_SRC)..."
	@cd llm-worker && uv run python -c "from pathlib import Path; Path('proto_generated').mkdir(parents=True, exist_ok=True)"
	cd llm-worker && uv run python -m grpc_tools.protoc \
		-I../$(PROTO_SRC) \
		--python_out=proto_generated \
		--pyi_out=proto_generated \
		ru/team42/events/message_batch.proto
	@cd llm-worker && uv run python -c "from pathlib import Path; root = Path('proto_generated'); root.joinpath('__init__.py').touch(); [p.joinpath('__init__.py').touch() for p in root.rglob('*') if p.is_dir()]"
	@echo "Done → $(PROTO_PY_OUT)/ru/team42/events/message_batch_pb2.py"

# ============================================================
# Other
# ============================================================

.PHONY: ps clean

ps:
	$(COMPOSE) $(CORE_CFG) $(OBS_CFG) $(SERVICES_CFG) ps

clean:
	$(COMPOSE) $(CORE_CFG) $(OBS_CFG) $(SERVICES_CFG) \
		down --volumes --remove-orphans
