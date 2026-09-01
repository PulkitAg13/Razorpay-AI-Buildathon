"""
RECOVERX AI — Synthetic Data Generator
Creates 1000+ realistic revenue events for simulation and evaluation.
All data is clearly synthetic.
"""

from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

# ── Distributions ─────────────────────────────────────────────────────────────

EVENT_TYPE_DIST = [
    ("PAYMENT_FAILURE", 0.50),
    ("CHECKOUT_ABANDONMENT", 0.30),
    ("SUBSCRIPTION_FAILURE", 0.15),
    ("INVOICE_OVERDUE", 0.05),
]

FAILURE_REASON_BY_EVENT = {
    "PAYMENT_FAILURE": [
        ("BANK_DECLINE", 0.22),
        ("INSUFFICIENT_FUNDS", 0.20),
        ("CARD_EXPIRED", 0.12),
        ("UPI_TIMEOUT", 0.10),
        ("NETWORK_ERROR", 0.10),
        ("TECHNICAL_ERROR", 0.10),
        ("PAYMENT_METHOD_BLOCKED", 0.08),
        ("FRAUD_SUSPECTED", 0.05),
        ("OTHER", 0.03),
    ],
    "CHECKOUT_ABANDONMENT": [
        ("CUSTOMER_ABANDONED", 0.50),
        ("SESSION_EXPIRED", 0.20),
        ("PRICE_SENSITIVITY", 0.15),
        ("PAYMENT_METHOD_UNAVAILABLE", 0.10),
        ("UX_FRICTION", 0.05),
    ],
    "SUBSCRIPTION_FAILURE": [
        ("CARD_EXPIRED", 0.30),
        ("BANK_DECLINE", 0.28),
        ("INSUFFICIENT_FUNDS", 0.22),
        ("MANDATE_REVOKED", 0.12),
        ("OTHER", 0.08),
    ],
    "INVOICE_OVERDUE": [
        ("INVOICE_DELAY", 0.40),
        ("DISPUTE", 0.25),
        ("CASH_FLOW_ISSUE", 0.20),
        ("FORGOT_TO_PAY", 0.15),
    ],
}

PAYMENT_METHOD_DIST = [
    ("UPI", 0.40),
    ("CARD", 0.35),
    ("NETBANKING", 0.15),
    ("WALLET", 0.07),
    ("BANK_TRANSFER", 0.03),
]

GATEWAY_LIST = ["Razorpay", "Cashfree", "PayU", "CCAvenue", "Stripe"]

CUSTOMER_TIER_DIST = [
    ("PREMIUM", 0.10),
    ("STANDARD", 0.55),
    ("NEW", 0.25),
    ("B2B", 0.10),
]

AMOUNT_RANGES = {
    "PREMIUM": (2000, 200000),
    "STANDARD": (200, 25000),
    "NEW": (100, 5000),
    "B2B": (10000, 500000),
}

INDIAN_NAMES = [
    "Arjun Sharma", "Priya Patel", "Vikram Mehta", "Anjali Singh",
    "Rahul Gupta", "Deepa Nair", "Suresh Kumar", "Kavitha Reddy",
    "Aditya Joshi", "Meera Krishnan", "Rohit Verma", "Sneha Iyer",
    "Manish Agarwal", "Pooja Mishra", "Sanjay Yadav", "Ritika Bose",
    "Kiran Pillai", "Neha Chaudhary", "Amit Tiwari", "Shreya Pandey",
    "Vivek Saxena", "Ananya Das", "Gaurav Malhotra", "Tanvi Khanna",
    "Ravi Shankar", "Swati Jain", "Nitin Choudhary", "Divya Menon",
]

COMPANY_NAMES = [
    "TechSpark Pvt Ltd", "InnovateCo Solutions", "DataBridge Systems",
    "CloudNest Technologies", "PixelForge Studios", "GrowthMatic Corp",
    "NexaLogic Enterprises", "SmartFlow Analytics",
]


def _weighted_choice(rng: random.Random, options: list[tuple]) -> str:
    items, weights = zip(*options)
    return rng.choices(items, weights=weights)[0]


