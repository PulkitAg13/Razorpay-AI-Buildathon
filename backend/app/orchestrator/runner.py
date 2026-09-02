"""
RECOVERX AI — Orchestrator Runner
Runs the LangGraph recovery pipeline with timeout, retry limits, and graceful error handling.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestrator.graph import get_compiled_graph
from app.orchestrator.state import RecoveryWorkflowState

logger = logging.getLogger(__name__)

AGENT_TIMEOUT_SECONDS = 45
MAX_WORKFLOW_ERRORS = 3


async def run_recovery_workflow(
    event_data: dict[str, Any],
    customer_data: dict[str, Any],
    db: Optional[AsyncSession] = None,
    is_simulation: bool = False,
) -> dict[str, Any]:
    """
    Run the complete RECOVERX AI multi-agent recovery workflow.

    Args:
        event_data: Revenue event dict (from DB or API)
        customer_data: Customer dict (from DB)
        db: Optional async DB session for audit logging + DB updates
        is_simulation: If True, marks the case as a simulation run

    Returns:
        Final workflow state dict with all agent outputs
    """
    case_id = f"CASE-{uuid.uuid4().hex[:12].upper()}"
    started_at = datetime.now(timezone.utc)

    logger.info(f"[Runner] Starting recovery workflow: case_id={case_id}")

    # Publish start event
    try:
        from app.eventbus import get_event_bus
        bus = get_event_bus()
        await bus.publish("live_feed", {
            "type": "case_created",
            "case_id": case_id,
            "amount": event_data.get("amount", 0),
            "event_type": event_data.get("event_type"),
            "timestamp": started_at.isoformat(),
        })
    except Exception:
        pass

    # Build initial state
    initial_state: RecoveryWorkflowState = {
        "case_id": case_id,
        "event_id": str(event_data.get("id", "")),
        "event_data": event_data,
        "customer_raw": customer_data,
        "current_step": "start",
        "error_count": 0,
        "errors": [],
        "abort": False,
        "abort_reason": None,
        "policy_approved": False,
        "human_escalation_required": False,
        "recovered_amount": 0.0,
    }

    graph = get_compiled_graph()

    try:
        final_state = await asyncio.wait_for(
            graph.ainvoke(initial_state),
            timeout=AGENT_TIMEOUT_SECONDS * 12,  # Total pipeline timeout
        )
    except asyncio.TimeoutError:
        logger.error(f"[Runner] Workflow timed out for case {case_id}")
        final_state = {
            **initial_state,
            "abort": True,
            "abort_reason": "Workflow timeout",
            "outcome_status": "NOT_RECOVERED",
            "errors": ["Workflow timeout after 540 seconds"],
        }
    except Exception as exc:
        logger.error(f"[Runner] Unexpected error for case {case_id}: {exc}", exc_info=True)
        final_state = {
            **initial_state,
            "abort": True,
            "abort_reason": f"Unexpected error: {exc}",
            "outcome_status": "NOT_RECOVERED",
            "errors": [str(exc)],
        }

    # Determine final lifecycle status
    final_status = "COMPLETED"
    if final_state.get("human_escalation_required"):
        final_status = "ESCALATED"
    elif final_state.get("abort"):
        final_status = "STOPPED"
    elif final_state.get("outcome_status") == "RECOVERED":
        final_status = "RECOVERED"
    elif final_state.get("outcome_status") == "PENDING":
        final_status = "PENDING"
    elif final_state.get("outcome_status") in ("NOT_RECOVERED", "FAILED"):
        final_status = "FAILED"
    elif final_state.get("outcome_status"):
        final_status = final_state.get("outcome_status")

    final_state["status"] = final_status

    completed_at = datetime.now(timezone.utc)
    duration = (completed_at - started_at).total_seconds()
    logger.info(
        f"[Runner] Completed case {case_id} in {duration:.1f}s — "
        f"status={final_status} outcome={final_state.get('outcome_status', 'UNKNOWN')}"
    )

    # Persist case to DB
    if db is not None:
        try:
            await _persist_case(db, case_id, event_data, final_state, is_simulation, completed_at, final_status)
        except Exception as exc:
            logger.warning(f"[Runner] Case persistence failed: {exc}", exc_info=True)

    # Publish completion event
    try:
        from app.eventbus import get_event_bus
        bus = get_event_bus()
        await bus.publish("live_feed", {
            "type": "case_resolved",
            "case_id": case_id,
            "status": final_status,
            "outcome": final_state.get("outcome_status", "UNKNOWN"),
            "recovered_amount": final_state.get("recovered_amount", 0),
            "duration_seconds": duration,
            "timestamp": completed_at.isoformat(),
        })
    except Exception:
        pass

    return {"case_id": case_id, **final_state}


async def _persist_case(
    db: AsyncSession,
    case_id: str,
    event_data: dict[str, Any],
    state: dict[str, Any],
    is_simulation: bool,
    completed_at: datetime,
    final_status: str,
) -> None:
    """Upsert a RecoveryCase record, its audit logs, human reviews, and outcomes."""
    from sqlalchemy import select
    from app.models.recovery_case import RecoveryCase
    from app.models.audit_log import AuditLog
    from app.models.outcome import Outcome
    from app.models.human_review import HumanReview

    # 1. Find or create RecoveryCase
    result = await db.execute(
        select(RecoveryCase).where(RecoveryCase.case_id == case_id)
    )
    case = result.scalar_one_or_none()

    if case is None:
        from app.models.revenue_event import RevenueEvent
        event_result = await db.execute(
            select(RevenueEvent).where(RevenueEvent.external_id == str(event_data.get("external_id", "")))
        )
        event_db = event_result.scalar_one_or_none()

        case = RecoveryCase(
            case_id=case_id,
            event_id=event_db.id if event_db else 0,
            is_simulation=is_simulation,
            started_at=datetime.now(timezone.utc),
        )
        db.add(case)

    # Update case fields
    case.status = final_status
    case.current_step = state.get("current_step", "unknown")
    case.root_cause = state.get("root_cause")
    case.selected_strategy = state.get("recommended_strategy")
    case.policy_approved = bool(state.get("policy_approved", False))
    case.outcome_status = state.get("outcome_status")
    case.recovered_amount = float(state.get("recovered_amount", 0))
    case.revenue_at_risk = float(
        (state.get("sentinel_output") or {}).get("revenue_at_risk", event_data.get("amount", 0))
    )
    case.human_escalation_required = bool(state.get("human_escalation_required", False))
    case.completed_at = completed_at
    case.errors_json = json.dumps(state.get("errors", []))

    for field, attr in [
        ("sentinel_output", "sentinel_output_json"),
        ("diagnosis_output", "diagnosis_output_json"),
        ("customer_profile", "customer_profile_json"),
        ("opportunity_score", "opportunity_score_json"),
        ("guardian_decision", "guardian_decision_json"),
        ("execution_result", "execution_result_json"),
        ("learning_update", "learning_update_json"),
    ]:
        val = state.get(field)
        if val:
            setattr(case, attr, json.dumps(val, default=str))

    for list_field, attr in [
        ("candidate_strategies", "candidate_strategies_json"),
        ("twin_predictions", "twin_predictions_json"),
    ]:
        val = state.get(list_field)
        if val:
            setattr(case, attr, json.dumps(val, default=str))

    # 2. Persist all accumulated audit log entries
    for entry in state.get("audit_entries", []):
        agent_name = entry.get("agent_name", "unknown")
        existing_log = (await db.execute(
            select(AuditLog).where(
                AuditLog.case_id == case_id,
                AuditLog.agent_name == agent_name,
            )
        )).scalar_one_or_none()

        if not existing_log:
            ts = entry.get("timestamp")
            parsed_ts = datetime.fromisoformat(ts) if ts else datetime.now(timezone.utc)
            log = AuditLog(
                case_id=case_id,
                agent_name=agent_name,
                step_index=int(entry.get("step_index", 0)),
                decision=entry.get("decision", ""),
                reasoning=entry.get("reasoning", ""),
                confidence=float(entry.get("confidence", 0.0)),
                decision_source=entry.get("decision_source", "DETERMINISTIC"),
                llm_provider=entry.get("llm_provider"),
                llm_model=entry.get("llm_model"),
                llm_used=int(entry.get("llm_used", False)),
                used_fallback=int(entry.get("used_fallback", False)),
                input_json=entry.get("input_json"),
                output_json=entry.get("output_json"),
                had_error=int(entry.get("had_error", False)),
                error_message=entry.get("error_message"),
                duration_ms=float(entry.get("duration_ms", 0.0)),
                timestamp=parsed_ts,
            )
            db.add(log)

    # 3. Create or update outcome record
    outcome = state.get("outcome_record")
    if outcome:
        existing_outcome = (await db.execute(
            select(Outcome).where(Outcome.case_id == case_id)
        )).scalar_one_or_none()

        if not existing_outcome:
            new_outcome = Outcome(
                case_id=case_id,
                status=outcome.get("status", "NOT_RECOVERED"),
                recovered_amount=float(outcome.get("recovered_amount", 0)),
                recovery_cost=float(outcome.get("recovery_cost", 0)),
                net_recovered=float(outcome.get("net_recovered", 0)),
                recovery_time_seconds=float(outcome.get("recovery_time_seconds", 0)),
                strategy_used=outcome.get("strategy_used", ""),
                notes=outcome.get("notes", ""),
                expected_recovery_value=float(
                    (state.get("opportunity_score") or {}).get("expected_recovery_value", 0)
                ),
            )
            db.add(new_outcome)
        else:
            existing_outcome.status = outcome.get("status", existing_outcome.status)
            existing_outcome.recovered_amount = float(outcome.get("recovered_amount", existing_outcome.recovered_amount))
            existing_outcome.net_recovered = float(outcome.get("net_recovered", existing_outcome.net_recovered))

    # 4. Create or update Human Review record if escalated
    if state.get("human_escalation_required"):
        existing_hr = (await db.execute(
            select(HumanReview).where(HumanReview.case_id == case_id)
        )).scalar_one_or_none()

        if not existing_hr:
            guardian = state.get("guardian_decision") or {}
            sentinel = state.get("sentinel_output") or {}
            policy_checks = guardian.get("policy_checks") or []
            hr = HumanReview(
                case_id=case_id,
                status="PENDING",
                escalation_reason=guardian.get("block_reason") or "Human approval required (Policy escalation)",
                escalation_priority="HIGH" if float(event_data.get("amount", 0)) > 50000 else "MEDIUM",
                ai_recommendation_json=json.dumps(guardian.get("selected_strategy") or {}),
                reasoning_summary=guardian.get("reasoning", ""),
                candidate_strategies_json=json.dumps(state.get("candidate_strategies") or []),
                twin_predictions_json=json.dumps(state.get("twin_predictions") or []),
                policy_checks_json=json.dumps(policy_checks),
                amount_at_risk=float(sentinel.get("revenue_at_risk", event_data.get("amount", 0))),
                ai_confidence=float(sentinel.get("confidence", 0.5)),
            )
            db.add(hr)

    await db.commit()
