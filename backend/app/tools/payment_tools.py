"""
RECOVERX AI — Payment Tools (Simulated)
All payment actions are simulated — no actual money is moved.
Only the Recovery Execution Agent is permitted to call these.
"""

from __future__ import annotations

import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Any

from app.simulation.engine import SimulationEngine, deterministic_roll

logger = logging.getLogger(__name__)
_sim = SimulationEngine()


async def retry_payment(
    case_id: str,
    amount: float,
    payment_method: str,
    customer_id: str,
    root_cause: str,
) -> dict[str, Any]:
    """
    Immediately retry a failed payment.
    Outcome determined by the simulation engine using deterministic hashing.
    """
    logger.info(f"[TOOL:retry_payment] case={case_id} amount=₹{amount:,.0f}")
    success, prob = _sim.simulate_payment_retry(
        amount=amount,
        payment_method=payment_method,
        root_cause=root_cause,
        case_id=case_id,
    )
    return {
        "tool": "retry_payment",
        "success": success,
        "transaction_id": f"pay_{uuid.uuid4().hex[:12]}" if success else None,
        "amount": amount,
        "payment_method": payment_method,
        "probability_used": prob,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "simulation": True,
    }


async def schedule_retry(
    case_id: str,
    amount: float,
    payment_method: str,
    delay_hours: float,
    customer_id: str,
    root_cause: str,
) -> dict[str, Any]:
    """
    Schedule a payment retry for a future time.
    Time-delayed retries often have higher success rates for bank failures.
    """
    logger.info(f"[TOOL:schedule_retry] case={case_id} delay={delay_hours}h")
    # Delayed retries have +10% success for temporary bank failures
    bonus = 0.10 if "BANK" in root_cause or "TECHNICAL" in root_cause else 0.0
    success, prob = _sim.simulate_payment_retry(
        amount=amount,
        payment_method=payment_method,
        root_cause=root_cause,
        success_bonus=bonus,
        case_id=case_id,
    )
    scheduled_time = datetime.now(timezone.utc)
    return {
        "tool": "schedule_retry",
        "success": True,  # Scheduling succeeds; action queued
        "scheduled_transaction_id": f"sched_{uuid.uuid4().hex[:8]}",
        "scheduled_at_hours_from_now": delay_hours,
        "expected_outcome": "success" if success else "likely_failure",
        "simulation_probability": prob + bonus,
        "timestamp": scheduled_time.isoformat(),
        "simulation": True,
    }


async def generate_payment_link(
    case_id: str,
    amount: float,
    customer_id: str,
    expiry_hours: int = 48,
) -> dict[str, Any]:
    """
    Generate a payment link for the customer.
    Success depends on customer engagement probability.
    """
    logger.info(f"[TOOL:generate_payment_link] case={case_id} amount=₹{amount:,.0f}")
    link_id = uuid.uuid4().hex[:12].upper()
    # Link click probability depends on amount (lower for very high amounts)
    click_prob = max(0.35, 0.75 - (amount / 200000))
    clicked_roll = deterministic_roll(case_id, "link_click")
    clicked = clicked_roll < click_prob
    paid_roll = deterministic_roll(case_id, "link_paid")
    paid = clicked and (paid_roll < 0.72)

    return {
        "tool": "generate_payment_link",
        "success": True,
        "link_id": link_id,
        "payment_url": f"https://rzp.io/pay/{link_id}",
        "amount": amount,
        "expires_in_hours": expiry_hours,
        "simulated_customer_clicked": clicked,
        "simulated_payment_completed": paid,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "simulation": True,
    }
