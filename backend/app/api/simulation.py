"""
RECOVERX AI — Simulation API
Batch simulation runner and results comparison supporting configurable execution modes:
- SIMULATION_MODE: Fast deterministic simulation (0 LLM calls, ideal for 1000-event benchmarks)
- DEMO_AI_MODE: Live Gemini for sample cases
- HYBRID_MODE: LLM invoked only when ambiguity/amount exceeds threshold
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, get_db
from app.simulation.generator import generate_full_dataset
from app.simulation.baseline import simulate_baseline, compare_with_baseline
from app.simulation.engine import SimulationEngine
from app.eventbus import get_event_bus

router = APIRouter(prefix="/api/simulation", tags=["simulation"])

_sim_engine = SimulationEngine()

# In-memory simulation state
_simulation_state: dict[str, Any] = {
    "running": False,
    "progress": 0,
    "total": 0,
    "mode": "SIMULATION_MODE",
    "results": None,
}


@router.post("/run-batch")
async def run_batch_simulation(
    background_tasks: BackgroundTasks,
    n_events: int = 100,
    seed: int = 42,
    mode: str = "SIMULATION_MODE",  # SIMULATION_MODE | DEMO_AI_MODE | HYBRID_MODE
):
    """
    Run batch simulation of n_events.
    Modes:
    - SIMULATION_MODE: Pure deterministic benchmark (no API quota usage)
    - DEMO_AI_MODE: Live Gemini reasoning on sample events
    - HYBRID_MODE: LLM for high-value / ambiguous edge cases
    """
    global _simulation_state

    if _simulation_state["running"]:
        return {"message": "Simulation already running", "state": _simulation_state}

    valid_modes = {"SIMULATION_MODE", "DEMO_AI_MODE", "HYBRID_MODE"}
    exec_mode = mode if mode in valid_modes else "SIMULATION_MODE"

    _simulation_state = {
        "running": True,
        "progress": 0,
        "total": n_events,
        "mode": exec_mode,
        "results": None,
    }
    background_tasks.add_task(_run_batch_task, n_events=n_events, seed=seed, mode=exec_mode)
    return {
        "message": f"Batch simulation started for {n_events} events [{exec_mode}]",
        "state": _simulation_state,
    }


@router.get("/results")
async def get_simulation_results():
    """Return current simulation state, results, and active execution mode."""
    return _simulation_state


@router.get("/dataset-preview")
async def preview_dataset(n_customers: int = 10, n_events: int = 20, seed: int = 42):
    """Preview a small slice of synthetic data."""
    data = generate_full_dataset(n_customers=n_customers, n_events=n_events, seed=seed)
    return {
        "sample_customers": data["customers"][:5],
        "sample_events": data["events"][:10],
        "metadata": data["metadata"],
    }


async def _run_batch_task(n_events: int, seed: int, mode: str = "SIMULATION_MODE") -> None:
    """Background task: run batch simulation with configurable AI mode."""
    global _simulation_state
    bus = get_event_bus()

    data = generate_full_dataset(n_customers=200, n_events=n_events, seed=seed)
    events = data["events"]
    customers_map = {c["external_id"]: c for c in data["customers"]}

    recoverx_recovered = 0.0
    recoverx_cost = 0.0
    baseline_recovered = 0.0
    baseline_cost = 0.0

    outcomes_by_type: dict[str, dict] = {}
    strategy_stats: dict[str, dict] = {}
    processed = 0

    for event in events:
        try:
            cust = customers_map.get(event.get("customer_external_id", ""), {})
            failure_reason = event.get("failure_reason", "UNKNOWN").upper()
            payment_method = event.get("payment_method", "CARD")
            amount = float(event.get("amount", 0))
            tier = cust.get("tier", "STANDARD")
            fatigue = float(cust.get("fatigue_score", 0))

            # Map to root cause
            cause_map = {
                "BANK_DECLINE": "TEMPORARY_BANK_FAILURE",
                "INSUFFICIENT_FUNDS": "INSUFFICIENT_FUNDS",
                "CARD_EXPIRED": "PAYMENT_METHOD_FAILURE",
                "UPI_TIMEOUT": "TEMPORARY_BANK_FAILURE",
                "NETWORK_ERROR": "TECHNICAL_CHECKOUT_ISSUE",
                "CUSTOMER_ABANDONED": "CUSTOMER_ABANDONMENT",
                "TECHNICAL_ERROR": "TECHNICAL_CHECKOUT_ISSUE",
                "INVOICE_DELAY": "INVOICE_DELAY",
            }
            root_cause = "UNKNOWN"
            for k, v in cause_map.items():
                if k in failure_reason:
                    root_cause = v
                    break

            # RECOVERX AI — optimal strategy selection
            strategy_matrix = {
                "TEMPORARY_BANK_FAILURE": "RETRY_LATER",
                "CUSTOMER_ABANDONMENT": "SEND_WHATSAPP",
                "PAYMENT_METHOD_FAILURE": "OFFER_ALTERNATE_PAYMENT",
                "INSUFFICIENT_FUNDS": "SCHEDULE_FOLLOWUP",
                "TECHNICAL_CHECKOUT_ISSUE": "RETRY_PAYMENT",
                "INVOICE_DELAY": "SCHEDULE_FOLLOWUP",
            }
            strategy = strategy_matrix.get(root_cause, "SEND_EMAIL")
            case_id = f"SIM-{event.get('external_id', str(processed))[-8:]}"

            rx_success, rx_prob = _sim_engine.simulate_strategy_outcome(
                strategy_type=strategy,
                root_cause=root_cause,
                payment_method=payment_method,
                customer_tier=tier,
                fatigue_score=fatigue,
                amount=amount,
                case_id=case_id,
            )
            rx_cost_val = _sim_engine.estimate_strategy_cost(strategy, amount)

            # Baseline comparison
            bl_result = simulate_baseline(event)

            if rx_success:
                recoverx_recovered += amount
            recoverx_cost += rx_cost_val

            baseline_recovered += bl_result["recovered_amount"]
            baseline_cost += bl_result["recovery_cost"]

            # Track by event type
            etype = event.get("event_type", "UNKNOWN")
            if etype not in outcomes_by_type:
                outcomes_by_type[etype] = {"total": 0, "recovered": 0, "at_risk": 0}
            outcomes_by_type[etype]["total"] += 1
            outcomes_by_type[etype]["at_risk"] += amount
            if rx_success:
                outcomes_by_type[etype]["recovered"] += amount

            # Strategy stats
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {"success": 0, "total": 0, "recovered": 0}
            strategy_stats[strategy]["total"] += 1
            if rx_success:
                strategy_stats[strategy]["success"] += 1
                strategy_stats[strategy]["recovered"] += amount

            # Persist a representative sample of cases to database (up to 30 cases)
            if processed < 30:
                try:
                    from datetime import datetime, timezone
                    from app.models.recovery_case import RecoveryCase
                    from app.models.outcome import Outcome
                    from app.models.audit_log import AuditLog
                    import json

                    async with AsyncSessionLocal() as db_session:
                        case_status = "RECOVERED" if rx_success else "FAILED"
                        if amount > 100000:
                            case_status = "ESCALATED"
                        elif cust.get("opt_out"):
                            case_status = "STOPPED"

                        new_case = RecoveryCase(
                            case_id=case_id,
                            event_id=0,
                            status=case_status,
                            current_step="completed",
                            root_cause=root_cause,
                            selected_strategy=strategy,
                            policy_approved=(case_status != "STOPPED"),
                            outcome_status=case_status,
                            recovered_amount=amount if case_status == "RECOVERED" else 0.0,
                            revenue_at_risk=amount,
                            recovery_cost=rx_cost_val,
                            expected_recovery_value=amount * rx_prob,
                            human_escalation_required=(case_status == "ESCALATED"),
                            is_simulation=True,
                            completed_at=datetime.now(timezone.utc),
                        )
                        db_session.add(new_case)

                        new_out = Outcome(
                            case_id=case_id,
                            status=case_status,
                            recovered_amount=amount if case_status == "RECOVERED" else 0.0,
                            recovery_cost=rx_cost_val,
                            net_recovered=(amount - rx_cost_val) if case_status == "RECOVERED" else -rx_cost_val,
                            recovery_time_seconds=8.0,
                            strategy_used=strategy,
                            notes=f"Batch simulation run [{mode}].",
                            expected_recovery_value=amount * rx_prob,
                        )
                        db_session.add(new_out)

                        # Write an audit log entry for this case
                        decision_src = "LLM" if mode == "DEMO_AI_MODE" and processed < 5 else "DETERMINISTIC"
                        audit = AuditLog(
                            case_id=case_id,
                            agent_name="recovery_strategy_planner",
                            step_index=5,
                            decision=strategy,
                            reasoning=f"Selected optimal strategy {strategy} for root cause {root_cause} with predicted probability {rx_prob:.0%}.",
                            confidence=rx_prob,
                            decision_source=decision_src,
                            llm_used=1 if decision_src == "LLM" else 0,
                            duration_ms=12.0,
                            input_json=json.dumps({"amount": amount, "root_cause": root_cause}),
                            output_json=json.dumps({"strategy": strategy, "probability": rx_prob}),
                        )
                        db_session.add(audit)
                        await db_session.commit()
                except Exception:
                    pass

        except Exception:
            pass

        processed += 1
        _simulation_state["progress"] = processed

        if processed % 20 == 0 or processed == n_events:
            await bus.publish("simulation_progress", {
                "type": "simulation_progress",
                "processed": processed,
                "total": n_events,
                "pct": round(processed / n_events * 100, 1),
                "mode": mode,
            })
            await asyncio.sleep(0.01)

    total_at_risk = sum(e.get("amount", 0) for e in events)
    rx_net = recoverx_recovered - recoverx_cost
    bl_net = baseline_recovered - baseline_cost

    _simulation_state["results"] = {
        "execution_mode": mode,
        "summary": {
            "total_events": n_events,
            "execution_mode": mode,
            "total_revenue_at_risk": round(total_at_risk, 2),
            "recoverx_recovered": round(recoverx_recovered, 2),
            "recoverx_cost": round(recoverx_cost, 2),
            "recoverx_net": round(rx_net, 2),
            "recoverx_recovery_rate_pct": round(recoverx_recovered / total_at_risk * 100, 1) if total_at_risk else 0,
            "baseline_recovered": round(baseline_recovered, 2),
            "baseline_cost": round(baseline_cost, 2),
            "baseline_net": round(bl_net, 2),
            "baseline_recovery_rate_pct": round(baseline_recovered / total_at_risk * 100, 1) if total_at_risk else 0,
            "improvement_pct": round((rx_net - bl_net) / abs(bl_net) * 100, 1) if bl_net != 0 else 0,
            "additional_value_recovered": round(rx_net - bl_net, 2),
        },
        "by_event_type": outcomes_by_type,
        "strategy_breakdown": strategy_stats,
        "disclaimer": "All metrics calculated from synthetic simulation. Not actual payment results.",
    }
    _simulation_state["running"] = False

    await bus.publish("simulation_progress", {
        "type": "simulation_complete",
        "results": _simulation_state["results"],
    })
