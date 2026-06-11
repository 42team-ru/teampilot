from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from loguru import logger
from pydantic import BaseModel

from session_manager import is_active, start_session, stop_session


class StartSessionRequest(BaseModel):
    meeting_id: str
    meeting_url: str
    team_id: str = ""


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("telemost-bot starting")
    yield
    logger.info("telemost-bot shutting down")


app = FastAPI(title="telemost-bot", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/sessions", status_code=201)
async def create_session(req: StartSessionRequest):
    """Start a new Playwright session for the given meeting."""
    if is_active(req.meeting_id):
        return {"meeting_id": req.meeting_id, "active": True, "detail": "already running"}
    try:
        await start_session(meeting_id=req.meeting_id, meeting_url=req.meeting_url, team_id=req.team_id)
    except Exception as e:
        logger.error("Failed to start session: meeting_id={} error={}", req.meeting_id, e)
        raise HTTPException(status_code=500, detail=str(e))
    return {"meeting_id": req.meeting_id, "active": True}


@app.delete("/sessions/{meeting_id}", status_code=200)
async def delete_session(meeting_id: str):
    """Stop and clean up a running session."""
    if not is_active(meeting_id):
        raise HTTPException(status_code=404, detail="session not found")
    await stop_session(meeting_id)
    return {"meeting_id": meeting_id, "active": False}


@app.get("/sessions/{meeting_id}")
async def get_session(meeting_id: str):
    """Check whether a session is active."""
    return {"meeting_id": meeting_id, "active": is_active(meeting_id)}
