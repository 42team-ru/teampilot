from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

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


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
