"""
RECOVERX AI — Baseline Strategy Comparison
Simulates the naive baseline (immediate retry + generic email) for comparison.
All RECOVERX metrics are measured AGAINST this baseline.
"""

from __future__ import annotations

from typing import Any

from app.simulation.engine import SimulationEngine

_sim = SimulationEngine(seed=99)


def simulate_baseline(event: dict[str, Any]) -> dict[str, Any]:
    """
    Simulate the naive baseline recovery strategy:
    1. Immediate payment retry
    2. If retry fails → generic email reminder
    No AI, no context, no strategy selection.
    """
    amount = float(event.get("amount", 0))
    failure_reason = event.get("failure_reason", "UNKNOWN").upper()
    payment_method = event.get("payment_method", "CARD")

    # Map failure reason to root cause for simulation
    cause_map = {
        "BANK_DECLINE": "TEMPORARY_BANK_FAILURE",
        "INSUFFICIENT_FUNDS": "INSUFFICIENT_FUNDS",
        "CARD_EXPIRED": "PAYMENT_METHOD_FAILURE",
        "UPI_TIMEOUT": "TEMPORARY_BANK_FAILURE",
        "NETWORK_ERROR": "TECHNICAL_CHECKOUT_ISSUE",
        "CUSTOMER_ABANDONED": "CUSTOMER_ABANDONMENT",
        "TECHNICAL_ERROR": "TECHNICAL_CHECKOUT_ISSUE",
    }
    root_cause = "UNKNOWN"
    for k, v in cause_map.items():
        if k in failure_reason:
            root_cause = v
            break

    # Baseline: immediate retry (no strategy intelligence)
    retry_success, retry_prob = _sim.simulate_baseline_outcome(
        root_cause=root_cause,
        payment_method=payment_method,
        amount=amount,
    )

    # Baseline cost: retry (₹15) + email (₹8) = ₹23
    cost = 23.0
    recovered = amount if retry_success else 0.0
    net = recovered - cost

    return {
        "strategy": "IMMEDIATE_RETRY_PLUS_EMAIL",
        "success": retry_success,
        "recovered_amount": recovered,
        "recovery_cost": cost,
        "net_recovered": net,
        "probability_used": retry_prob,
        "description": "Baseline: Immediate retry + generic email. No AI context or strategy selection.",
    }


def compare_with_baseline(
    recoverx_outcome: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    """
    Compare RECOVERX AI outcome against baseline.
    Returns improvement metrics.
    """
    baseline = simulate_baseline(event)
    rx_recovered = float(recoverx_outcome.get("recovered_amount", 0))
    rx_cost = float(recoverx_outcome.get("recovery_cost", 0))
    rx_net = rx_recovered - rx_cost

    bl_recovered = baseline["recovered_amount"]
    bl_net = baseline["net_recovered"]

    improvement_pct = ((rx_net - bl_net) / abs(bl_net) * 100) if bl_net != 0 else (100.0 if rx_net > 0 else 0.0)

    return {
        "recoverx_ai": {
            "recovered": rx_recovered,
            "cost": rx_cost,
            "net": rx_net,
            "strategy": recoverx_outcome.get("strategy_used", "UNKNOWN"),
        },
        "baseline": {
            "recovered": bl_recovered,
            "cost": baseline["recovery_cost"],
            "net": bl_net,
            "strategy": "IMMEDIATE_RETRY_PLUS_EMAIL",
        },
        "improvement": {
            "net_value_delta": round(rx_net - bl_net, 2),
            "improvement_pct": round(improvement_pct, 1),
            "recoverx_better": rx_net > bl_net,
        },
    }
