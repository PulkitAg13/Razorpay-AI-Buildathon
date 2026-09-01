"""RECOVERX AI — Agent Status, Audit, Human Review, and WebSocket APIs."""

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import asyncio

from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.human_review import HumanReview
from app.models.recovery_case import RecoveryCase
from app.eventbus import get_event_bus

# ── Agent Status ──────────────────────────────────────────────────────────────
agents_router = APIRouter(prefix="/api/agents", tags=["agents"])

AGENT_NAMES = [
    "revenue_sentinel", "root_cause_diagnosis", "customer_context_intelligence",
    "recovery_opportunity", "recovery_strategy_planner", "recovery_digital_twin",
    "compliance_policy_guardian", "recovery_execution", "outcome_monitor",
    "learning_optimization",
]


@agents_router.get("/status")
async def get_agent_status(db: AsyncSession = Depends(get_db)):
    """Live agent status and throughput metrics."""
    from app.llm import get_llm_provider
    provider = get_llm_provider()

    statuses = []
    for name in AGENT_NAMES:
        count_result = await db.execute(
            select(func.count(AuditLog.id)).where(AuditLog.agent_name == name)
        )
        total = int(count_result.scalar() or 0)

        error_result = await db.execute(
            select(func.count(AuditLog.id)).where(
                AuditLog.agent_name == name, AuditLog.had_error == 1
            )
        )
        errors = int(error_result.scalar() or 0)

        fallback_result = await db.execute(
            select(func.count(AuditLog.id)).where(
                AuditLog.agent_name == name, AuditLog.used_fallback == 1
            )
        )
        fallbacks = int(fallback_result.scalar() or 0)

        avg_dur_result = await db.execute(
            select(func.avg(AuditLog.duration_ms)).where(AuditLog.agent_name == name)
        )
        avg_dur = float(avg_dur_result.scalar() or 0)

        statuses.append({
            "agent_name": name,
            "display_name": name.replace("_", " ").title(),
            "total_invocations": total,
            "error_count": errors,
            "fallback_count": fallbacks,
            "success_rate": round((total - errors) / total * 100, 1) if total > 0 else 100.0,
            "avg_duration_ms": round(avg_dur, 1),
            "status": "ACTIVE" if total > 0 else "IDLE",
        })

    return {
        "agents": statuses,
        "llm_provider": provider.provider_name,
        "total_invocations": sum(a["total_invocations"] for a in statuses),
    }


# ── Audit Explorer ────────────────────────────────────────────────────────────
audit_router = APIRouter(prefix="/api/audit", tags=["audit"])


@audit_router.get("")
async def list_audit_logs(
    page: int = 1,
    limit: int = 50,
    agent_name: Optional[str] = None,
    case_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Paginated audit log with optional filters."""
    q = select(AuditLog).order_by(AuditLog.timestamp.desc())
    if agent_name:
        q = q.where(AuditLog.agent_name == agent_name)
    if case_id:
        q = q.where(AuditLog.case_id == case_id)

    offset = (page - 1) * limit
    result = await db.execute(q.offset(offset).limit(limit))
    logs = [a.to_dict() for a in result.scalars()]

    count_q = select(func.count(AuditLog.id))
    if agent_name:
        count_q = count_q.where(AuditLog.agent_name == agent_name)
    if case_id:
        count_q = count_q.where(AuditLog.case_id == case_id)
    total = int((await db.execute(count_q)).scalar() or 0)

    return {"logs": logs, "total": total, "page": page, "pages": (total + limit - 1) // limit}


# ── Human Review Queue ────────────────────────────────────────────────────────
human_review_router = APIRouter(prefix="/api/human-review", tags=["human-review"])


@human_review_router.get("/queue")
async def get_review_queue(
    status: str = "PENDING",
    db: AsyncSession = Depends(get_db),
):
    """List pending human review items."""
    result = await db.execute(
        select(HumanReview)
        .where(HumanReview.status == status)
        .order_by(HumanReview.created_at.desc())
    )
    return {"items": [r.to_dict() for r in result.scalars()]}


class ReviewDecision(BaseModel):
    action: str  # APPROVE | REJECT | MODIFY
    reviewer_notes: Optional[str] = None
    modified_strategy: Optional[dict] = None


@human_review_router.post("/{review_id}/decide")
async def decide_review(
    review_id: int,
    decision: ReviewDecision,
    db: AsyncSession = Depends(get_db),
):
    """Approve, reject, or modify a human review item."""
    import json
    from datetime import datetime, timezone

    result = await db.execute(select(HumanReview).where(HumanReview.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review item not found")

    review.status = decision.action
    review.reviewer_notes = decision.reviewer_notes
    review.reviewed_at = datetime.now(timezone.utc)
    if decision.modified_strategy:
        review.modified_strategy_json = json.dumps(decision.modified_strategy)

    # Update the case status
    case_result = await db.execute(
        select(RecoveryCase).where(RecoveryCase.case_id == review.case_id)
    )
    case = case_result.scalar_one_or_none()
    if case:
        case.status = "COMPLETED" if decision.action == "APPROVE" else "STOPPED"
        case.human_escalation_required = False

    await db.commit()
    return {"message": f"Review {decision.action}D", "review_id": review_id}


# ── WebSocket Live Feed ────────────────────────────────────────────────────────
ws_router = APIRouter(tags=["websocket"])


@ws_router.websocket("/ws/live-feed")
async def websocket_live_feed(websocket: WebSocket):
    """
    WebSocket endpoint for real-time agent activity stream.
    Replays recent events on connect, then streams live.
    """
    await websocket.accept()
    bus = get_event_bus()

    try:
        # Replay recent events
        recent = await bus.get_recent("live_feed", limit=30)
        for event in recent:
            await websocket.send_json(event)

        # Stream live events
        async for event in bus.subscribe("live_feed"):
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
