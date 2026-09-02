"""
RECOVERX AI — Cases API
CRUD and simulation endpoints for recovery cases.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.recovery_case import RecoveryCase
from app.models.revenue_event import RevenueEvent
from app.models.customer import Customer
from app.orchestrator.runner import run_recovery_workflow

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.get("")
async def list_cases(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    event_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Paginated list of recovery cases."""
    q = select(RecoveryCase).order_by(RecoveryCase.id.desc())

    if status:
        q = q.where(RecoveryCase.status == status)

    offset = (page - 1) * limit
    q = q.offset(offset).limit(limit)

    result = await db.execute(q)
    cases = [c.to_dict() for c in result.scalars()]

    # Count total
    from sqlalchemy import func
    count_q = select(func.count(RecoveryCase.id))
    if status:
        count_q = count_q.where(RecoveryCase.status == status)
    total = int((await db.execute(count_q)).scalar() or 0)

    return {
        "cases": cases,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@router.get("/{case_id}")
async def get_case(case_id: str, db: AsyncSession = Depends(get_db)):
    """Full case detail including all agent decisions."""
    result = await db.execute(
        select(RecoveryCase).where(RecoveryCase.case_id == case_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    case_dict = case.to_dict()

    # Load audit logs
    from app.models.audit_log import AuditLog
    audit_result = await db.execute(
        select(AuditLog)
        .where(AuditLog.case_id == case_id)
        .order_by(AuditLog.timestamp.asc())
    )
    case_dict["audit_logs"] = [a.to_dict() for a in audit_result.scalars()]

    # Load outcome
    from app.models.outcome import Outcome
    outcome_result = await db.execute(
        select(Outcome).where(Outcome.case_id == case_id)
    )
    outcome = outcome_result.scalar_one_or_none()
    if outcome:
        case_dict["outcome"] = outcome.to_dict()

    return case_dict


@router.post("/{case_id}/retry")
async def retry_case(case_id: str, db: AsyncSession = Depends(get_db)):
    """
    Run an immediate recovery retry on an actionable pending or failed recovery case.
    Executes deterministic simulation, transitions state, logs audit, and updates live feed.
    """
    import json
    from datetime import datetime, timezone
    from app.models.audit_log import AuditLog
    from app.models.outcome import Outcome
    from app.simulation.engine import deterministic_roll
    from app.eventbus import get_event_bus

    result = await db.execute(
        select(RecoveryCase).where(RecoveryCase.case_id == case_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    # Determine recovery success using deterministic hash
    amount = case.revenue_at_risk or 5000.0
    roll = deterministic_roll(case_id, "manual_retry")
    # 78% retry success probability for pending/scheduled actions
    success = roll < 0.78

    if success:
        case.status = "RECOVERED"
        case.outcome_status = "RECOVERED"
        case.recovered_amount = amount
    else:
        case.status = "FAILED"
        case.outcome_status = "NOT_RECOVERED"

    case.completed_at = datetime.now(timezone.utc)

    # Upsert outcome
    outcome_result = await db.execute(
        select(Outcome).where(Outcome.case_id == case_id)
    )
    outcome = outcome_result.scalar_one_or_none()
    if outcome:
        outcome.status = case.outcome_status
        outcome.recovered_amount = case.recovered_amount
        outcome.net_recovered = case.recovered_amount - (outcome.recovery_cost or 15.0)
    else:
        outcome = Outcome(
            case_id=case_id,
            status=case.outcome_status,
            recovered_amount=case.recovered_amount,
            recovery_cost=15.0,
            net_recovered=case.recovered_amount - 15.0,
            recovery_time_seconds=8.0,
            strategy_used="MANUAL_RETRY",
            notes="Manual recovery retry executed by operator.",
            expected_recovery_value=amount * 0.75,
        )
        db.add(outcome)

    # Audit log entry
    audit = AuditLog(
        case_id=case_id,
        agent_name="recovery_execution",
        step_index=8,
        decision="RECOVERED" if success else "RETRY_FAILED",
        reasoning=f"Operator triggered manual recovery retry. Outcome: {case.status}.",
        confidence=0.85,
        decision_source="DETERMINISTIC",
        llm_used=0,
        used_fallback=0,
        input_json=json.dumps({"action": "manual_retry", "amount": amount}),
        output_json=json.dumps({"success": success, "status": case.status, "recovered_amount": case.recovered_amount}),
        duration_ms=15.0,
    )
    db.add(audit)
    await db.commit()

    # Publish live event
    try:
        bus = get_event_bus()
        await bus.publish("live_feed", {
            "type": "case_resolved",
            "case_id": case_id,
            "status": case.status,
            "outcome": case.outcome_status,
            "recovered_amount": case.recovered_amount,
            "duration_seconds": 0.5,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass

    return {
        "message": f"Case retry executed: {case.status}",
        "case_id": case_id,
        "status": case.status,
        "recovered_amount": case.recovered_amount,
    }


@router.post("/{case_id}/stop")
async def stop_case(case_id: str, db: AsyncSession = Depends(get_db)):
    """
    Manually stop and close a recovery case.
    """
    import json
    from datetime import datetime, timezone
    from app.models.audit_log import AuditLog
    from app.models.outcome import Outcome
    from app.eventbus import get_event_bus

    result = await db.execute(
        select(RecoveryCase).where(RecoveryCase.case_id == case_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    case.status = "STOPPED"
    case.outcome_status = "STOPPED"
    case.completed_at = datetime.now(timezone.utc)

    # Upsert outcome
    outcome_result = await db.execute(
        select(Outcome).where(Outcome.case_id == case_id)
    )
    outcome = outcome_result.scalar_one_or_none()
    if outcome:
        outcome.status = "STOPPED"
    else:
        outcome = Outcome(
            case_id=case_id,
            status="STOPPED",
            recovered_amount=0.0,
            recovery_cost=0.0,
            net_recovered=0.0,
            recovery_time_seconds=0.0,
            strategy_used="STOP_RECOVERY",
            notes="Case stopped by operator.",
        )
        db.add(outcome)

    # Audit log
    audit = AuditLog(
        case_id=case_id,
        agent_name="compliance_policy_guardian",
        step_index=7,
        decision="STOPPED_BY_OPERATOR",
        reasoning="Recovery halted manually by operator.",
        confidence=1.0,
        decision_source="DETERMINISTIC",
        llm_used=0,
        used_fallback=0,
        duration_ms=5.0,
    )
    db.add(audit)
    await db.commit()

    try:
        bus = get_event_bus()
        await bus.publish("live_feed", {
            "type": "case_resolved",
            "case_id": case_id,
            "status": "STOPPED",
            "outcome": "STOPPED",
            "recovered_amount": 0.0,
            "duration_seconds": 0.1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass

    return {"message": "Case stopped", "case_id": case_id, "status": "STOPPED"}


class SimulateCaseRequest(BaseModel):
    amount: float
    event_type: str = "PAYMENT_FAILURE"
    failure_reason: str = "BANK_DECLINE"
    payment_method: str = "CARD"
    customer_tier: str = "STANDARD"
    contact_count_7d: int = 0
    previous_recovery_attempts: int = 0
    gateway: str = "Razorpay"


@router.post("/simulate")
async def simulate_case(
    request: SimulateCaseRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Run a single custom event through the complete multi-agent workflow.
    Used by the Simulation Lab page.
    """
    import uuid
    from datetime import datetime, timezone

    # Build synthetic event
    event_data = {
        "id": 0,
        "external_id": f"MANUAL-{uuid.uuid4().hex[:8].upper()}",
        "event_type": request.event_type,
        "amount": request.amount,
        "currency": "INR",
        "customer_id": "manual_test",
        "payment_method": request.payment_method,
        "failure_reason": request.failure_reason,
        "gateway": request.gateway,
        "gateway_error_code": "ERR_MANUAL",
        "status": "PENDING",
        "event_time": datetime.now(timezone.utc).isoformat(),
        "metadata": {"source": "simulation_lab"},
    }

    customer_data = {
        "id": 0,
        "external_id": "CUST-MANUAL",
        "name": "Simulation Test Customer",
        "tier": request.customer_tier,
        "preferred_payment_method": request.payment_method,
        "preferred_channel": "WHATSAPP",
        "best_contact_time": "10:00-12:00",
        "historical_recovery_rate": 0.65,
        "total_successful_payments": 10,
        "total_failed_payments": request.previous_recovery_attempts,
        "lifetime_value": request.amount * 10,
        "fatigue_score": min(1.0, request.contact_count_7d * 0.15),
        "contact_count_7d": request.contact_count_7d,
        "no_response_streak": max(0, request.contact_count_7d - 1),
        "opt_out": False,
        "payment_history": [],
        "contact_history": [],
    }

    result = await run_recovery_workflow(
        event_data=event_data,
        customer_data=customer_data,
        db=db,
        is_simulation=True,
    )

    return result
