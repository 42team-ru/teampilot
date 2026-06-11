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

PROXY_DIR    := infrastructure/yookassa-proxy

VOICE_RVC_DIR   := voice-rvc
VOICE_RVC_PORT  ?= 5050
VOICE_RVC_MODEL ?= prigozhin

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
# Voice-RVC (мем-голоса, локально на GPU)
# ============================================================

##@ Voice-RVC (локальный TTS с RVC-голосами, GPU)

.PHONY: voice-rvc-setup voice-rvc-up voice-rvc-cpu voice-rvc-test
voice-rvc-setup: ## venv 3.10 + зависимости + CUDA-torch (RTX) + проверка GPU
	cd $(VOICE_RVC_DIR) && uv venv --python 3.10
	cd $(VOICE_RVC_DIR) && uv pip install -r requirements.txt
	cd $(VOICE_RVC_DIR) && uv pip install --force-reinstall torch torchaudio --index-url https://download.pytorch.org/whl/cu124
	cd $(VOICE_RVC_DIR) && .venv/bin/python -c "import torch; print('TORCH', torch.__version__, 'CUDA', torch.cuda.is_available(), (torch.cuda.get_device_name(0) if torch.cuda.is_available() else '-'))"
voice-rvc-up:    ## Запустить на GPU (cuda:0), порт 5050
	cd $(VOICE_RVC_DIR) && RVC_MODELS_DIR=$(CURDIR)/$(VOICE_RVC_DIR)/rvc_models RVC_DEVICE=cuda:0 \
		.venv/bin/uvicorn app:app --host 0.0.0.0 --port $(VOICE_RVC_PORT)
voice-rvc-cpu:   ## Запустить на CPU (фолбэк, если torch/CUDA не подружились)
	cd $(VOICE_RVC_DIR) && RVC_MODELS_DIR=$(CURDIR)/$(VOICE_RVC_DIR)/rvc_models RVC_DEVICE=cpu:0 \
		.venv/bin/uvicorn app:app --host 0.0.0.0 --port $(VOICE_RVC_PORT)
voice-rvc-test:  ## Тест синтеза → /tmp/voice_rvc_test.mp3 (по умолч. модель zelensky)
	curl -s -X POST localhost:$(VOICE_RVC_PORT)/v1/audio/speech -H 'Content-Type: application/json' \
		-d '{"model":"$(VOICE_RVC_MODEL)","input":"Привет, я голосовой ассистент Пилот. Сколько задач в беклоге?"}' \
		--output /tmp/voice_rvc_test.mp3 && echo "→ /tmp/voice_rvc_test.mp3" && \
		(command -v ffplay >/dev/null && ffplay -autoexit -nodisp -loglevel quiet /tmp/voice_rvc_test.mp3 || echo "проиграй: ffplay /tmp/voice_rvc_test.mp3")

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

##@ YooKassa Proxy (русский VPS)

.PHONY: yk-proxy-up yk-proxy-down yk-proxy-logs yk-proxy-install
yk-proxy-install: ## Установить Docker на чистый Ubuntu/Debian сервер
	ssh -i ~/.ssh/id_rsa hexaend@$(YK_PROXY_HOST) "curl -fsSL https://get.docker.com | sudo sh && sudo usermod -aG docker hexaend"
yk-proxy-up:      ## Запустить прокси на русском VPS
	ssh -i ~/.ssh/id_rsa hexaend@$(YK_PROXY_HOST) "sudo mkdir -p /opt/yookassa-proxy && sudo chown hexaend:hexaend /opt/yookassa-proxy"
	scp -i ~/.ssh/id_rsa $(PROXY_DIR)/docker-compose.yml hexaend@$(YK_PROXY_HOST):/opt/yookassa-proxy/
	scp -i ~/.ssh/id_rsa $(PROXY_DIR)/Caddyfile hexaend@$(YK_PROXY_HOST):/opt/yookassa-proxy/
	ssh -i ~/.ssh/id_rsa hexaend@$(YK_PROXY_HOST) "cd /opt/yookassa-proxy && docker compose up -d --force-recreate"
yk-proxy-down:    ## Остановить прокси на русском VPS
	ssh -i ~/.ssh/id_rsa hexaend@$(YK_PROXY_HOST) "cd /opt/yookassa-proxy && docker compose down"
yk-proxy-logs:    ## Логи прокси
	ssh -i ~/.ssh/id_rsa hexaend@$(YK_PROXY_HOST) "cd /opt/yookassa-proxy && docker compose logs -f"

##@ Other

.PHONY: ps clean
ps:    ## Статус контейнеров
	$(COMPOSE) $(CORE_CFG) $(SERVICES_CFG) ps
clean: ## Удалить все контейнеры и volumes
	$(COMPOSE) $(CORE_CFG) $(SERVICES_CFG) \
		down --volumes --remove-orphans
