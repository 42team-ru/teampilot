# ============================================================
# Configuration
# ============================================================

ifneq (,$(wildcard .env))
  include .env
  export
endif

DOCKER_DIR  := infrastructure/docker
PROJECT_DIR := .
ENV_FILE    := .env
BACKEND_DIR := $(CURDIR)/backend

REGISTRY := ghcr.io
OWNER    := 42team-ru

COMPOSE := docker compose --project-directory $(PROJECT_DIR) --env-file $(ENV_FILE)

CORE_CFG     := -f $(DOCKER_DIR)/docker-compose.core.yml
SERVICES_CFG := -f $(DOCKER_DIR)/docker-compose.services.yml
AI_CFG       := -f $(DOCKER_DIR)/docker-compose.ai.yml

PROTO_SRC    := backend/core/kafka-proto-common/src/main/proto
PROTO_PY_OUT := llm-worker/proto_generated

# ============================================================
# Help
# ============================================================

.PHONY: help
help: ## Показать список команд
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage: make \033[36m<target>\033[0m\n"} \
	  /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } \
	  /^[a-zA-Z_-]+:.*##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 }' \
	  $(MAKEFILE_LIST)
	@echo ""

# ============================================================
# Core
# ============================================================

##@ Core (БД, Kafka, MinIO, Qdrant, Caddy)

.PHONY: core-up core-down core-logs
core-up:   ## Запустить
	$(COMPOSE) $(CORE_CFG) up -d
core-down: ## Остановить
	$(COMPOSE) $(CORE_CFG) down
core-logs: ## Логи
	$(COMPOSE) $(CORE_CFG) logs -f

# ============================================================
# Services
# ============================================================

##@ Services (monolith, bot, llm-worker)

.PHONY: services-up services-down services-logs
services-up:   ## Запустить (с пересборкой Python-образов)
	$(COMPOSE) $(SERVICES_CFG) up -d --build
services-down: ## Остановить
	$(COMPOSE) $(SERVICES_CFG) down
services-logs: ## Логи
	$(COMPOSE) $(SERVICES_CFG) logs -f

# ============================================================
# Dev
# ============================================================

##@ Dev (core + services)

.PHONY: dev-up dev-down dev-logs deploy
dev-up:   ## Поднять всё окружение (локальная сборка Python-образов)
	$(COMPOSE) $(CORE_CFG) $(SERVICES_CFG) up -d --build
	@echo "Dev окружение запущено"
dev-down: ## Остановить
	$(COMPOSE) $(CORE_CFG) $(SERVICES_CFG) down
dev-logs: ## Логи
	$(COMPOSE) $(CORE_CFG) $(SERVICES_CFG) logs -f
deploy:   ## Задеплоить с пулом образов из GHCR (для сервера)
	$(COMPOSE) $(CORE_CFG) $(SERVICES_CFG) up -d --remove-orphans

# ============================================================
# AI
# ============================================================

##@ AI (Whisper ASR локально, порт 8002)

.PHONY: whisper-up whisper-down whisper-logs
whisper-up:   ## Запустить
	$(COMPOSE) $(AI_CFG) up -d
whisper-down: ## Остановить
	$(COMPOSE) $(AI_CFG) down
whisper-logs: ## Логи
	$(COMPOSE) $(AI_CFG) logs -f

# ============================================================
# Backend images (Jib)
# ============================================================

##@ Backend images

.PHONY: build push release
build:   ## Собрать monolith локально (jibDockerBuild)
	cd $(BACKEND_DIR) && chmod +x gradlew && ./gradlew --no-daemon :monolith:jibDockerBuild
push:    ## Запушить monolith в ghcr.io/$(OWNER)
	docker push $(REGISTRY)/$(OWNER)/monolith:latest
release: ## Собрать и запушить monolith (jib)
	cd $(BACKEND_DIR) && chmod +x gradlew && ./gradlew --no-daemon :monolith:jib

# ============================================================
# Proto
# ============================================================

##@ Proto

.PHONY: proto-gen
proto-gen: ## Сгенерировать Python-классы из .proto
	@echo "Генерация из $(PROTO_SRC)..."
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

##@ Other

.PHONY: ps clean
ps:    ## Статус контейнеров
	$(COMPOSE) $(CORE_CFG) $(SERVICES_CFG) ps
clean: ## Удалить все контейнеры и volumes
	$(COMPOSE) $(CORE_CFG) $(SERVICES_CFG) \
		down --volumes --remove-orphans
