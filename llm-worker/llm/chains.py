from langchain_openai import ChatOpenAI

from llm.prompts import audio_status_prompt, audio_task_prompt, classifier_prompt, decision_prompt, file_summary_prompt, speaker_segments_prompt, status_prompt, status_query_prompt, sync_match_prompt, task_prompt
from llm.safe_parser import SafeJsonOutputParser
from settings import settings

# Температура 0.0 для обеих моделей — нам нужен детерминизм, а не креативность
# request_timeout — защита от вечного зависания Ollama (Kafka не объявит consumer мёртвым)
# max_retries=1 — одна попытка повтора, больше не нужно
_cheap = ChatOpenAI(
    model=settings.LLM_CHEAP_MODEL,
    base_url=settings.LLM_API_BASE,
    api_key=settings.LLM_API_KEY,
    temperature=0.0,
    request_timeout=60,
    max_retries=1,
)
_expensive = ChatOpenAI(
    model=settings.LLM_EXPENSIVE_MODEL,
    base_url=settings.LLM_API_BASE,
    api_key=settings.LLM_API_KEY,
    temperature=0.0,
    request_timeout=120,
    max_retries=1,
)

_safe_json = SafeJsonOutputParser()

# Собираем цепочки из новых промптов и безопасного парсера
classifier_chain = classifier_prompt | _cheap | _safe_json
task_chain = task_prompt | _expensive | _safe_json
status_chain = status_prompt | _expensive | _safe_json
audio_task_chain = audio_task_prompt | _expensive | _safe_json
audio_status_chain = audio_status_prompt | _expensive | _safe_json
file_summary_chain = file_summary_prompt | _expensive | _safe_json
speaker_segments_chain = speaker_segments_prompt | _cheap | _safe_json
decision_chain = decision_prompt | _cheap | _safe_json
sync_match_chain = sync_match_prompt | _cheap | _safe_json
status_query_chain = status_query_prompt | _cheap | _safe_json
