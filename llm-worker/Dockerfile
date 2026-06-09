FROM python:3.12-slim AS proto-builder

COPY --from=ghcr.io/astral-sh/uv:0.11.19 /uv /bin/uv

WORKDIR /build

COPY llm-worker/pyproject.toml llm-worker/uv.lock ./
RUN uv sync --frozen

COPY backend/core/kafka-proto-common/src/main/proto ./proto_src
RUN mkdir -p proto_generated && \
    uv run python -m grpc_tools.protoc \
        -I./proto_src \
        --python_out=proto_generated \
        --pyi_out=proto_generated \
        ru/team42/events/message_batch.proto && \
    find proto_generated -type d -exec touch {}/__init__.py \;

FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.19 /uv /bin/uv

WORKDIR /app

COPY llm-worker/pyproject.toml llm-worker/uv.lock ./
RUN uv sync --frozen --no-dev

COPY llm-worker/ .
COPY --from=proto-builder /build/proto_generated ./proto_generated

ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "main.py"]
