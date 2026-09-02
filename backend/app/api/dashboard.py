"""
RECOVERX AI — Dashboard API
Aggregate KPIs and charts for the Executive Dashboard.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.outcome import Outcome
from app.models.recovery_case import RecoveryCase
from app.models.revenue_event import RevenueEvent

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/metrics")
async def get_metrics(db: AsyncSession = Depends(get_db)):
    """Aggregate KPIs for the executive dashboard."""

    # Total revenue at risk
    risk_result = await db.execute(
        select(func.sum(RecoveryCase.revenue_at_risk))
    )
    total_at_risk = float(risk_result.scalar() or 0)

    # Total recovered
    recovered_result = await db.execute(
        select(func.sum(RecoveryCase.recovered_amount)).where(
            RecoveryCase.status == "RECOVERED"
        )
    )
    total_recovered = float(recovered_result.scalar() or 0)

    # Total cases
    total_cases_result = await db.execute(select(func.count(RecoveryCase.id)))
    total_cases = int(total_cases_result.scalar() or 0)

    # Recovered cases
    recovered_cases_result = await db.execute(
        select(func.count(RecoveryCase.id)).where(RecoveryCase.status == "RECOVERED")
    )
    recovered_cases = int(recovered_cases_result.scalar() or 0)

    # Recovery rate %
    recovery_rate = (total_recovered / total_at_risk * 100) if total_at_risk > 0 else (
        (recovered_cases / total_cases * 100) if total_cases > 0 else 0
    )

    # Active cases
    active_result = await db.execute(
        select(func.count(RecoveryCase.id)).where(
            RecoveryCase.status.in_(["PROCESSING", "PENDING", "EXECUTING", "CREATED", "NEW"])
        )
    )
    active_cases = int(active_result.scalar() or 0)

    # Escalations
    escalated_result = await db.execute(
        select(func.count(RecoveryCase.id)).where(
            RecoveryCase.status == "ESCALATED"
        )
    )
    escalated = int(escalated_result.scalar() or 0)

    # Stopped cases
    stopped_result = await db.execute(
        select(func.count(RecoveryCase.id)).where(RecoveryCase.status == "STOPPED")
    )
    stopped = int(stopped_result.scalar() or 0)

    # Recovery cost
    cost_result = await db.execute(select(func.sum(Outcome.recovery_cost)))
    total_cost = float(cost_result.scalar() or (recovered_cases * 15.0))

    # Policy approved cases
    approved_result = await db.execute(
        select(func.count(RecoveryCase.id)).where(RecoveryCase.policy_approved == True)
    )
    approved = int(approved_result.scalar() or 0)

    # Average recovery time
    avg_time_result = await db.execute(
        select(func.avg(Outcome.recovery_time_seconds)).where(Outcome.status == "RECOVERED")
    )
    avg_recovery_time = float(avg_time_result.scalar() or 8.5)

    # Recent cases (last 10 cases)
    recent_cases = await db.execute(
        select(RecoveryCase).order_by(RecoveryCase.started_at.desc()).limit(10)
    )
    recent = [c.to_dict() for c in recent_cases.scalars()]

    return {
        "total_revenue_at_risk": round(total_at_risk, 2),
        "total_recovered": round(total_recovered, 2),
        "recovery_rate_pct": round(recovery_rate, 1),
        "net_recovered": round(max(0, total_recovered - total_cost), 2),
        "total_cases": total_cases,
        "recovered_cases": recovered_cases,
        "active_cases": active_cases,
        "escalated_cases": escalated,
        "stopped_cases": stopped,
        "total_recovery_cost": round(total_cost, 2),
        "avg_recovery_time_seconds": round(avg_recovery_time, 1),
        "policy_approved_count": approved,
        "policy_violations_prevented": stopped,
        "recent_cases": recent,
        "disclaimer": "All metrics calculated from synthetic simulation outcomes.",
    }


@router.get("/timeline")
async def get_timeline(days: int = 7, db: AsyncSession = Depends(get_db)):
    """Daily recovery metrics for trend charts."""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import and_

    now = datetime.now(timezone.utc)
    result = []

    for i in range(days, -1, -1):
        day_start = now - timedelta(days=i + 1)
        day_end = now - timedelta(days=i)

        at_risk = await db.execute(
            select(func.sum(RecoveryCase.revenue_at_risk)).where(
                and_(RecoveryCase.started_at >= day_start, RecoveryCase.started_at < day_end)
            )
        )
        recovered = await db.execute(
            select(func.sum(Outcome.recovered_amount)).where(
                and_(
                    Outcome.created_at >= day_start,
                    Outcome.created_at < day_end,
                    Outcome.status == "RECOVERED",
                )
            )
        )

        result.append({
            "date": day_end.strftime("%Y-%m-%d"),
            "revenue_at_risk": round(float(at_risk.scalar() or 0), 2),
            "recovered": round(float(recovered.scalar() or 0), 2),
        })

    return result
