"""
RECOVERX AI — Simulation Engine
Probability-based outcome engine for recovery action simulation.
All metrics are calculated from simulated outcomes — not fabricated.
"""

from __future__ import annotations

import random
from typing import Tuple


# Recovery probability matrix: (root_cause, payment_method) → base_probability
_BASE_PROBS: dict[tuple[str, str], float] = {
    # Temporary bank failures — high recovery with retry
    ("TEMPORARY_BANK_FAILURE", "CARD"): 0.78,
    ("TEMPORARY_BANK_FAILURE", "UPI"): 0.82,
    ("TEMPORARY_BANK_FAILURE", "NETBANKING"): 0.74,
    ("TEMPORARY_BANK_FAILURE", "WALLET"): 0.70,
    ("TEMPORARY_BANK_FAILURE", "BANK_TRANSFER"): 0.65,

    # Insufficient funds — low recovery
    ("INSUFFICIENT_FUNDS", "CARD"): 0.28,
    ("INSUFFICIENT_FUNDS", "UPI"): 0.30,
    ("INSUFFICIENT_FUNDS", "NETBANKING"): 0.25,
    ("INSUFFICIENT_FUNDS", "WALLET"): 0.35,
    ("INSUFFICIENT_FUNDS", "BANK_TRANSFER"): 0.20,

    # Payment method failure — medium with alternate
    ("PAYMENT_METHOD_FAILURE", "CARD"): 0.55,
    ("PAYMENT_METHOD_FAILURE", "UPI"): 0.60,
    ("PAYMENT_METHOD_FAILURE", "NETBANKING"): 0.50,
    ("PAYMENT_METHOD_FAILURE", "WALLET"): 0.45,
    ("PAYMENT_METHOD_FAILURE", "BANK_TRANSFER"): 0.40,

    # Customer abandonment — medium with engagement
    ("CUSTOMER_ABANDONMENT", "CARD"): 0.52,
    ("CUSTOMER_ABANDONMENT", "UPI"): 0.58,
    ("CUSTOMER_ABANDONMENT", "NETBANKING"): 0.48,
    ("CUSTOMER_ABANDONMENT", "WALLET"): 0.50,
    ("CUSTOMER_ABANDONMENT", "BANK_TRANSFER"): 0.35,

    # Technical checkout — high recovery
    ("TECHNICAL_CHECKOUT_ISSUE", "CARD"): 0.72,
    ("TECHNICAL_CHECKOUT_ISSUE", "UPI"): 0.75,
    ("TECHNICAL_CHECKOUT_ISSUE", "NETBANKING"): 0.68,
    ("TECHNICAL_CHECKOUT_ISSUE", "WALLET"): 0.70,
    ("TECHNICAL_CHECKOUT_ISSUE", "BANK_TRANSFER"): 0.65,

    # Subscription failure — medium
    ("SUBSCRIPTION_PAYMENT_FAILURE", "CARD"): 0.60,
    ("SUBSCRIPTION_PAYMENT_FAILURE", "UPI"): 0.62,
    ("SUBSCRIPTION_PAYMENT_FAILURE", "NETBANKING"): 0.55,
    ("SUBSCRIPTION_PAYMENT_FAILURE", "WALLET"): 0.50,
    ("SUBSCRIPTION_PAYMENT_FAILURE", "BANK_TRANSFER"): 0.45,

    # Invoice delay — varies
    ("INVOICE_DELAY", "BANK_TRANSFER"): 0.65,
    ("INVOICE_DELAY", "NETBANKING"): 0.55,
    ("INVOICE_DELAY", "CARD"): 0.45,
    ("INVOICE_DELAY", "UPI"): 0.48,
    ("INVOICE_DELAY", "WALLET"): 0.40,

    # Unknown
    ("UNKNOWN", "CARD"): 0.42,
    ("UNKNOWN", "UPI"): 0.44,
    ("UNKNOWN", "NETBANKING"): 0.40,
    ("UNKNOWN", "WALLET"): 0.38,
    ("UNKNOWN", "BANK_TRANSFER"): 0.35,
}

# Strategy multipliers — how much does each strategy modify base probability?
_STRATEGY_MULTIPLIERS: dict[str, dict[str, float]] = {
    "RETRY_PAYMENT": {
        "TEMPORARY_BANK_FAILURE": 1.0,
        "TECHNICAL_CHECKOUT_ISSUE": 0.95,
        "INSUFFICIENT_FUNDS": 0.4,
        "PAYMENT_METHOD_FAILURE": 0.6,
        "CUSTOMER_ABANDONMENT": 0.3,
        "DEFAULT": 0.7,
    },
    "RETRY_LATER": {
        "TEMPORARY_BANK_FAILURE": 1.10,
        "TECHNICAL_CHECKOUT_ISSUE": 1.05,
        "INSUFFICIENT_FUNDS": 0.55,
        "PAYMENT_METHOD_FAILURE": 0.65,
        "CUSTOMER_ABANDONMENT": 0.45,
        "DEFAULT": 0.8,
    },
    "GENERATE_PAYMENT_LINK": {
        "CUSTOMER_ABANDONMENT": 1.15,
        "PAYMENT_METHOD_FAILURE": 1.05,
        "INSUFFICIENT_FUNDS": 0.70,
        "TEMPORARY_BANK_FAILURE": 0.90,
        "TECHNICAL_CHECKOUT_ISSUE": 0.95,
        "DEFAULT": 0.9,
    },
    "OFFER_ALTERNATE_PAYMENT": {
        "PAYMENT_METHOD_FAILURE": 1.25,
        "CUSTOMER_ABANDONMENT": 1.10,
        "INSUFFICIENT_FUNDS": 0.80,
        "TEMPORARY_BANK_FAILURE": 0.85,
        "DEFAULT": 0.95,
    },
    "SEND_WHATSAPP": {
        "CUSTOMER_ABANDONMENT": 1.20,
        "INSUFFICIENT_FUNDS": 0.75,
        "TEMPORARY_BANK_FAILURE": 0.85,
        "PAYMENT_METHOD_FAILURE": 0.90,
        "DEFAULT": 0.85,
    },
    "SEND_EMAIL": {
        "CUSTOMER_ABANDONMENT": 1.05,
        "INSUFFICIENT_FUNDS": 0.65,
        "TEMPORARY_BANK_FAILURE": 0.80,
        "PAYMENT_METHOD_FAILURE": 0.85,
        "DEFAULT": 0.80,
    },
    "SCHEDULE_FOLLOWUP": {
        "INSUFFICIENT_FUNDS": 0.80,
        "INVOICE_DELAY": 1.10,
        "CUSTOMER_ABANDONMENT": 0.90,
        "SUBSCRIPTION_PAYMENT_FAILURE": 0.95,
        "DEFAULT": 0.85,
    },
}

