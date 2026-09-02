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
    decision_source: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Paginated audit log with optional filters."""
    q = select(AuditLog).order_by(AuditLog.timestamp.desc())
    if agent_name:
        q = q.where(AuditLog.agent_name == agent_name)
    if case_id:
        q = q.where(AuditLog.case_id == case_id)
    if decision_source and decision_source != "ALL":
        q = q.where(AuditLog.decision_source == decision_source)

    offset = (page - 1) * limit
    result = await db.execute(q.offset(offset).limit(limit))
    logs = [a.to_dict() for a in result.scalars()]

    count_q = select(func.count(AuditLog.id))
    if agent_name:
        count_q = count_q.where(AuditLog.agent_name == agent_name)
    if case_id:
        count_q = count_q.where(AuditLog.case_id == case_id)
    if decision_source and decision_source != "ALL":
        count_q = count_q.where(AuditLog.decision_source == decision_source)
    total = int((await db.execute(count_q)).scalar() or 0)

    return {"logs": logs, "total": total, "page": page, "pages": (total + limit - 1) // limit}


@audit_router.get("/{audit_id}")
async def get_audit_log(audit_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieve single audit log entry by ID."""
    result = await db.execute(select(AuditLog).where(AuditLog.id == audit_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return log.to_dict()


# ── Human Review Queue ────────────────────────────────────────────────────────
human_review_router = APIRouter(prefix="/api/human-review", tags=["human-review"])


@human_review_router.get("/queue")
async def get_review_queue(
    status: str = "PENDING",
    db: AsyncSession = Depends(get_db),
):
    """List human review items by status (PENDING, APPROVED, REJECTED)."""
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
    """
    Approve, reject, or modify a human review item.
    Approving runs recovery execution deterministically, creates audit logs, and resolves the case.
    """
    import json
    from datetime import datetime, timezone
    from app.models.outcome import Outcome
    from app.simulation.engine import deterministic_roll

    result = await db.execute(select(HumanReview).where(HumanReview.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review item not found")

    action = decision.action.upper()
    review.status = "APPROVED" if action in ("APPROVE", "APPROVED") else "REJECTED"
    review.reviewer_notes = decision.reviewer_notes
    review.reviewed_at = datetime.now(timezone.utc)
    if decision.modified_strategy:
        review.modified_strategy_json = json.dumps(decision.modified_strategy)

    # Fetch corresponding case
    case_result = await db.execute(
        select(RecoveryCase).where(RecoveryCase.case_id == review.case_id)
    )
    case = case_result.scalar_one_or_none()

    outcome_status = "STOPPED"
    recovered_amt = 0.0

    if case:
        case.human_escalation_required = False
        amount = case.revenue_at_risk or review.amount_at_risk or 50000.0

        if review.status == "APPROVED":
            # Approved by human operator -> execute recovery
            case.status = "EXECUTING"
            # Deterministic success calculation for human-guided recovery (high 85% success rate)
            roll = deterministic_roll(review.case_id, "human_approval_exec")
            success = roll < 0.85

            if success:
                case.status = "RECOVERED"
                case.outcome_status = "RECOVERED"
                case.recovered_amount = amount
                outcome_status = "RECOVERED"
                recovered_amt = amount
            else:
                case.status = "FAILED"
                case.outcome_status = "NOT_RECOVERED"
                outcome_status = "NOT_RECOVERED"
                recovered_amt = 0.0

            case.completed_at = datetime.now(timezone.utc)

            # Upsert Outcome
            outcome_res = await db.execute(select(Outcome).where(Outcome.case_id == case.case_id))
            out = outcome_res.scalar_one_or_none()
            if out:
                out.status = outcome_status
                out.recovered_amount = recovered_amt
                out.net_recovered = recovered_amt - (out.recovery_cost or 150.0)
            else:
                out = Outcome(
                    case_id=case.case_id,
                    status=outcome_status,
                    recovered_amount=recovered_amt,
                    recovery_cost=150.0,
                    net_recovered=recovered_amt - 150.0,
                    recovery_time_seconds=12.0,
                    strategy_used="HUMAN_APPROVED_EXECUTION",
                    notes=f"Human approved. Notes: {decision.reviewer_notes or 'None'}",
                    expected_recovery_value=amount * 0.85,
                )
                db.add(out)

            # Audit entry for Human Approval + Execution
            audit = AuditLog(
                case_id=case.case_id,
                agent_name="recovery_execution",
                step_index=8,
                decision="RECOVERED" if success else "EXECUTION_FAILED",
                reasoning=f"Human review approved by operator. Notes: {decision.reviewer_notes or 'Approved'}. Status: {case.status}.",
                confidence=1.0,
                decision_source="DETERMINISTIC",
                llm_used=0,
                used_fallback=0,
                input_json=json.dumps({"reviewer_action": "APPROVE", "notes": decision.reviewer_notes}),
                output_json=json.dumps({"status": case.status, "recovered_amount": recovered_amt}),
                duration_ms=25.0,
            )
            db.add(audit)

        else:
            # Rejected by human operator
            case.status = "STOPPED"
            case.outcome_status = "STOPPED"
            case.completed_at = datetime.now(timezone.utc)
            outcome_status = "STOPPED"
            recovered_amt = 0.0

            outcome_res = await db.execute(select(Outcome).where(Outcome.case_id == case.case_id))
            out = outcome_res.scalar_one_or_none()
            if out:
                out.status = "STOPPED"
            else:
                out = Outcome(
                    case_id=case.case_id,
                    status="STOPPED",
                    recovered_amount=0.0,
                    recovery_cost=0.0,
                    net_recovered=0.0,
                    recovery_time_seconds=0.0,
                    strategy_used="HUMAN_REJECTED",
                    notes=f"Human rejected. Notes: {decision.reviewer_notes or 'None'}",
                )
                db.add(out)

            audit = AuditLog(
                case_id=case.case_id,
                agent_name="compliance_policy_guardian",
                step_index=7,
                decision="HUMAN_REJECTED",
                reasoning=f"Human review rejected by operator. Notes: {decision.reviewer_notes or 'Rejected'}.",
                confidence=1.0,
                decision_source="DETERMINISTIC",
                llm_used=0,
                used_fallback=0,
                input_json=json.dumps({"reviewer_action": "REJECT", "notes": decision.reviewer_notes}),
                output_json=json.dumps({"status": "STOPPED"}),
                duration_ms=10.0,
            )
            db.add(audit)

    await db.commit()

    # Publish live feed event
    try:
        bus = get_event_bus()
        await bus.publish("live_feed", {
            "type": "case_resolved",
            "case_id": review.case_id,
            "status": case.status if case else review.status,
            "outcome": outcome_status,
            "recovered_amount": recovered_amt,
            "duration_seconds": 0.2,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass

    return {
        "message": f"Review {review.status}",
        "review_id": review_id,
        "case_id": review.case_id,
        "case_status": case.status if case else review.status,
        "outcome_status": outcome_status,
        "recovered_amount": recovered_amt,
    }


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
