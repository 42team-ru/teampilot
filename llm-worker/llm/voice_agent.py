"""Голосовой агент-PM «Пилот»: текст вопроса → tool-calling по доске → короткий ответ.

Используется синхронным эндпоинтом /voice/answer. Инструменты дёргают Spring backend
(счётчики/списки/создание) и Qdrant (семантика). Ответ — 1-2 разговорных предложения,
которые затем озвучиваются (infra.tts)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from loguru import logger

from infra import backend_client
from infra.qdrant import search_tasks as qdrant_search_tasks
from llm.chains import _cheap
from settings import settings

MSK = timezone(timedelta(hours=3))
_MAX_TOOL_ROUNDS = 4

# Отдельная модель для голоса (если задана), иначе переиспользуем дешёвую цепочку
if settings.VOICE_LLM_MODEL:
    _llm = ChatOpenAI(
        model=settings.VOICE_LLM_MODEL,
        base_url=settings.LLM_API_BASE,
        api_key=settings.LLM_API_KEY,
        temperature=0.2,
        request_timeout=40,
        max_retries=1,
    )
else:
    _llm = _cheap


def _build_tools(team_id: str) -> list:
    """Инструменты, замкнутые на team_id текущего звонка."""

    @tool
    def get_board_overview() -> str:
        """Счётчики задач команды: сколько активных в каждой колонке (беклог, в работе и т.п.),
        сколько просрочено, сколько со сроком сегодня и завтра, сколько выполнено."""
        return json.dumps(backend_client.get_stats(team_id), ensure_ascii=False)

    @tool
    def list_tasks(
        overdue: bool = False,
        due_before: str | None = None,
        assignee_name: str | None = None,
        column: str | None = None,
    ) -> str:
        """Список активных задач команды с фильтрами. overdue=true — только просроченные.
        due_before — момент в ISO-8601 UTC (например 2026-06-13T21:00:00Z): вернуть задачи
        с дедлайном раньше него. assignee_name — имя исполнителя. column — название колонки."""
        return json.dumps(
            backend_client.voice_query(
                team_id,
                overdue=overdue,
                due_before=due_before,
                assignee_name=assignee_name,
                column=column,
            ),
            ensure_ascii=False,
        )

    @tool
    def search_tasks(query: str) -> str:
        """Семантический поиск задач команды по смыслу — когда надо найти задачу по теме,
        а не по точному названию (например «что-нибудь про оплату»)."""
        return json.dumps(qdrant_search_tasks(query, team_id, limit=5), ensure_ascii=False)

    @tool
    def create_task(
        title: str,
        assignee_name: str | None = None,
        deadline: str | None = None,
        description: str | None = None,
    ) -> str:
        """Создать новую задачу на доске. title — короткое название. assignee_name — на кого
        назначить (имя участника). deadline — момент в ISO-8601 UTC. Возвращает созданную задачу."""
        return json.dumps(
            backend_client.create_task(
                team_id,
                title,
                assignee_name=assignee_name,
                deadline=deadline,
                description=description,
            ),
            ensure_ascii=False,
        )

    return [get_board_overview, list_tasks, search_tasks, create_task]


def _system_prompt() -> SystemMessage:
    now = datetime.now(MSK)
    weekdays = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    return SystemMessage(content=(
        "Ты — голосовой ассистент-проджект-менеджер по имени Пилот, ты находишься в рабочем "
        "звонке команды и отвечаешь на вопросы про доску задач.\n"
        f"Сейчас {now:%Y-%m-%d %H:%M} по Москве, сегодня {weekdays[now.weekday()]}.\n"
        "Правила ответа:\n"
        "- Отвечай по-русски, коротко и разговорно — 1-2 предложения, как живая речь вслух.\n"
        "- Без списков, markdown, эмодзи и ссылок — это произносится голосом.\n"
        "- Для любых данных о задачах вызывай инструменты, не выдумывай.\n"
        "- Относительные сроки («до завтра», «до пятницы») переводи в конкретный момент "
        "ISO-8601 UTC для параметров инструментов, опираясь на текущую дату выше.\n"
        "- Если задач нет или данных недостаточно — честно и коротко скажи об этом.\n"
        "- Имена исполнителей передавай как есть (например «Олег»)."
    ))


def answer(text: str, team_id: str, meeting_id: str = "") -> str:
    """Главная точка: вопрос (текст) → ответ (текст) через tool-calling."""
    tools = _build_tools(team_id)
    tools_by_name = {t.name: t for t in tools}
    llm = _llm.bind_tools(tools)

    messages: list = [_system_prompt(), HumanMessage(content=text)]

    for _ in range(_MAX_TOOL_ROUNDS):
        ai: AIMessage = llm.invoke(messages)
        messages.append(ai)

        if not ai.tool_calls:
            return (ai.content or "").strip() or "Не нашёл, что ответить."

        for tc in ai.tool_calls:
            fn = tools_by_name.get(tc["name"])
            if fn is None:
                result = json.dumps({"error": f"unknown tool {tc['name']}"})
            else:
                try:
                    result = fn.invoke(tc["args"])
                except Exception as e:  # noqa: BLE001 — деградируем мягко, не роняем звонок
                    logger.opt(exception=True).warning("voice tool {} failed: {}", tc["name"], e)
                    result = json.dumps({"error": str(e)}, ensure_ascii=False)
            messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

    # Превышен лимит раундов — финальный ответ без инструментов
    final: AIMessage = _llm.invoke(messages)
    return (final.content or "").strip() or "Извините, не смог обработать запрос."