# Customer tier multipliers
_TIER_MULTIPLIERS: dict[str, float] = {
    "PREMIUM": 1.15,
    "STANDARD": 1.00,
    "NEW": 0.85,
    "B2B": 0.90,
}

# Time-since-failure degradation
_TIME_DECAY_RATES: dict[str, float] = {
    "TEMPORARY_BANK_FAILURE": 0.05,   # Degrades fast — act within hours
    "CUSTOMER_ABANDONMENT": 0.02,      # Moderate — act within a day
    "INSUFFICIENT_FUNDS": 0.01,        # Slow — funds arrive on payday
    "PAYMENT_METHOD_FAILURE": 0.015,
    "TECHNICAL_CHECKOUT_ISSUE": 0.03,
    "DEFAULT": 0.02,
}


class SimulationEngine:
    """
    Probability-based simulation engine.
    Determines whether a recovery action succeeds based on:
    - Root cause of failure
    - Payment method
    - Selected strategy
    - Customer tier
    - Fatigue score
    - Time since failure
    - Random variation (seeded per case for reproducibility)
    """

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    def simulate_payment_retry(
        self,
        amount: float,
        payment_method: str,
        root_cause: str,
        success_bonus: float = 0.0,
    ) -> Tuple[bool, float]:
        """Return (success, probability_used)."""
        key = (root_cause, payment_method)
        base = _BASE_PROBS.get(key, 0.45)
        # Small amount modifier: very small amounts harder to recover (effort > value)
        if amount < 100:
            base *= 0.7
        prob = min(0.97, base + success_bonus)
        success = self._rng.random() < prob
        return success, round(prob, 3)

    def simulate_strategy_outcome(
        self,
        strategy_type: str,
        root_cause: str,
        payment_method: str,
        customer_tier: str,
        fatigue_score: float,
        amount: float,
        hours_since_failure: float = 1.0,
    ) -> Tuple[bool, float]:
        """
        Full strategy simulation.
        Returns (success, final_probability).
        """
        # 1. Base probability from cause × method matrix
        key = (root_cause, payment_method)
        base = _BASE_PROBS.get(key, 0.45)

        # 2. Strategy multiplier
        strat_mults = _STRATEGY_MULTIPLIERS.get(strategy_type, {"DEFAULT": 0.85})
        multiplier = strat_mults.get(root_cause, strat_mults.get("DEFAULT", 0.85))

        # 3. Tier adjustment
        tier_mult = _TIER_MULTIPLIERS.get(customer_tier, 1.0)

        # 4. Fatigue penalty
        fatigue_penalty = fatigue_score * 0.35  # max 35% degradation at full fatigue

        # 5. Time decay
        decay_rate = _TIME_DECAY_RATES.get(root_cause, _TIME_DECAY_RATES["DEFAULT"])
        time_penalty = min(0.30, hours_since_failure * decay_rate / 24)

        # 6. Amount modifier
        if amount < 100:
            amount_mod = 0.75
        elif amount > 100000:
            amount_mod = 1.05  # High value gets more effort
        else:
            amount_mod = 1.0

        # 7. Combine
        prob = base * multiplier * tier_mult * amount_mod
        prob = max(0.05, min(0.97, prob - fatigue_penalty - time_penalty))

        # 8. Simulate
        success = self._rng.random() < prob
        return success, round(prob, 3)

    def estimate_strategy_cost(
        self,
        strategy_type: str,
        amount: float,
    ) -> float:
        """Estimate the cost of executing a recovery strategy in INR."""
        base_costs = {
            "RETRY_PAYMENT": 10.0,
            "RETRY_LATER": 15.0,
            "GENERATE_PAYMENT_LINK": 25.0,
            "OFFER_ALTERNATE_PAYMENT": 30.0,
            "SEND_WHATSAPP": 20.0,
            "SEND_EMAIL": 8.0,
            "SCHEDULE_FOLLOWUP": 15.0,
            "ESCALATE_TO_HUMAN": 150.0,
            "STOP_RECOVERY": 0.0,
        }
        return base_costs.get(strategy_type, 25.0)

    def simulate_baseline_outcome(
        self,
        root_cause: str,
        payment_method: str,
        amount: float,
    ) -> Tuple[bool, float]:
        """
        Simulate the naive baseline strategy:
        Immediate retry → generic email.
        Used for comparison against RECOVERX AI strategy.
        """
        # Baseline: immediate retry (no intelligence)
        key = (root_cause, payment_method)
        base = _BASE_PROBS.get(key, 0.45)
        # Baseline has no strategy optimization — flat 75% of base prob
        prob = max(0.05, base * 0.75)
        success = self._rng.random() < prob
        return success, round(prob, 3)
