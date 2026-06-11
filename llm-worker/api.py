import time
from urllib.parse import quote

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, Response
from loguru import logger
from pydantic import BaseModel

from infra.qdrant import search_knowledge

app = FastAPI(title="llm-worker knowledge API", docs_url=None, redoc_url=None)


@app.get("/knowledge/search")
async def knowledge_search(
    team_id: str = Query(..., description="Team UUID"),
    q: str = Query(..., description="Search query"),
    limit: int = Query(5, ge=1, le=20),
) -> JSONResponse:
    results = search_knowledge(q, team_id, limit=limit)
    return JSONResponse(content=results)


class VoiceAnswerRequest(BaseModel):
    text: str
    team_id: str
    meeting_id: str = ""


@app.post("/voice/answer")
def voice_answer(req: VoiceAnswerRequest) -> Response:
    """Голосовой Q&A: текст вопроса → tool-calling по доске → ответ → TTS → аудио.

    Синхронный эндпоинт (FastAPI выполнит в threadpool) — внутри блокирующие
    httpx/openai вызовы. Возвращает аудио; текст ответа дублируется в заголовке
    X-Answer-Text (URL-encoded) для логов бота."""
    from infra.tts import synthesize
    from llm.voice_agent import answer as voice_answer_text

    t0 = time.monotonic()
    try:
        answer_text = voice_answer_text(req.text, req.team_id, req.meeting_id)
    except Exception as e:
        logger.opt(exception=True).error("voice/answer LLM failed: {}", e)
        answer_text = "Извините, не получилось обработать запрос."
    t1 = time.monotonic()

    audio = synthesize(answer_text)
    t2 = time.monotonic()

    logger.info(
        "voice/answer q={!r} a={!r} | llm={:.2f}s tts={:.2f}s total={:.2f}s",
        req.text, answer_text, t1 - t0, t2 - t1, t2 - t0,
    )
    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={"X-Answer-Text": quote(answer_text)},
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
