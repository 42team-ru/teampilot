from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from settings import settings

_cheap = ChatOpenAI(
    model=settings.LLM_CHEAP_MODEL,
    base_url=settings.LLM_API_BASE,
    api_key=settings.LLM_API_KEY,
    temperature=0,
)
_expensive = ChatOpenAI(
    model=settings.LLM_EXPENSIVE_MODEL,
    base_url=settings.LLM_API_BASE,
    api_key=settings.LLM_API_KEY,
    temperature=0.1,
)

_json = JsonOutputParser()

classifier_chain = ChatPromptTemplate.from_messages([
    ("system",
     "Ты ассистент для анализа командного Telegram-чата. По батчу сообщений определи:\n"
     "1. Есть ли признак создания НОВОЙ задачи (нужно сделать X, возьми задачу, до пятницы Y).\n"
     "2. Есть ли СМЕНА СТАТУСА существующей задачи (готово, сделал, закрыл, назначил на).\n"
     "Ответь ТОЛЬКО JSON без markdown:\n"
     '{"has_task": bool, "confidence_task": 0.0-1.0, '
     '"has_status_change": bool, "confidence_status": 0.0-1.0}'),
    ("human", "{messages}"),
]) | _cheap | _json

task_chain = ChatPromptTemplate.from_messages([
    ("system",
     "Ты помощник PM. Извлеки задачу из сообщений Telegram-чата команды.\n"
     "Ответь ТОЛЬКО JSON без markdown:\n"
     '{"title": "...", "description": "...", "assignee": "username или null", '
     '"deadline": "ISO-8601 или null", "priority": "HIGH|MEDIUM|LOW"}'),
    ("human", "{messages}"),
]) | _expensive | _json

status_chain = ChatPromptTemplate.from_messages([
    ("system",
     "Ты трекер статусов. По сообщениям Telegram-чата найди смену статуса задачи.\n"
     "Ответь ТОЛЬКО JSON без markdown:\n"
     '{"task_hint": "о какой задаче речь", "assignee": "username или null", '
     '"action": "COMPLETE|ASSIGN|CANCEL"}'),
    ("human", "{messages}"),
]) | _expensive | _json
