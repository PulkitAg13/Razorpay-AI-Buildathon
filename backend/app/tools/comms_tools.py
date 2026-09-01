"""
RECOVERX AI — Communication Tools (Simulated)
WhatsApp and email actions are simulated — no actual messages are sent.
Only the Recovery Execution Agent is permitted to call these.
"""

from __future__ import annotations

import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


async def send_whatsapp(
    case_id: str,
    customer_id: str,
    template: str,
    params: dict[str, Any],
    fatigue_score: float = 0.0,
) -> dict[str, Any]:
    """
    Send a WhatsApp message to the customer.
    Delivery and response probability depends on fatigue and time.
    """
    logger.info(f"[TOOL:send_whatsapp] case={case_id} customer={customer_id}")

    # Delivery degrades with fatigue
    delivery_prob = max(0.30, 0.92 - fatigue_score * 0.5)
    read_prob = delivery_prob * max(0.20, 0.75 - fatigue_score * 0.4)
    response_prob = read_prob * max(0.10, 0.60 - fatigue_score * 0.5)

    delivered = random.random() < delivery_prob
    read = delivered and random.random() < 0.75
    customer_responded = read and random.random() < response_prob

    return {
        "tool": "send_whatsapp",
        "success": delivered,
        "message_id": f"wa_{uuid.uuid4().hex[:10]}",
        "template": template,
        "customer_id": customer_id,
        "simulated_delivered": delivered,
        "simulated_read": read,
        "simulated_customer_responded": customer_responded,
        "delivery_probability": round(delivery_prob, 2),
        "fatigue_score_used": fatigue_score,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "simulation": True,
    }


async def send_email(
    case_id: str,
    customer_id: str,
    template: str,
    params: dict[str, Any],
    fatigue_score: float = 0.0,
) -> dict[str, Any]:
    """
    Send an email to the customer.
    Open rates and click-through depend on fatigue and template quality.
    """
    logger.info(f"[TOOL:send_email] case={case_id} customer={customer_id}")

    delivery_prob = 0.97  # Email almost always delivers
    open_prob = max(0.10, 0.35 - fatigue_score * 0.2)
    click_prob = open_prob * max(0.10, 0.45 - fatigue_score * 0.3)

    delivered = random.random() < delivery_prob
    opened = delivered and random.random() < open_prob
    clicked = opened and random.random() < click_prob

    return {
        "tool": "send_email",
        "success": delivered,
        "email_id": f"em_{uuid.uuid4().hex[:10]}",
        "template": template,
        "customer_id": customer_id,
        "simulated_delivered": delivered,
        "simulated_opened": opened,
        "simulated_clicked": clicked,
        "open_probability": round(open_prob, 2),
        "fatigue_score_used": fatigue_score,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "simulation": True,
    }
