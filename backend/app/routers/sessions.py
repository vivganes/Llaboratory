from __future__ import annotations
import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSession

from app.database import get_db, SessionLocal
from app.models import Session, PlanVersion
from app.schemas import SessionCreate, SessionOut, SessionDetailOut, EventOut, SessionRerunOut
from app.services.agent_loop import run_session, get_or_create_queue

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionOut])
def list_sessions(
    plan_version_id: str | None = None,
    status: str | None = None,
    db: DBSession = Depends(get_db),
):
    q = db.query(Session)
    if plan_version_id:
        q = q.filter(Session.plan_version_id == plan_version_id)
    if status:
        q = q.filter(Session.status == status)
    return q.order_by(Session.started_at.desc()).all()


@router.post("", response_model=SessionOut, status_code=201)
def create_session(body: SessionCreate, db: DBSession = Depends(get_db)):
    pv = db.get(PlanVersion, body.plan_version_id)
    if not pv:
        raise HTTPException(400, "PlanVersion not found")

    session = Session(plan_version_id=body.plan_version_id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/run", response_model=SessionOut)
async def run_session_endpoint(
    session_id: str,
    background_tasks: BackgroundTasks,
    db: DBSession = Depends(get_db),
):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.status not in ("pending",):
        raise HTTPException(400, f"Session is already {session.status}")

    # Create SSE queue before launching background task
    get_or_create_queue(session_id)

    # Launch agent loop as a FastAPI background task (runs after response is sent)
    background_tasks.add_task(run_session, session_id, SessionLocal)

    db.refresh(session)
    return session


@router.get("/{session_id}", response_model=SessionDetailOut)
def get_session(session_id: str, db: DBSession = Depends(get_db)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session


@router.post("/{session_id}/abort", response_model=SessionOut)
def abort_session(session_id: str, db: DBSession = Depends(get_db)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.status not in ("running", "pending"):
        raise HTTPException(400, "Session is not running")
    session.status = "aborted"
    session.termination_reason = "aborted"
    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/rerun", response_model=SessionRerunOut)
def rerun_session(session_id: str, db: DBSession = Depends(get_db)):
    """Create a new session using the same PlanVersion and run it."""
    original = db.get(Session, session_id)
    if not original:
        raise HTTPException(404, "Session not found")

    pv = original.plan_version
    new_session = Session(plan_version_id=pv.id)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    return SessionRerunOut(
        original_session_id=session_id,
        new_session_id=new_session.id,
        plan_version_id=pv.id,
    )


@router.post("/{session_id}/rerun-and-run", response_model=SessionRerunOut)
async def rerun_and_run_session(
    session_id: str,
    background_tasks: BackgroundTasks,
    db: DBSession = Depends(get_db),
):
    """Rerun: create a new session from the same PlanVersion and immediately start it."""
    original = db.get(Session, session_id)
    if not original:
        raise HTTPException(404, "Session not found")

    pv = original.plan_version
    new_session = Session(plan_version_id=pv.id)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    get_or_create_queue(new_session.id)
    background_tasks.add_task(run_session, new_session.id, SessionLocal)

    return SessionRerunOut(
        original_session_id=session_id,
        new_session_id=new_session.id,
        plan_version_id=pv.id,
    )
@router.get("/{session_id}/stream")
async def stream_session(session_id: str, db: DBSession = Depends(get_db)):
    """SSE endpoint — streams live events while session is running."""
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    queue = get_or_create_queue(session_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                yield "event: ping\ndata: {}\n\n"
                continue

            if item is None:
                yield "event: done\ndata: {}\n\n"
                break

            yield f"event: message\ndata: {json.dumps(item)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{session_id}/events", response_model=list[EventOut])
def get_events(session_id: str, db: DBSession = Depends(get_db)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session.events


@router.get("/{session_id}/metrics")
def get_session_metrics(session_id: str, db: DBSession = Depends(get_db)):
    """Per-session derived metrics."""
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    events = session.events
    tool_calls: dict[str, int] = {}
    tool_sequence: list[str] = []
    hallucinated_count = 0
    error_count = 0
    call_made = False

    for ev in events:
        payload = json.loads(ev.payload) if isinstance(ev.payload, str) else ev.payload
        if ev.type == "tool_call":
            name = payload.get("name", "unknown")
            tool_calls[name] = tool_calls.get(name, 0) + 1
            tool_sequence.append(name)
            call_made = True
        elif ev.type == "hallucinated_tool_call":
            hallucinated_count += 1
        elif ev.type == "tool_error":
            error_count += 1

    totals = json.loads(session.totals) if isinstance(session.totals, str) else session.totals

    return {
        "session_id": session_id,
        "status": session.status,
        "termination_reason": session.termination_reason,
        "any_tool_called": call_made,
        "tool_calls": tool_calls,
        "tool_sequence": tool_sequence,
        "hallucinated_tool_calls": hallucinated_count,
        "tool_errors": error_count,
        **totals,
    }