def generate_customers(n: int = 200, seed: int = 42) -> list[dict[str, Any]]:
    """Generate n synthetic customer records."""
    rng = random.Random(seed)
    customers = []

    for i in range(n):
        tier = _weighted_choice(rng, CUSTOMER_TIER_DIST)
        is_b2b = tier == "B2B"
        name = rng.choice(COMPANY_NAMES) if is_b2b else rng.choice(INDIAN_NAMES)

        contact_count = rng.randint(0, 5)
        no_response = max(0, contact_count - rng.randint(0, contact_count))

        # Payment history (last 12 months)
        payment_count = rng.randint(3, 24)
        success_rate = {"PREMIUM": 0.90, "STANDARD": 0.78, "NEW": 0.65, "B2B": 0.82}[tier]
        payment_history = []
        for j in range(payment_count):
            days_ago = rng.randint(1, 365)
            status = "SUCCESS" if rng.random() < success_rate else "FAILED"
            payment_history.append({
                "date": (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat(),
                "amount": rng.uniform(*AMOUNT_RANGES[tier]),
                "status": status,
                "method": _weighted_choice(rng, PAYMENT_METHOD_DIST),
            })

        customers.append({
            "external_id": f"CUST-{uuid.uuid4().hex[:10].upper()}",
            "name": name,
            "email": f"{name.lower().replace(' ', '.')}@example.com",
            "phone": f"+91{rng.randint(7000000000, 9999999999)}",
            "tier": tier,
            "preferred_payment_method": _weighted_choice(rng, PAYMENT_METHOD_DIST),
            "preferred_channel": rng.choice(["WHATSAPP", "EMAIL", "EMAIL", "EMAIL"]),
            "best_contact_time": rng.choice(["09:00-11:00", "11:00-13:00", "14:00-17:00", "17:00-20:00"]),
            "historical_recovery_rate": round(success_rate * rng.uniform(0.85, 1.1), 2),
            "total_successful_payments": sum(1 for p in payment_history if p["status"] == "SUCCESS"),
            "total_failed_payments": sum(1 for p in payment_history if p["status"] == "FAILED"),
            "lifetime_value": round(sum(p["amount"] for p in payment_history if p["status"] == "SUCCESS"), 2),
            "fatigue_score": round(min(1.0, contact_count * 0.15 + no_response * 0.10), 2),
            "contact_count_7d": contact_count,
            "no_response_streak": no_response,
            "opt_out": rng.random() < 0.02,  # 2% opt-out rate
            "payment_history": payment_history,
            "contact_history": [],
        })

    return customers


def generate_events(
    customers: list[dict[str, Any]],
    n: int = 1000,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Generate n synthetic revenue events referencing the given customers."""
    rng = random.Random(seed + 1)
    events = []

    for i in range(n):
        customer = rng.choice(customers)
        tier = customer["tier"]
        event_type = _weighted_choice(rng, EVENT_TYPE_DIST)

        failure_options = FAILURE_REASON_BY_EVENT.get(event_type, FAILURE_REASON_BY_EVENT["PAYMENT_FAILURE"])
        failure_reason = _weighted_choice(rng, failure_options)
        payment_method = customer.get("preferred_payment_method") or _weighted_choice(rng, PAYMENT_METHOD_DIST)
        gateway = rng.choice(GATEWAY_LIST)

        # Amount distribution by tier
        lo, hi = AMOUNT_RANGES[tier]
        # Use log-normal to get realistic skewed distribution
        mean_log = (lo + hi) / 2
        amount = min(hi, max(lo, rng.lognormvariate(
            mu=((lo + hi) / 2 / 1000),
            sigma=0.8,
        ) * 1000))
        amount = round(amount, 2)

        # Event timing (last 30 days)
        hours_ago = rng.uniform(0.5, 720)
        event_time = datetime.now(timezone.utc) - timedelta(hours=hours_ago)

        gateway_error_map = {
            "BANK_DECLINE": "ERR_BANK_1001",
            "INSUFFICIENT_FUNDS": "ERR_FUNDS_2001",
            "CARD_EXPIRED": "ERR_CARD_3001",
            "UPI_TIMEOUT": "ERR_UPI_4001",
            "NETWORK_ERROR": "ERR_NET_5001",
            "TECHNICAL_ERROR": "ERR_TECH_6001",
        }

        events.append({
            "external_id": f"EVT-{uuid.uuid4().hex[:12].upper()}",
            "event_type": event_type,
            "amount": amount,
            "currency": "INR",
            "customer_id": customer["external_id"],
            "customer_external_id": customer["external_id"],
            "payment_method": payment_method,
            "failure_reason": failure_reason,
            "gateway": gateway,
            "gateway_error_code": gateway_error_map.get(failure_reason, "ERR_UNKNOWN"),
            "status": "PENDING",
            "event_time": event_time.isoformat(),
            "metadata": {
                "session_id": uuid.uuid4().hex,
                "device": rng.choice(["mobile", "desktop", "tablet"]),
                "os": rng.choice(["Android", "iOS", "Windows", "macOS"]),
                "hours_since_failure": round(hours_ago, 1),
            },
        })

    return events


def generate_full_dataset(
    n_customers: int = 200,
    n_events: int = 1000,
    seed: int = 42,
) -> dict[str, Any]:
    """Generate complete synthetic dataset."""
    customers = generate_customers(n=n_customers, seed=seed)
    events = generate_events(customers=customers, n=n_events, seed=seed)
    return {
        "customers": customers,
        "events": events,
        "metadata": {
            "total_customers": len(customers),
            "total_events": len(events),
            "total_revenue_at_risk": round(sum(e["amount"] for e in events), 2),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "disclaimer": "All data is synthetic and generated for simulation purposes only.",
        },
    }
