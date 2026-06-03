from langchain_openai import ChatOpenAI

from llm.prompts import classifier_prompt, status_prompt, task_prompt
from llm.safe_parser import SafeJsonOutputParser
from settings import settings

# Температура 0.0 для обеих моделей — нам нужен детерминизм, а не креативность
_cheap = ChatOpenAI(
    model=settings.LLM_CHEAP_MODEL,
    base_url=settings.LLM_API_BASE,
    api_key=settings.LLM_API_KEY,
    temperature=0.0,
)
_expensive = ChatOpenAI(
    model=settings.LLM_EXPENSIVE_MODEL,
    base_url=settings.LLM_API_BASE,
    api_key=settings.LLM_API_KEY,
    temperature=0.0,
)

_safe_json = SafeJsonOutputParser()

# Собираем цепочки из новых промптов и безопасного парсера
classifier_chain = classifier_prompt | _cheap | _safe_json
task_chain = task_prompt | _expensive | _safe_json
status_chain = status_prompt | _expensive | _safe_json
